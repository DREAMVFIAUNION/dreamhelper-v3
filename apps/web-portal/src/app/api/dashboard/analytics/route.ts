import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// GET /api/dashboard/analytics — 用户个人使用统计
export async function GET(req: NextRequest) {
  try {
    const userId = getLocalUserId()
    const { searchParams } = new URL(req.url)
    const days = Math.min(30, Math.max(7, parseInt(searchParams.get('days') || '14')))

    const now = new Date()
    const dateLabels: string[] = []
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      dateLabels.push(d.toISOString().slice(0, 10))
    }

    const startDate = new Date(dateLabels[0]!)
    startDate.setHours(0, 0, 0, 0)

    const [sessions, messages, totalSessions, totalMessages] = await Promise.all([
      prisma.chatSession.findMany({
        where: { userId, createdAt: { gte: startDate } },
        select: { createdAt: true },
      }),
      prisma.message.findMany({
        where: { session: { userId }, createdAt: { gte: startDate } },
        select: { createdAt: true, role: true },
      }),
      prisma.chatSession.count({ where: { userId } }),
      prisma.message.count({ where: { session: { userId } } }),
    ])

    function countByDay(items: { createdAt: Date }[]): Record<string, number> {
      const map: Record<string, number> = {}
      for (const item of items) {
        const day = item.createdAt.toISOString().slice(0, 10)
        map[day] = (map[day] || 0) + 1
      }
      return map
    }

    const sessionsByDay = countByDay(sessions)
    const messagesByDay = countByDay(messages)
    const userMsgsByDay = countByDay(messages.filter((m) => m.role === 'user'))

    const series = {
      labels: dateLabels,
      sessions: dateLabels.map((d) => sessionsByDay[d] || 0),
      messages: dateLabels.map((d) => messagesByDay[d] || 0),
      userMessages: dateLabels.map((d) => userMsgsByDay[d] || 0),
    }

    const totals = {
      sessions: totalSessions,
      messages: totalMessages,
      periodSessions: sessions.length,
      periodMessages: messages.length,
    }

    return NextResponse.json({ success: true, days, series, totals })
  } catch (error) {
    console.error('dashboard analytics failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
