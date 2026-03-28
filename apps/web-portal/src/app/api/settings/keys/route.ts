import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@dreamhelp/database'
import { getLocalUserId } from '@/lib/local-user'

export async function GET() {
  const userId = getLocalUserId()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const configs = await prisma.systemConfig.findMany({
      where: { key: { endsWith: '_API_KEY' } },
    })
    
    const keys = configs.reduce((acc, curr) => {
      acc[curr.key] = curr.value
      return acc
    }, {} as Record<string, string>)

    return NextResponse.json(keys)
  } catch (error) {
    console.error('[API Keys GET] Error:', error)
    return NextResponse.json({ error: 'Failed' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  const userId = getLocalUserId()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  try {
    const body = await req.json()
    
    // Body should be an object containing keys like { OPENAI_API_KEY: 'sk-...', DEEPSEEK_API_KEY: '...' }
    const promises = Object.entries(body).map(async ([key, value]) => {
      if (!key.endsWith('_API_KEY') || typeof value !== 'string') return

      if (value.trim() === '') {
        // Delete if empty
        await prisma.systemConfig.deleteMany({ where: { key } })
      } else {
        // Upsert if provided
        await prisma.systemConfig.upsert({
          where: { key },
          update: { value, updatedAt: new Date() },
          create: { key, value, description: `User provided ${key}`, createdAt: new Date(), updatedAt: new Date() },
        })
      }
    })

    await Promise.all(promises)
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('[API Keys POST] Error:', error)
    return NextResponse.json({ error: 'Failed' }, { status: 500 })
  }
}
