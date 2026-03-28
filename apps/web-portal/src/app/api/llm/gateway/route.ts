import { NextRequest, NextResponse } from "next/server";
import { brainCoreFetch } from '@/lib/brain-core-url';

export async function GET(req: NextRequest) {
  try {
    const resp = await brainCoreFetch('/api/v1/llm/gateway/stats');
    const data = await resp.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch gateway stats" },
      { status: 502 }
    );
  }
}
