import { NextRequest, NextResponse } from 'next/server';
import { auth0Config } from '@/lib/auth0';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');

  if (error) {
    return NextResponse.redirect(new URL('/?error=' + error, request.url));
  }

  if (!code) {
    return NextResponse.redirect(new URL('/?error=no_code', request.url));
  }

  // Verify state cookie
  const stateCookie = request.cookies.get('auth0_state');
  if (!stateCookie || state !== stateCookie.value) {
    return NextResponse.redirect(new URL('/?error=invalid_state', request.url));
  }

  try {
    // Exchange code for tokens
    const tokenBody: Record<string, string> = {
      grant_type: 'authorization_code',
      client_id: auth0Config.clientId,
      client_secret: process.env.AUTH0_CLIENT_SECRET || '',
      code,
      redirect_uri: auth0Config.callbackUrl,
    };
    if (auth0Config.audience) {
      tokenBody.audience = auth0Config.audience;
    }

    const tokenResponse = await fetch(`https://${auth0Config.domain}/oauth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tokenBody),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('Token exchange failed:', errorData);
      return NextResponse.redirect(new URL('/?error=token_exchange_failed', request.url));
    }

    const tokens = await tokenResponse.json();

    // Get user info
    const userInfoResponse = await fetch(`https://${auth0Config.domain}/userinfo`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    const user = await userInfoResponse.json();

    // Create response and set cookies
    const response = NextResponse.redirect(new URL('/', request.url));

    // Set access token (short-lived)
    response.cookies.set('access_token', tokens.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: tokens.expires_in,
      path: '/',
    });

    // Set refresh token if provided
    if (tokens.refresh_token) {
      response.cookies.set('refresh_token', tokens.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 60 * 60 * 24 * 30, // 30 days
        path: '/',
      });
    }

    // Clear state cookie
    response.cookies.delete('auth0_state');

    return response;
  } catch (error) {
    console.error('Auth callback error:', error);
    return NextResponse.redirect(new URL('/?error=callback_error', request.url));
  }
}