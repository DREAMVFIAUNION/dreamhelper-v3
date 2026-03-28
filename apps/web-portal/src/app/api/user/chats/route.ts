import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

// DELETE /api/user/chats — 删除当前用户的所有对话
export async function DELETE(req: NextRequest) {
  try {
    const userId = getLocalUserId()

    // 先删除所有消息，再删除会话
    const sessions = await prisma.chatSession.findMany({
      where: { userId },
      select: { id: true },
    })

    const sessionIds = sessions.map((s) => s.id)

    if (sessionIds.length > 0) {
      await prisma.message.deleteMany({
        where: { sessionId: { in: sessionIds } },
      })
      await prisma.chatSession.deleteMany({
        where: { userId },
      })
    }

    return NextResponse.json({
      success: true,
      deleted: sessionIds.length,
    })
  } catch (error) {
    console.error('delete chats failed:', error)
    return NextResponse.json({ success: false, error: '删除失败' }, { status: 500 })
  }
}
