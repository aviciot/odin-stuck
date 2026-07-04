import { NextRequest, NextResponse } from 'next/server';

const AUTH_BASE = process.env.ODIN_AUTH_URL || 'http://odin-auth-service:8701';

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get('odin_refresh_token')?.value;
  if (!refreshToken) {
    return NextResponse.json({ detail: 'No refresh token' }, { status: 401 });
  }

  const upstream = await fetch(`${AUTH_BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { Cookie: `odin_refresh_token=${refreshToken}` },
  });

  const data = await upstream.json();
  if (!upstream.ok) {
    return NextResponse.json(data, { status: upstream.status });
  }

  const { access_token, refresh_token, expires_in } = data;
  const res = NextResponse.json({ ok: true, expires_in });

  res.cookies.set('odin_access_token', access_token, {
    httpOnly: true,
    sameSite: 'strict',
    secure: process.env.NODE_ENV === 'production',
    maxAge: expires_in,
    path: '/',
  });
  res.cookies.set('odin_refresh_token', refresh_token, {
    httpOnly: true,
    sameSite: 'strict',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60 * 24 * 7,
    path: '/',
  });

  return res;
}
