import { beforeEach, describe, expect, it, vi } from "vitest"
import { NextRequest } from "next/server"

vi.mock("@/lib/brain-core-url", () => ({
  brainCoreFetch: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe("Chat API", () => {
  it("GET /api/chat/models should return models array (fallback when brain-core offline)", async () => {
    const { GET } = await import("@/app/api/chat/models/route")
    const res = await GET()
    expect(res.status).toBe(200)
    const data = await res.json()
    expect(data).toHaveProperty("models")
    expect(Array.isArray(data.models)).toBe(true)
  })

  it("POST /api/chat/completions should return 502 when brain-core is unavailable", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})
    const { brainCoreFetch } = await import("@/lib/brain-core-url")
    vi.mocked(brainCoreFetch).mockRejectedValue(new TypeError("fetch failed"))

    const { POST } = await import("@/app/api/chat/completions/route")
    const req = new NextRequest(new URL("/api/chat/completions", "http://localhost:3000"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: "hello", stream: false }),
    })
    const res = await POST(req)

    expect(res.status).toBe(502)
    consoleSpy.mockRestore()
  })
})
