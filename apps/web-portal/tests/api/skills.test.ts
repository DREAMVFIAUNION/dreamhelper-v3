import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

vi.mock('@dreamhelp/auth', () => ({
  verifyToken: vi.fn().mockResolvedValue({ sub: 'user-1' }),
}))

vi.mock('@/lib/brain-core-url', () => ({
  brainCoreFetch: vi.fn(),
}))

afterEach(() => {
  vi.clearAllMocks()
})

describe('Skills API', () => {
  it('GET /api/skills should reject unauthenticated request', async () => {
    const { GET } = await import('@/app/api/skills/route')
    const req = new NextRequest(new URL('/api/skills', 'http://localhost:3000'))
    const res = await GET(req)

    expect(res.status).toBe(401)
    const data = await res.json()
    expect(data).toHaveProperty('error')
  })

  it('GET /api/skills with query param should proxy authenticated requests', async () => {
    const { brainCoreFetch } = await import('@/lib/brain-core-url')
    vi.mocked(brainCoreFetch).mockResolvedValue(
      new Response(JSON.stringify({ skills: [{ id: 'calculator' }] }), { status: 200 }),
    )

    const { GET } = await import('@/app/api/skills/route')
    const req = new NextRequest(new URL('/api/skills?q=calculator', 'http://localhost:3000'), {
      headers: { cookie: 'token=test-token' },
    })
    const res = await GET(req)

    expect(res.status).toBe(200)
    expect(vi.mocked(brainCoreFetch)).toHaveBeenCalledWith('/api/v1/skills/search?q=calculator')
  })

  it('GET /api/skills with category param should proxy authenticated requests', async () => {
    const { brainCoreFetch } = await import('@/lib/brain-core-url')
    vi.mocked(brainCoreFetch).mockResolvedValue(
      new Response(JSON.stringify({ skills: [{ id: 'pomodoro_timer' }] }), { status: 200 }),
    )

    const { GET } = await import('@/app/api/skills/route')
    const req = new NextRequest(new URL('/api/skills?category=daily', 'http://localhost:3000'), {
      headers: { cookie: 'token=test-token' },
    })
    const res = await GET(req)

    expect(res.status).toBe(200)
    expect(vi.mocked(brainCoreFetch)).toHaveBeenCalledWith('/api/v1/skills/category/daily')
  })
})
