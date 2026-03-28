import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'

// ═══ GET /api/admin/users/[id]/sessions — 用户的聊天会话列表 ═══

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  try {
    const sessions = await prisma.chatSession.findMany({
      where: { userId: id },
      select: {
        id: true,
        title: true,
        status: true,
        createdAt: true,
        updatedAt: true,
        _count: { select: { messages: true } },
      },
      orderBy: { updatedAt: 'desc' },
      take: 50,
    })

    return NextResponse.json({
      success: true,
      sessions: sessions.map((s) => ({
        id: s.id,
        title: s.title,
        status: s.status,
        messageCount: s._count.messages,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
      })),
    })
  } catch (error) {
    console.error('admin user sessions failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
