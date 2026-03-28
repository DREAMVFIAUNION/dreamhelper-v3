import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// GET /api/dashboard/stats — 用户侧 Dashboard 概览数据
export async function GET(req: NextRequest) {
  try {
    const userId = getLocalUserId()
    const todayStart = new Date(new Date().setHours(0, 0, 0, 0))

    const [
      totalSessions,
      todaySessions,
      totalMessages,
      todayMessages,
      totalDocs,
      recentSessions,
    ] = await Promise.all([
      prisma.chatSession.count({ where: { userId, status: 'active' } }),
      prisma.chatSession.count({ where: { userId, status: 'active', createdAt: { gte: todayStart } } }),
      prisma.message.count({ where: { session: { userId } } }),
      prisma.message.count({ where: { session: { userId }, createdAt: { gte: todayStart } } }),
      prisma.document.count({ where: { knowledgeBase: { ownerId: userId } } }),
      prisma.chatSession.findMany({
        where: { userId, status: 'active' },
        orderBy: { updatedAt: 'desc' },
        take: 5,
        select: {
          id: true,
          title: true,
          updatedAt: true,
          _count: { select: { messages: true } },
        },
      }),
    ])

    return NextResponse.json({
      success: true,
      stats: {
        totalSessions,
        todaySessions,
        totalMessages,
        todayMessages,
        totalDocs,
      },
      recentSessions: recentSessions.map((s) => ({
        id: s.id,
        title: s.title,
        updatedAt: s.updatedAt,
        messageCount: s._count.messages,
      })),
    })
  } catch (error) {
    console.error('dashboard stats failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
