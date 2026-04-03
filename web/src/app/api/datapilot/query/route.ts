import { NextRequest, NextResponse } from 'next/server';
import { datapilotApiBase, getAccessToken, proxyUnauthorized } from '@/lib/datapilot-proxy';

export async function POST(request: NextRequest) {
  const token = getAccessToken(request);
  if (!token) {
    return proxyUnauthorized();
  }

  let payload: { sql?: string; limit?: number };
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const res = await fetch(`${datapilotApiBase()}/query`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      sql: payload.sql ?? '',
      limit: payload.limit,
    }),
    cache: 'no-store',
  });

  const text = await res.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }

  return NextResponse.json(body, { status: res.status });
}
