import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async rewrites() {
    const apiBase = process.env.ODIN_API_URL || 'http://odin-bridge:8001';
    return [
      { source: '/api/bridge/:path*', destination: `${apiBase}/:path*` },
    ];
  },
};

export default nextConfig;
