import { NextRequest, NextResponse } from 'next/server'
import { brainCoreFetch } from '@/lib/brain-core-url'
import { getLocalUserId } from '@/lib/local-user'

export async function GET(req: NextRequest) {
  const userId = getLocalUserId()

  try {
    const res = await brainCoreFetch(`/api/v1/proactive/messages/${userId}`)
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ user_id: userId, messages: [] })
  }
}
