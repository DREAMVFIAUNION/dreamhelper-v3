import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// GET /api/user/export?format=json|markdown
export async function GET(req: NextRequest) {
  try {
    const userId = getLocalUserId()
    const format = req.nextUrl.searchParams.get('format') || 'json'

    // 获取用户信息
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { id: true, email: true, username: true, createdAt: true },
    })

    // 获取所有会话和消息
    const sessions = await prisma.chatSession.findMany({
      where: { userId },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' },
          select: { role: true, content: true, createdAt: true },
        },
      },
      orderBy: { createdAt: 'desc' },
    })

    if (format === 'markdown') {
      let md = `# DreamHelp 数据导出\n\n`
      md += `- **用户**: ${user?.username ?? user?.email ?? userId}\n`
      md += `- **导出时间**: ${new Date().toISOString()}\n`
      md += `- **会话数**: ${sessions.length}\n\n`

      for (const session of sessions) {
        md += `---\n\n## ${session.title || '未命名会话'}\n\n`
        md += `*创建于 ${session.createdAt.toISOString()}*\n\n`
        for (const msg of session.messages) {
          const role = msg.role === 'user' ? '👤 用户' : '🤖 助手'
          md += `**${role}** *(${msg.createdAt.toISOString()})*\n\n${msg.content}\n\n`
        }
      }

      return new NextResponse(md, {
        headers: {
          'Content-Type': 'text/markdown; charset=utf-8',
          'Content-Disposition': `attachment; filename="dreamhelp-export.md"`,
        },
      })
    }

    // JSON format
    const data = {
      exportedAt: new Date().toISOString(),
      user,
      sessions: sessions.map((s) => ({
        id: s.id,
        title: s.title,
        createdAt: s.createdAt,
        messages: s.messages,
      })),
    }

    return new NextResponse(JSON.stringify(data, null, 2), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Disposition': `attachment; filename="dreamhelp-export.json"`,
      },
    })
  } catch (error) {
    console.error('export failed:', error)
    return NextResponse.json({ success: false, error: '导出失败' }, { status: 500 })
  }
}
