import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

// Helper to create mock requests
function mockRequest(url: string, init?: { method?: string; headers?: Record<string, string>; body?: string }): NextRequest {
  return new NextRequest(new URL(url, 'http://localhost:3000'), init as any)
}

vi.mock('@dreamhelp/database', () => ({
  prisma: {
    user: {
      findUnique: vi.fn(),
      update: vi.fn(),
      create: vi.fn(),
    },
  },
}))

beforeEach(async () => {
  vi.clearAllMocks()
  const { prisma } = await import('@dreamhelp/database')
  vi.mocked(prisma.user.findUnique).mockResolvedValue(null)
})

describe('Auth API Routes', () => {
  describe('POST /api/auth/login', () => {
    it('should reject missing fields', async () => {
      const { POST } = await import('@/app/api/auth/login/route')
      const req = mockRequest('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const res = await POST(req)
      const data = await res.json()

      expect(res.status).toBe(400)
      expect(data.success).toBe(false)
    })

    it('should reject invalid credentials', async () => {
      const { POST } = await import('@/app/api/auth/login/route')
      const req = mockRequest('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'nonexist@test.com', password: 'wrong' }),
      })
      const res = await POST(req)
      expect(res.status).toBe(401)
    })
  })

  describe('POST /api/auth/register', () => {
    it('should reject weak password', async () => {
      const { POST } = await import('@/app/api/auth/register/route')
      const req = mockRequest('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'a@b.com', username: 'test', password: '123' }),
      })
      const res = await POST(req)
      const data = await res.json()

      expect(res.status).toBe(400)
      expect(data.success).toBe(false)
    })

    it('should reject missing fields', async () => {
      const { POST } = await import('@/app/api/auth/register/route')
      const req = mockRequest('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: '' }),
      })
      const res = await POST(req)
      expect(res.status).toBe(400)
    })
  })

  describe('GET /api/auth/me', () => {
    it('should reject unauthenticated request', async () => {
      const { GET } = await import('@/app/api/auth/me/route')
      const req = mockRequest('/api/auth/me')
      const res = await GET(req)
      const data = await res.json()

      expect(res.status).toBe(401)
      expect(data.success).toBe(false)
    })
  })

  describe('POST /api/auth/logout', () => {
    it('should clear token cookie', async () => {
      const { POST } = await import('@/app/api/auth/logout/route')
      const res = await POST()
      const data = await res.json()

      expect(data.success).toBe(true)
    })
  })
})
