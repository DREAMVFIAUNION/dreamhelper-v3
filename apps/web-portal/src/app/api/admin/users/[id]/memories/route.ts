import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'

// ═══ GET /api/admin/users/[id]/memories — 用户的长期记忆/画像 ═══

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  try {
    const memories = await prisma.userMemory.findMany({
      where: { userId: id },
      select: {
        id: true,
        key: true,
        value: true,
        confidence: true,
        source: true,
        createdAt: true,
        updatedAt: true,
      },
      orderBy: { updatedAt: 'desc' },
    })

    return NextResponse.json({ success: true, memories })
  } catch (error) {
    console.error('admin user memories failed:', error)
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 })
  }
}
