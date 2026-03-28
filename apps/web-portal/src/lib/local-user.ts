/**
 * 本地用户常量 — 免注册模式
 *
 * 梦帮小助采用 local-first 模式，无需注册登录。
 * 所有数据归属于单一本地用户。
 */

/** 本地默认用户 ID (固定 UUID, 与 seed 脚本一致) */
export const LOCAL_USER_ID = '00000000-0000-0000-0000-000000000001'

/** 本地默认用户对象 */
export const LOCAL_USER = {
  id: LOCAL_USER_ID,
  email: 'local@dreamhelper.local',
  username: 'local',
  displayName: '本地用户',
  avatarUrl: null as string | null,
  tierLevel: 0,
  emailVerified: true,
} as const

/** 获取当前用户 ID (本地模式始终返回固定 ID) */
export function getLocalUserId(): string {
  return LOCAL_USER_ID
}
