import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// ═══ GET /api/chat/sessions — 获取用户的会话列表 ═══

export async function GET(req: NextRequest) {
  try {
    const userId = getLocalUserId()

    const sessions = await prisma.chatSession.findMany({
      where: { userId, status: 'active' },
      select: {
        id: true,
        title: true,
        agentId: true,
        metadata: true,
        createdAt: true,
        updatedAt: true,
        _count: { select: { messages: true } },
      },
      orderBy: { updatedAt: 'desc' },
    })

    return NextResponse.json({
      success: true,
      sessions: sessions.map((s) => ({
        id: s.id,
        title: s.title || '新对话',
        agentId: s.agentId,
        messageCount: s._count.messages,
        metadata: s.metadata,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
      })),
    })
  } catch (error) {
    console.error('list sessions failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// ═══ POST /api/chat/sessions — 创建新会话 ═══

export async function POST(req: NextRequest) {
  try {
    const userId = getLocalUserId()

    let body: { title?: string; agentId?: string } = {}
    try {
      body = (await req.json()) as { title?: string; agentId?: string }
    } catch {
      // 空 body 也可以，使用默认值
    }

    const session = await prisma.chatSession.create({
      data: {
        user: { connect: { id: userId } },
        ...(body.agentId ? { agent: { connect: { id: body.agentId } } } : {}),
        title: body.title || null,
      },
      select: {
        id: true,
        title: true,
        agentId: true,
        createdAt: true,
        updatedAt: true,
      },
    })

    return NextResponse.json({
      success: true,
      session: {
        id: session.id,
        title: session.title || '新对话',
        agentId: session.agentId,
        messageCount: 0,
        createdAt: session.createdAt,
        updatedAt: session.updatedAt,
      },
    }, { status: 201 })
  } catch (error) {
    console.error('create session failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
