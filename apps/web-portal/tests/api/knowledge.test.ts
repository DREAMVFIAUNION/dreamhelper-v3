import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'

function mockReq(url: string, init?: RequestInit): NextRequest {
  return new NextRequest(new URL(url, 'http://localhost:3000'), init as any)
}

describe.skip('Knowledge API', () => {
  it('GET /api/knowledge should reject unauthenticated request', async () => {
    const { GET } = await import('@/app/api/knowledge/route')
    const req = mockReq('/api/knowledge')
    const res = await GET(req)
    expect(res.status).toBe(401)
    const data = await res.json()
    expect(data.success).toBe(false)
  })

  it('POST /api/knowledge should reject unauthenticated request', async () => {
    const { POST } = await import('@/app/api/knowledge/route')
    const req = mockReq('/api/knowledge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: 'test doc' }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
    const data = await res.json()
    expect(data.success).toBe(false)
  })
})
