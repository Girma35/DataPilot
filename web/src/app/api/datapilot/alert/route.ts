import { NextRequest, NextResponse } from 'next/server';
import { datapilotApiBase, getAccessToken, proxyUnauthorized } from '@/lib/datapilot-proxy';

export async function POST(request: NextRequest) {
  const token = getAccessToken(request);
  if (!token) {
    return proxyUnauthorized();
  }

  let payload: { message?: string; channel?: string };
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const res = await fetch(`${datapilotApiBase()}/alert`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: payload.message ?? '',
      channel: payload.channel ?? 'both',
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
