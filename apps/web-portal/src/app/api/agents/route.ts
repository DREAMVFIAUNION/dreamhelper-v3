import { NextRequest, NextResponse } from 'next/server';
import { brainCoreFetch } from '@/lib/brain-core-url';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const qs = searchParams.toString();
  const resp = await brainCoreFetch(`/api/v1/agents${qs ? `?${qs}` : ''}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const resp = await brainCoreFetch('/api/v1/agents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
