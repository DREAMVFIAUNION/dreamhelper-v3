import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'

// ═══ GET /api/admin/stats — 管理面板统计数据 ═══

export async function GET(req: NextRequest) {
  try {
    const todayStart = new Date(new Date().setHours(0, 0, 0, 0))

    // 并行查询统计数据
    const [
      totalUsers,
      activeUsers,
      totalSessions,
      activeSessions,
      totalMessages,
      totalAgents,
      totalKnowledgeBases,
      todayUsers,
      todayMessages,
      recentUsers,
      recentSessions,
    ] = await Promise.all([
      prisma.user.count(),
      prisma.user.count({ where: { status: 'active' } }),
      prisma.chatSession.count(),
      prisma.chatSession.count({ where: { status: 'active' } }),
      prisma.message.count(),
      prisma.agent.count(),
      prisma.knowledgeBase.count(),
      prisma.user.count({ where: { createdAt: { gte: todayStart } } }),
      prisma.message.count({ where: { createdAt: { gte: todayStart } } }),
      prisma.user.findMany({
        orderBy: { createdAt: 'desc' },
        take: 5,
        select: { id: true, username: true, email: true, createdAt: true, status: true },
      }),
      prisma.chatSession.findMany({
        where: { status: 'active' },
        orderBy: { updatedAt: 'desc' },
        take: 5,
        select: { id: true, title: true, updatedAt: true, userId: true },
      }),
    ])

    return NextResponse.json({
      success: true,
      stats: {
        totalUsers,
        activeUsers,
        totalSessions,
        activeSessions,
        totalMessages,
        totalAgents,
        totalKnowledgeBases,
        todayUsers,
        todayMessages,
      },
      recentUsers,
      recentSessions,
    })
  } catch (error) {
    console.error('admin stats failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
