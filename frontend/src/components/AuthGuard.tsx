'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

// Standalone check — does not use Zustand (avoids store hydration races)
function isTokenValid(): boolean {
  try {
    const token = localStorage.getItem('odin_access_token');
    if (!token) return false;
    const seg = token.split('.')[1];
    const b64 = seg.replace(/-/g, '+').replace(/_/g, '/') + '==';
    const payload = JSON.parse(atob(b64));
    // Give 10s leeway for clock skew
    return payload.exp * 1000 > Date.now() - 10_000;
  } catch {
    return false;
  }
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isTokenValid()) {
      setReady(true);
    } else {
      // Clear any bad tokens
      localStorage.removeItem('odin_access_token');
      localStorage.removeItem('odin_refresh_token');
      router.replace('/login');
    }
  }, []);

  if (!ready) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--tm-bg)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <svg style={{ width: '32px', height: '32px', color: 'var(--tm-accent)', animation: 'spin 1s linear infinite', display: 'block', margin: '0 auto 12px' }}
            fill="none" viewBox="0 0 24 24">
            <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <p style={{ fontSize: '13px', color: 'var(--tm-text-muted)' }}>Verifying session…</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return <>{children}</>;
}
