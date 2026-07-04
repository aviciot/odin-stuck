import { NextRequest, NextResponse } from 'next/server';

const BRIDGE_BASE = process.env.ODIN_API_URL || 'http://odin-bridge:8001';

async function proxy(req: NextRequest, params: Promise<{ path: string[] }>) {
  const token = req.cookies.get('odin_access_token')?.value;
  const { path: segments } = await params;
  const path = segments.join('/');
  const url = `${BRIDGE_BASE}/api/v1/${path}${req.nextUrl.search}`;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const body = req.method !== 'GET' && req.method !== 'HEAD'
    ? await req.text()
    : undefined;

  const upstream = await fetch(url, { method: req.method, headers, body });
  const data = upstream.status === 204 ? null : await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
export async function PUT(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
export async function PATCH(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
export async function DELETE(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
