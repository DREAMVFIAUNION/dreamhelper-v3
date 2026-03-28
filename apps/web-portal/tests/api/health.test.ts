import { describe, it, expect } from 'vitest'
import { GET } from '@/app/api/health/route'

describe('GET /api/health', () => {
  it('should return ok status', async () => {
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.status).toBe('ok')
    expect(data.version).toBe('3.7.0')
    expect(data.timestamp).toBeDefined()
    expect(typeof data.uptime).toBe('number')
  })
})
