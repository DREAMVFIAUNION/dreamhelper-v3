import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'

// GET /api/admin/sessions — 管理员查看所有会话 (分页+筛选)
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const page = Math.max(1, parseInt(searchParams.get('page') || '1'))
    const limit = Math.min(50, Math.max(1, parseInt(searchParams.get('limit') || '20')))
    const status = searchParams.get('status') || undefined
    const userId = searchParams.get('userId') || undefined
    const q = searchParams.get('q') || undefined

    const where: Record<string, unknown> = {}
    if (status) where.status = status
    if (userId) where.userId = userId
    if (q) where.title = { contains: q }

    const [total, sessions] = await Promise.all([
      prisma.chatSession.count({ where }),
      prisma.chatSession.findMany({
        where,
        orderBy: { updatedAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
        select: {
          id: true,
          title: true,
          status: true,
          createdAt: true,
          updatedAt: true,
          userId: true,
          user: { select: { username: true, email: true } },
          _count: { select: { messages: true } },
        },
      }),
    ])

    return NextResponse.json({
      success: true,
      sessions: sessions.map((s) => ({
        id: s.id,
        title: s.title,
        status: s.status,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
        userId: s.userId,
        username: s.user.username,
        email: s.user.email,
        messageCount: s._count.messages,
      })),
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    })
  } catch (error) {
    console.error('admin sessions failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
