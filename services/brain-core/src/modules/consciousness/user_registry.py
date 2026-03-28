"""意识核用户注册表 — 让小助知道"有哪些人"

从心跳上报 + 对话事件自动注册/更新用户信息,
为 InnerVoice 提供"我认识的用户"上下文,
为主动表达提供目标用户列表。
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("consciousness.user_registry")


@dataclass
class KnownUser:
    """意识核认识的一个用户"""
    user_id: str
    display_name: str = ""
    username: str = ""
    email: str = ""
    last_active: float = 0.0
    last_chat_topic: str = ""
    interaction_count: int = 0
    recent_topics: list = field(default_factory=list)
    mood_estimate: str = "未知"
    first_seen: float = field(default_factory=time.time)

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_active if self.last_active else float("inf")

    @property
    def idle_label(self) -> str:
        s = self.idle_seconds
        if s < 60:
            return "刚刚活跃"
        elif s < 3600:
            return f"{int(s // 60)}分钟前"
        elif s < 86400:
            return f"{int(s // 3600)}小时前"
        else:
            return f"{int(s // 86400)}天前"


class UserRegistry:
    """意识核已知用户注册表 — 全局单例"""

    def __init__(self):
        self._users: Dict[str, KnownUser] = {}

    @staticmethod
    def _mask_email(email: str) -> str:
        """P2-#9: 邮箱脱敏 — user@example.com → u***r@example.com"""
        if not email or "@" not in email:
            return email
        local, domain = email.rsplit("@", 1)
        if len(local) <= 2:
            masked = local[0] + "***"
        else:
            masked = local[0] + "***" + local[-1]
        return f"{masked}@{domain}"

    def on_heartbeat(self, user_id: str, display_name: str = ""):
        """心跳事件 → 注册/更新用户"""
        if not user_id or user_id == "anonymous":
            return
        if user_id not in self._users:
            self._users[user_id] = KnownUser(user_id=user_id)
            logger.info("[UserRegistry] New user discovered: %s (%s)", user_id[:8], display_name or "?")
        u = self._users[user_id]
        u.last_active = time.time()
        if display_name:
            u.display_name = display_name

    def on_user_message(self, user_id: str, content: str, display_name: str = ""):
        """用户发消息 → 更新交互信息"""
        if not user_id or user_id == "anonymous":
            return
        self.on_heartbeat(user_id, display_name)
        u = self._users[user_id]
        u.interaction_count += 1
        # 简单提取话题关键词 (取前20字)
        topic_snippet = content[:20].strip()
        if topic_snippet:
            u.last_chat_topic = topic_snippet
            u.recent_topics.append(topic_snippet)
            u.recent_topics = u.recent_topics[-5:]  # 保留最近5个

    def on_user_profile(self, user_id: str, display_name: str = "", mood: str = ""):
        """用户画像更新"""
        if user_id in self._users:
            u = self._users[user_id]
            if display_name:
                u.display_name = display_name
            if mood:
                u.mood_estimate = mood

    def on_user_profile_sync(self, user_id: str, username: str = "",
                              display_name: str = "", email: str = ""):
        """从 DB 同步用户完整资料 — 每次对话请求时调用"""
        if not user_id or user_id == "anonymous":
            return
        self.on_heartbeat(user_id, display_name)
        u = self._users[user_id]
        if username:
            u.username = username
        if display_name:
            u.display_name = display_name
        if email:
            # P2-#9: 脱敏存储邮箱
            u.email = self._mask_email(email)
        logger.debug("[UserRegistry] Profile synced: %s (%s / %s)", user_id[:8], display_name, username)

    def get_user(self, user_id: str) -> Optional[KnownUser]:
        return self._users.get(user_id)

    def get_all_users(self) -> List[KnownUser]:
        return list(self._users.values())

    def get_online_users(self, idle_threshold: float = 1800) -> List[KnownUser]:
        """获取近期活跃用户 (默认30分钟内)"""
        return [u for u in self._users.values() if u.idle_seconds < idle_threshold]

    def get_most_recent_user(self) -> Optional[KnownUser]:
        """获取最近活跃的用户"""
        if not self._users:
            return None
        return max(self._users.values(), key=lambda u: u.last_active)

    def get_context_prompt(self) -> str:
        """生成"你认识的用户"上下文 (注入 InnerVoice prompt)"""
        if not self._users:
            return "暂无已知用户交互记录"

        lines = []
        for u in sorted(self._users.values(), key=lambda x: x.last_active, reverse=True)[:10]:
            name = u.display_name or u.username or f"用户{u.user_id[:8]}"
            topics = ", ".join(u.recent_topics[-3:]) if u.recent_topics else "暂无"
            identity = name
            if u.username and u.username != name:
                identity += f" (@{u.username})"
            lines.append(
                f"- {identity}: {u.idle_label}, "
                f"聊过{u.interaction_count}次, "
                f"近期话题=[{topics}], 情绪={u.mood_estimate}"
            )
        return "\n".join(lines)

    def get_expression_targets(self) -> List[str]:
        """获取可以主动表达的目标用户ID列表
        优先: 在线用户 > 最近活跃用户 > 所有用户
        """
        # 1. 在线用户 (30分钟内)
        online = self.get_online_users(1800)
        if online:
            return [u.user_id for u in online]

        # 2. 最近24小时活跃的用户
        recent = [u for u in self._users.values() if u.idle_seconds < 86400]
        if recent:
            return [u.user_id for u in recent]

        # 3. 所有已知用户
        return [u.user_id for u in self._users.values()]

    def get_stats(self) -> dict:
        return {
            "total_known": len(self._users),
            "online_30min": len(self.get_online_users(1800)),
            "online_2h": len(self.get_online_users(7200)),
        }


# 全局单例
_registry: Optional[UserRegistry] = None


def get_user_registry() -> UserRegistry:
    global _registry
    if _registry is None:
        _registry = UserRegistry()
    return _registry
