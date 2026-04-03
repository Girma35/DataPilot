import { NextRequest, NextResponse } from 'next/server';
import { datapilotApiBase, getAccessToken, proxyUnauthorized } from '@/lib/datapilot-proxy';

export async function GET(request: NextRequest) {
  const token = getAccessToken(request);
  if (!token) {
    return proxyUnauthorized();
  }

  const res = await fetch(`${datapilotApiBase()}/health`, {
    headers: { Authorization: `Bearer ${token}` },
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
