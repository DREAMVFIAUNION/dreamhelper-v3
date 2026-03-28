import { NextRequest, NextResponse } from 'next/server'

/**
 * 纯本地个人应用中间件 (No-Auth Local Mode)
 *
 * - 根路由 '/' 重定向到 '/chat'
 * - 所有 API 和静态资源直接放行
 * - 所有的前端页面 (dashboard 等) 均无需 JWT 鉴权
 */

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // 静态资源 / API 直接放行
  if (pathname.startsWith('/api/') || pathname.startsWith('/_next/')) {
    return NextResponse.next()
  }

  // 根路由重定向到 /chat
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/chat', req.url))
  }

  // 所有其他路由直接放行
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|logo|og-image).*)'],
}
