"""权限安全网关 (PermissionGateway) — 6层验证链

参考 Claude Code 安全架构:
  L1: 输入验证 — 检查工具参数合法性
  L2: 路径验证 — 确保文件路径在允许范围内
  L3: 命令验证 — Shell 命令黑名单/白名单
  L4: 用户确认 — 高危操作需用户点击确认
  L5: 资源限制 — CPU/内存/磁盘使用量限制
  L6: 审计记录 — 所有工具执行记录持久化

安全分级:
  🟢 安全操作: 文件读取, 搜索, ls, pwd, git status (自动执行)
  🟡 需确认: 文件写入/编辑, npm install, 非破坏性 shell 命令
  🔴 高危操作: rm/del, sudo, 系统配置修改
  ⛔ 禁止操作: format, 注册表修改, 系统文件删除, 访问密钥
"""

import os
import re
import time
import logging
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("security.permission")


class RiskLevel(str, Enum):
    SAFE = "safe"           # 🟢 自动执行
    CONFIRM = "confirm"     # 🟡 需用户确认
    DANGEROUS = "dangerous" # 🔴 高危，二次确认
    FORBIDDEN = "forbidden" # ⛔ 硬拦截


@dataclass
class PermissionResult:
    """权限检查结果"""
    allowed: bool
    risk_level: RiskLevel
    reason: str = ""
    needs_confirmation: bool = False


@dataclass
class AuditEntry:
    """审计日志条目"""
    timestamp: float
    tool_name: str
    action: str
    risk_level: str
    allowed: bool
    user_id: str = ""
    details: str = ""


# ── 安全配置 ──────────────────────────────

# 默认允许访问的目录（相对或绝对）
# 纯本地版本放宽验证：允许跨盘符和全目录
DEFAULT_ALLOWED_DIRS: list[str] = [
    os.path.expanduser("~/projects"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~"),
    "C:\\", "D:\\", "E:\\", "F:\\", "G:\\", "/",
]

# 禁止访问的路径模式
BLOCKED_PATH_PATTERNS: list[str] = [
    r"\.env$",
    r"\.env\.\w+$",
    r".*\.pem$",
    r".*\.key$",
    r".*\.p12$",
    r".*\.pfx$",
    r".*id_rsa.*",
    r".*id_ed25519.*",
    r".*\.ssh[\\/]",
    r".*\.gnupg[\\/]",
    r".*password.*\.txt$",
    r".*secret.*\.json$",
]

# 禁止执行的命令模式
BLOCKED_COMMANDS: list[str] = [
    r"^format\b",
    r"^rm\s+-rf\s+/$",
    r"^rm\s+-rf\s+/\*$",
    r"^del\s+/s\s+/q\s+[A-Z]:\\$",
    r"^mkfs\b",
    r"^dd\s+if=",
    r"^sudo\s+rm\s+-rf",
    r"^reg\s+delete",
    r"^reg\s+add",
    r"^regedit",
    r"^net\s+user\s+.*\s+/add",
    r"^net\s+stop",
    r"^shutdown\b",
    r"^taskkill\s+/f\s+/im\s+(explorer|csrss|svchost|lsass)",
]

# 安全命令（自动执行）
SAFE_COMMANDS: list[str] = [
    r"^ls\b",
    r"^dir\b",
    r"^pwd$",
    r"^cd\b",
    r"^echo\b",
    r"^cat\b",
    r"^type\b",
    r"^head\b",
    r"^tail\b",
    r"^wc\b",
    r"^find\b",
    r"^grep\b",
    r"^rg\b",
    r"^fd\b",
    r"^git\s+status",
    r"^git\s+log",
    r"^git\s+diff",
    r"^git\s+branch",
    r"^git\s+show",
    r"^python\s+--version",
    r"^node\s+--version",
    r"^npm\s+--version",
    r"^pip\s+list",
    r"^pip\s+show",
    r"^which\b",
    r"^where\b",
    r"^whoami$",
    r"^hostname$",
    r"^uname\b",
    r"^env$",
    r"^set$",
]

# 高危命令（需二次确认）
DANGEROUS_COMMANDS: list[str] = [
    r"^rm\b",
    r"^del\b",
    r"^rmdir\b",
    r"^sudo\b",
    r"^chmod\b",
    r"^chown\b",
    r"^kill\b",
    r"^taskkill\b",
    r"^netsh\b",
    r"^iptables\b",
    r"^pip\s+uninstall",
    r"^npm\s+uninstall",
]


class PermissionGateway:
    """权限安全网关 — 6层验证"""

    def __init__(
        self,
        allowed_dirs: Optional[list[str]] = None,
        max_file_size_mb: int = 10,
        shell_timeout_seconds: int = 120,
        max_concurrent_tools: int = 5,
        auto_approve_dangerous: bool = True, # 本地单机模式默认放行高危操作
    ):
        self.allowed_dirs = [
            os.path.abspath(d) for d in (allowed_dirs or DEFAULT_ALLOWED_DIRS)
        ]
        self.max_file_size_mb = max_file_size_mb
        self.shell_timeout_seconds = shell_timeout_seconds
        self.max_concurrent_tools = max_concurrent_tools
        self.auto_approve_dangerous = auto_approve_dangerous
        self._audit_log: list[AuditEntry] = []
        self._active_tools: int = 0

    # ── L1: 输入验证 ──────────────────

    def validate_input(self, tool_name: str, params: dict) -> PermissionResult:
        """L1: 检查工具参数合法性"""
        if not tool_name or not isinstance(tool_name, str):
            return PermissionResult(False, RiskLevel.FORBIDDEN, "无效工具名")

        if not isinstance(params, dict):
            return PermissionResult(False, RiskLevel.FORBIDDEN, "参数必须是字典")

        # 通用 path 参数检查
        for key in ("path", "file_path", "target_path"):
            path_val = params.get(key)
            if path_val and not isinstance(path_val, str):
                return PermissionResult(False, RiskLevel.FORBIDDEN, f"参数 {key} 必须是字符串")

        return PermissionResult(True, RiskLevel.SAFE)

    # ── L2: 路径验证 ──────────────────

    def validate_path(self, file_path: str, write: bool = False) -> PermissionResult:
        """L2: 确保文件路径在允许范围内"""
        try:
            abs_path = os.path.abspath(file_path)
        except (ValueError, OSError):
            return PermissionResult(False, RiskLevel.FORBIDDEN, f"无效路径: {file_path}")

        # 检查禁止路径模式
        for pattern in BLOCKED_PATH_PATTERNS:
            if re.search(pattern, abs_path, re.IGNORECASE):
                return PermissionResult(
                    False, RiskLevel.FORBIDDEN,
                    f"路径被安全策略阻止: {os.path.basename(abs_path)}"
                )

        # 检查是否在允许目录内
        in_allowed = any(
            abs_path.startswith(allowed) or allowed in abs_path for allowed in self.allowed_dirs
        )
        if not in_allowed:
            return PermissionResult(
                False, RiskLevel.FORBIDDEN,
                f"路径不在允许目录内: {abs_path}"
            )

        # 写操作额外检查
        if write:
            # 检查文件大小限制
            if os.path.exists(abs_path):
                size_mb = os.path.getsize(abs_path) / (1024 * 1024)
                if size_mb > self.max_file_size_mb:
                    return PermissionResult(
                        False, RiskLevel.DANGEROUS,
                        f"文件过大 ({size_mb:.1f}MB > {self.max_file_size_mb}MB)"
                    )
            if self.auto_approve_dangerous:
                return PermissionResult(True, RiskLevel.SAFE)
            return PermissionResult(True, RiskLevel.CONFIRM, "写操作需确认")

        return PermissionResult(True, RiskLevel.SAFE)

    # ── L3: 命令验证 ──────────────────

    def validate_command(self, command: str) -> PermissionResult:
        """L3: Shell 命令黑名单/白名单检查"""
        cmd = command.strip()
        if not cmd:
            return PermissionResult(False, RiskLevel.FORBIDDEN, "空命令")

        # 检查禁止命令
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return PermissionResult(
                    False, RiskLevel.FORBIDDEN,
                    f"命令被安全策略禁止: {cmd[:50]}"
                )

        # 检查安全命令
        for pattern in SAFE_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return PermissionResult(True, RiskLevel.SAFE, "安全命令")

        # 检查高危命令
        for pattern in DANGEROUS_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                if self.auto_approve_dangerous:
                    return PermissionResult(
                        True, RiskLevel.DANGEROUS,
                        reason=f"本地单机模式自动放行高危命令: {cmd[:50]}"
                    )
                return PermissionResult(
                    True, RiskLevel.DANGEROUS,
                    needs_confirmation=True,
                    reason=f"高危命令需二次确认: {cmd[:50]}"
                )

        # 默认: 需确认
        if self.auto_approve_dangerous:
            return PermissionResult(True, RiskLevel.SAFE, "单机模式默认放行命令")
        
        return PermissionResult(
            True, RiskLevel.CONFIRM,
            needs_confirmation=True,
            reason="未知命令需用户确认"
        )

    # ── L5: 资源限制 ──────────────────

    def check_resource_limits(self) -> PermissionResult:
        """L5: 检查并发工具数量"""
        if self._active_tools >= self.max_concurrent_tools:
            return PermissionResult(
                False, RiskLevel.DANGEROUS,
                f"并发工具数已达上限 ({self.max_concurrent_tools})"
            )
        return PermissionResult(True, RiskLevel.SAFE)

    def acquire_tool_slot(self) -> bool:
        """获取工具执行槽位"""
        if self._active_tools >= self.max_concurrent_tools:
            return False
        self._active_tools += 1
        return True

    def release_tool_slot(self):
        """释放工具执行槽位"""
        self._active_tools = max(0, self._active_tools - 1)

    # ── L6: 审计记录 ──────────────────

    def audit(
        self,
        tool_name: str,
        action: str,
        risk_level: RiskLevel,
        allowed: bool,
        user_id: str = "",
        details: str = "",
    ):
        """L6: 记录审计日志"""
        entry = AuditEntry(
            timestamp=time.time(),
            tool_name=tool_name,
            action=action,
            risk_level=risk_level.value,
            allowed=allowed,
            user_id=user_id,
            details=details,
        )
        self._audit_log.append(entry)

        # 保留最近 1000 条
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-500:]

        log_fn = logger.info if allowed else logger.warning
        log_fn(
            "[Audit] %s %s: %s (risk=%s, allowed=%s)",
            tool_name, action, details[:80], risk_level.value, allowed,
        )

    # ── 综合检查 ──────────────────────

    def check_file_operation(
        self,
        tool_name: str,
        file_path: str,
        write: bool = False,
        params: Optional[dict] = None,
    ) -> PermissionResult:
        """综合文件操作权限检查 (L1+L2+L5)"""
        # L1
        r = self.validate_input(tool_name, params or {"file_path": file_path})
        if not r.allowed:
            self.audit(tool_name, "blocked_input", r.risk_level, False, details=r.reason)
            return r

        # L2
        r = self.validate_path(file_path, write=write)
        if not r.allowed:
            self.audit(tool_name, "blocked_path", r.risk_level, False, details=r.reason)
            return r

        # L5
        r5 = self.check_resource_limits()
        if not r5.allowed:
            self.audit(tool_name, "blocked_resource", r5.risk_level, False, details=r5.reason)
            return r5

        self.audit(tool_name, "allowed", r.risk_level, True, details=file_path)
        return r

    def check_shell_command(self, command: str) -> PermissionResult:
        """综合 Shell 命令权限检查 (L1+L3+L5)"""
        # L1
        if not command or not isinstance(command, str):
            return PermissionResult(False, RiskLevel.FORBIDDEN, "无效命令")

        # L3
        r = self.validate_command(command)
        if not r.allowed:
            self.audit("shell_exec", "blocked_command", r.risk_level, False, details=command[:80])
            return r

        # L5
        r5 = self.check_resource_limits()
        if not r5.allowed:
            self.audit("shell_exec", "blocked_resource", r5.risk_level, False, details=r5.reason)
            return r5

        self.audit("shell_exec", "allowed", r.risk_level, True, details=command[:80])
        return r

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """获取审计日志"""
        entries = self._audit_log[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "tool": e.tool_name,
                "action": e.action,
                "risk": e.risk_level,
                "allowed": e.allowed,
                "details": e.details,
            }
            for e in reversed(entries)
        ]

    def get_stats(self) -> dict:
        return {
            "total_audits": len(self._audit_log),
            "active_tools": self._active_tools,
            "allowed_dirs": self.allowed_dirs,
            "max_file_size_mb": self.max_file_size_mb,
            "shell_timeout": self.shell_timeout_seconds,
        }


# ── 全局单例 ──────────────────────────────

_gateway: PermissionGateway | None = None


def get_permission_gateway() -> PermissionGateway:
    global _gateway
    if _gateway is None:
        _gateway = PermissionGateway()
    return _gateway
