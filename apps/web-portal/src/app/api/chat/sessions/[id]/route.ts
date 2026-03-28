import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// ═══ GET /api/chat/sessions/[id] — 获取单个会话 (含消息) ═══

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const userId = getLocalUserId()
    const { id } = await params

    const session = await prisma.chatSession.findFirst({
      where: { id, userId, status: 'active' },
      select: {
        id: true,
        title: true,
        agentId: true,
        metadata: true,
        createdAt: true,
        updatedAt: true,
        messages: {
          select: {
            id: true,
            role: true,
            content: true,
            thinking: true,
            toolCalls: true,
            tokens: true,
            createdAt: true,
          },
          orderBy: { createdAt: 'asc' },
        },
      },
    })

    if (!session) {
      return NextResponse.json({ success: false, error: '会话不存在' }, { status: 404 })
    }

    return NextResponse.json({
      success: true,
      session: {
        id: session.id,
        title: session.title || '新对话',
        agentId: session.agentId,
        metadata: session.metadata,
        createdAt: session.createdAt,
        updatedAt: session.updatedAt,
        messages: session.messages,
      },
    })
  } catch (error) {
    console.error('get session failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// ═══ PATCH /api/chat/sessions/[id] — 更新会话 (重命名等) ═══

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const userId = getLocalUserId()
    const { id } = await params

    let body: { title?: string }
    try {
      body = (await req.json()) as { title?: string }
    } catch {
      return NextResponse.json({ success: false, error: '请求格式错误' }, { status: 400 })
    }

    // 确保会话属于当前用户
    const existing = await prisma.chatSession.findFirst({
      where: { id, userId },
      select: { id: true },
    })

    if (!existing) {
      return NextResponse.json({ success: false, error: '会话不存在' }, { status: 404 })
    }

    const updated = await prisma.chatSession.update({
      where: { id },
      data: { title: body.title },
      select: { id: true, title: true, updatedAt: true },
    })

    return NextResponse.json({ success: true, session: updated })
  } catch (error) {
    console.error('update session failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}

// ═══ DELETE /api/chat/sessions/[id] — 软删除会话 ═══

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const userId = getLocalUserId()
    const { id } = await params

    const existing = await prisma.chatSession.findFirst({
      where: { id, userId },
      select: { id: true },
    })

    if (!existing) {
      return NextResponse.json({ success: false, error: '会话不存在' }, { status: 404 })
    }

    // 软删除：标记为 archived
    await prisma.chatSession.update({
      where: { id },
      data: { status: 'archived' },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('delete session failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
