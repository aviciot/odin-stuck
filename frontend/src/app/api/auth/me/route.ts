import { NextRequest, NextResponse } from 'next/server';

const AUTH_BASE = process.env.ODIN_AUTH_URL || 'http://odin-auth-service:8701';

export async function GET(req: NextRequest) {
  const token = req.cookies.get('odin_access_token')?.value;
  if (!token) {
    return NextResponse.json({ detail: 'Not authenticated' }, { status: 401 });
  }

  const upstream = await fetch(`${AUTH_BASE}/api/v1/auth/me`, {
    headers: { Cookie: `odin_access_token=${token}` },
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
