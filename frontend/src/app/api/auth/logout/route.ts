import { NextRequest, NextResponse } from 'next/server';

const AUTH_BASE = process.env.ODIN_AUTH_URL || 'http://odin-auth-service:8701';

export async function POST(req: NextRequest) {
  const token = req.cookies.get('odin_access_token')?.value;

  if (token) {
    await fetch(`${AUTH_BASE}/api/v1/auth/logout`, {
      method: 'POST',
      headers: { Cookie: `odin_access_token=${token}` },
    }).catch(() => {});
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.delete('odin_access_token');
  res.cookies.delete('odin_refresh_token');
  return res;
}
