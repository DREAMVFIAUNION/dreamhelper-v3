import { NextRequest, NextResponse } from 'next/server'
import { brainCoreFetch } from '@/lib/brain-core-url'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const res = await brainCoreFetch('/api/v1/proactive/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data)
  } catch (e) {
    return NextResponse.json({ status: 'error' })
  }
}
