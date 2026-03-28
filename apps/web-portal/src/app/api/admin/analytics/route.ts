import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'

// GET /api/admin/analytics — 按天聚合的数据分析
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const days = Math.min(90, Math.max(7, parseInt(searchParams.get('days') || '14')))

    // 生成最近 N 天的日期范围
    const now = new Date()
    const dateLabels: string[] = []
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(d.getDate() - i)
      dateLabels.push(d.toISOString().slice(0, 10))
    }

    const startDate = new Date(dateLabels[0]!)
    startDate.setHours(0, 0, 0, 0)

    // 查询原始数据
    const [allUsers, allSessions, allMessages] = await Promise.all([
      prisma.user.findMany({
        where: { createdAt: { gte: startDate } },
        select: { createdAt: true },
      }),
      prisma.chatSession.findMany({
        where: { createdAt: { gte: startDate } },
        select: { createdAt: true },
      }),
      prisma.message.findMany({
        where: { createdAt: { gte: startDate } },
        select: { createdAt: true },
      }),
    ])

    // 按天聚合
    function countByDay(items: { createdAt: Date }[]): Record<string, number> {
      const map: Record<string, number> = {}
      for (const item of items) {
        const day = item.createdAt.toISOString().slice(0, 10)
        map[day] = (map[day] || 0) + 1
      }
      return map
    }

    const usersByDay = countByDay(allUsers)
    const sessionsByDay = countByDay(allSessions)
    const messagesByDay = countByDay(allMessages)

    const series = {
      labels: dateLabels,
      users: dateLabels.map((d) => usersByDay[d] || 0),
      sessions: dateLabels.map((d) => sessionsByDay[d] || 0),
      messages: dateLabels.map((d) => messagesByDay[d] || 0),
    }

    // 汇总
    const totals = {
      users: allUsers.length,
      sessions: allSessions.length,
      messages: allMessages.length,
    }

    return NextResponse.json({ success: true, days, series, totals })
  } catch (error) {
    console.error('admin analytics failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
