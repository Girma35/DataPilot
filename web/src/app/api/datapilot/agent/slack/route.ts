import { NextRequest, NextResponse } from 'next/server';
import { datapilotApiBase, getAccessToken, proxyUnauthorized } from '@/lib/datapilot-proxy';

export async function POST(request: NextRequest) {
  const token = getAccessToken(request);
  if (!token) {
    return proxyUnauthorized();
  }

  let payload: {
    message?: string;
    slack_channel?: string;
    connection?: string;
    login_hint?: string;
  };
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const res = await fetch(`${datapilotApiBase()}/agent/slack`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: payload.message ?? '',
      slack_channel: payload.slack_channel ?? '',
      connection: payload.connection,
      login_hint: payload.login_hint,
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
