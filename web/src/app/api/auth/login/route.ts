import { NextResponse } from 'next/server';
import { getAuthorizationUrl, isAuth0Configured } from '@/lib/auth0';

export async function GET() {
  if (!isAuth0Configured) {
    return NextResponse.json(
      {
        error:
          'Auth0 is not configured. Set NEXT_PUBLIC_AUTH0_DOMAIN and NEXT_PUBLIC_AUTH0_CLIENT_ID (e.g. in the repo root .env, loaded automatically).',
      },
      { status: 503 }
    );
  }

  const state = crypto.randomUUID();

  // Store state in cookie for verification during callback
  const response = NextResponse.redirect(getAuthorizationUrl(state));
  response.cookies.set('auth0_state', state, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 10, // 10 minutes
    path: '/',
  });
  
  return response;
}