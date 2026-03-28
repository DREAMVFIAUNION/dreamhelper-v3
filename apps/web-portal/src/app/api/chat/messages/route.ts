import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// ═══ POST /api/chat/messages — 保存消息 (user + assistant) ═══

export async function POST(req: NextRequest) {
  try {
    const userId = getLocalUserId()

    let body: {
      sessionId: string
      messages: Array<{
        role: string
        content: string
        thinking?: string
        toolCalls?: unknown
        tokens?: number
        latencyMs?: number
      }>
    }

    try {
      body = (await req.json()) as typeof body
    } catch {
      return NextResponse.json({ success: false, error: '请求格式错误' }, { status: 400 })
    }

    if (!body.sessionId || !body.messages?.length) {
      return NextResponse.json({ success: false, error: '参数缺失' }, { status: 400 })
    }

    // 验证会话归属
    const session = await prisma.chatSession.findFirst({
      where: { id: body.sessionId, userId, status: 'active' },
      select: { id: true, title: true },
    })

    if (!session) {
      return NextResponse.json({ success: false, error: '会话不存在' }, { status: 404 })
    }

    // 批量创建消息
    const created = await prisma.message.createMany({
      data: body.messages.map((m) => ({
        sessionId: body.sessionId,
        role: m.role,
        content: m.content,
        thinking: m.thinking ? JSON.parse(JSON.stringify(m.thinking)) : undefined,
        toolCalls: m.toolCalls ? JSON.parse(JSON.stringify(m.toolCalls)) : undefined,
        tokens: m.tokens,
        latencyMs: m.latencyMs,
      })),
    })

    // 如果会话没有标题，用第一条用户消息自动生成标题
    if (!session.title) {
      const firstUserMsg = body.messages.find((m) => m.role === 'user')
      if (firstUserMsg) {
        const autoTitle = firstUserMsg.content.slice(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '')
        await prisma.chatSession.update({
          where: { id: body.sessionId },
          data: { title: autoTitle },
        })
      }
    }

    // 更新会话 updatedAt
    await prisma.chatSession.update({
      where: { id: body.sessionId },
      data: { updatedAt: new Date() },
    })

    return NextResponse.json({ success: true, count: created.count })
  } catch (error) {
    console.error('save messages failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
