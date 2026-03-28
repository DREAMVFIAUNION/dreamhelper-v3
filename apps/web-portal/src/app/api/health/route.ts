import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    version: '3.7.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  })
}
