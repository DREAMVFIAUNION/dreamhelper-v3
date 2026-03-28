import { NextRequest, NextResponse } from 'next/server';
import { brainCoreFetch } from '@/lib/brain-core-url';

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const resp = await brainCoreFetch(`/api/v1/agents/${id}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await req.json();
  const resp = await brainCoreFetch(`/api/v1/agents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const resp = await brainCoreFetch(`/api/v1/agents/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
