/**
 * Next.js API Route — 代理 brain-core 的 chat/completions SSE
 * 前端请求 /api/chat/completions → brain-core:8000/api/v1/chat/completions
 *
 * 增强: 当请求包含 sessionId 时，从 DB 加载历史消息拼入上下文
 */

import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

import { brainCoreFetch } from '@/lib/brain-core-url'
const MAX_HISTORY_MESSAGES = 50

export async function POST(request: NextRequest) {
  const body = (await request.json()) as {
    session_id?: string
    content?: string
    message?: string
    messages?: Array<{ role: string; content: string }>
    stream?: boolean
    user_id?: string
    user_profile?: { username: string; display_name: string; email: string; tier_level: number }
  }

  const userId = getLocalUserId()

  // 如果有 sessionId，从 DB 加载历史消息拼入上下文
  if (body.session_id && userId) {
    try {
      const session = await prisma.chatSession.findFirst({
        where: { id: body.session_id, userId, status: 'active' },
        select: { id: true },
      })

      if (session) {
        const historyMessages = await prisma.message.findMany({
          where: { sessionId: session.id },
          select: { role: true, content: true },
          orderBy: { createdAt: 'asc' },
          take: MAX_HISTORY_MESSAGES,
        })

        // 将历史消息注入请求体，brain-core 会读取 messages 字段
        if (historyMessages.length > 0) {
          body.messages = historyMessages.map((m) => ({
            role: m.role,
            content: m.content,
          }))
        }
      }
    } catch (err) {
      console.error('[completions] load history failed:', err)
      // 不阻断请求，降级为无历史
    }
  }

  // 注入 user_id + 用户资料供 brain-core 使用 (记忆/画像/身份识别)
  if (userId) {
    body.user_id = userId
    try {
      const dbUser = await prisma.user.findUnique({
        where: { id: userId },
        select: { username: true, displayName: true, email: true, tierLevel: true },
      })
      if (dbUser) {
        body.user_profile = {
          username: dbUser.username,
          display_name: dbUser.displayName || dbUser.username,
          email: dbUser.email,
          tier_level: dbUser.tierLevel,
        }
      }
    } catch { /* DB lookup failed, degrade gracefully */ }
  }

  try {
    const resp = await brainCoreFetch('/api/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!resp.ok) {
      return NextResponse.json(
        { error: 'Brain-core error', status: resp.status },
        { status: resp.status },
      )
    }

    // 非流式
    if (body.stream === false) {
      const data = await resp.json()
      return NextResponse.json(data)
    }

    // 流式：透传 SSE
    if (!resp.body) {
      return NextResponse.json({ error: 'No response body' }, { status: 502 })
    }

    return new Response(resp.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })
  } catch (error) {
    console.error('[completions] proxy failed:', error)
    return NextResponse.json(
      { error: 'Brain-core 连接失败，请确认服务已启动' },
      { status: 502 },
    )
  }
}
