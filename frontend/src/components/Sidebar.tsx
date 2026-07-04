'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

const NAV = [
  { href: '/dashboard', icon: 'dashboard', label: 'Command Center' },
  { href: '/runs',      icon: 'history',   label: 'Run History' },
];

const ADMIN_NAV = [
  { href: '/admin/orchestrators', icon: 'account_tree', label: 'Orchestrators' },
  { href: '/admin/agents',        icon: 'smart_toy',    label: 'Agents' },
  { href: '/admin/tokens',        icon: 'key',           label: 'Access Tokens' },
  { href: '/admin/playground',    icon: 'science',       label: 'Playground' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const isActive = (href: string) =>
    href === '/dashboard' ? pathname === href : pathname.startsWith(href);

  async function handleLogout() {
    await logout();
    router.replace('/login');
  }

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : (user?.email?.[0] ?? 'O').toUpperCase();

  return (
    <>
      {/* Sidebar */}
      <aside style={{
        width: '260px', height: '100vh', position: 'fixed', left: 0, top: 0,
        background: 'var(--tm-sidebar)', borderRight: '1px solid rgba(255,255,255,.06)',
        display: 'flex', flexDirection: 'column', padding: '24px 0', zIndex: 40,
      }}>
        {/* Brand */}
        <div style={{ padding: '0 24px', marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            {/* Mini logo */}
            {/* Shield + M logo */}
            <svg width="34" height="38" viewBox="0 0 80 88" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="sb-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style={{ stopColor: '#3b4dff', stopOpacity: 1 }} />
                  <stop offset="100%" style={{ stopColor: '#7c3aed', stopOpacity: 1 }} />
                </linearGradient>
              </defs>
              <path d="M40 4 L74 18 L74 46 C74 64 58 78 40 84 C22 78 6 64 6 46 L6 18 Z"
                fill="rgba(59,77,255,0.15)" stroke="url(#sb-grad)" strokeWidth="3" />
              <circle cx="20" cy="28" r="4.5" fill="url(#sb-grad)" />
              <circle cx="40" cy="52" r="4.5" fill="url(#sb-grad)" />
              <circle cx="60" cy="28" r="4.5" fill="url(#sb-grad)" />
              <line x1="20" y1="28" x2="40" y2="52" stroke="url(#sb-grad)" strokeWidth="3" strokeLinecap="round"/>
              <line x1="40" y1="52" x2="60" y2="28" stroke="url(#sb-grad)" strokeWidth="3" strokeLinecap="round"/>
              <circle cx="40" cy="52" r="5.5" fill="#e63946" />
            </svg>
            <div>
              <h1 style={{ color: '#e8eaed', fontWeight: 900, fontSize: '18px', letterSpacing: '-0.02em', lineHeight: 1 }}>the-M</h1>
              <p style={{ color: 'rgba(255,255,255,.3)', fontSize: '9px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                Orchestration
              </p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, overflowY: 'auto', padding: '0 12px' }} className="custom-scrollbar">
          <p style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', color: 'rgba(255,255,255,.25)', textTransform: 'uppercase', padding: '0 12px', marginBottom: '8px' }}>
            Observe
          </p>
          {NAV.map(({ href, icon, label }) => (
            <Link key={href} href={href} style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '8px 12px', borderRadius: '0 24px 24px 0',
              marginBottom: '2px', textDecoration: 'none', fontSize: '14px',
              transition: 'all .15s',
              background: isActive(href) ? 'var(--tm-accent-bg)' : 'transparent',
              color: isActive(href) ? 'var(--tm-accent)' : 'rgba(255,255,255,.45)',
              fontWeight: isActive(href) ? 600 : 400,
            }}
              onMouseEnter={(e) => { if (!isActive(href)) (e.currentTarget as HTMLElement).style.color = '#e8eaed'; }}
              onMouseLeave={(e) => { if (!isActive(href)) (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,.45)'; }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>{icon}</span>
              {label}
            </Link>
          ))}

          {user?.role === 'admin' || user?.role === 'super_admin' ? (
            <>
              <p style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', color: 'rgba(255,255,255,.25)', textTransform: 'uppercase', padding: '16px 12px 8px' }}>
                Admin
              </p>
              {ADMIN_NAV.map(({ href, icon, label }) => (
                <Link key={href} href={href} style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '8px 12px', borderRadius: '0 24px 24px 0',
                  marginBottom: '2px', textDecoration: 'none', fontSize: '14px',
                  transition: 'all .15s',
                  background: isActive(href) ? 'var(--tm-accent-bg)' : 'transparent',
                  color: isActive(href) ? 'var(--tm-accent)' : 'rgba(255,255,255,.45)',
                  fontWeight: isActive(href) ? 600 : 400,
                }}
                  onMouseEnter={(e) => { if (!isActive(href)) (e.currentTarget as HTMLElement).style.color = '#e8eaed'; }}
                  onMouseLeave={(e) => { if (!isActive(href)) (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,.45)'; }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>{icon}</span>
                  {label}
                </Link>
              ))}
            </>
          ) : null}
        </nav>

        {/* Footer: status + user */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,.06)' }}>
          {/* System status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <div className="pulse-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#4edea3', flexShrink: 0 }} />
            <div>
              <p style={{ fontSize: '10px', fontWeight: 700, color: '#e8eaed', textTransform: 'uppercase', letterSpacing: '0.05em' }}>System Status</p>
              <p style={{ fontSize: '10px', color: '#4edea3' }}>All Systems Operational</p>
            </div>
          </div>
          {/* User */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px', flexShrink: 0,
              background: '#d7dbfd', color: '#585d7a',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '12px', fontWeight: 700,
            }}>{initials}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: '13px', fontWeight: 600, color: '#e8eaed', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.name || user?.email}</p>
              <p style={{ fontSize: '10px', color: 'rgba(255,255,255,.3)', textTransform: 'uppercase' }}>{user?.role}</p>
            </div>
            <button onClick={handleLogout} title="Sign out"
              style={{ color: 'rgba(255,255,255,.3)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,.3)')}>
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>logout</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
