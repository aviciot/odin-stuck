'use client';
import { useEffect, useState, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import { useAuthStore } from '@/stores/authStore';
import { odinApi, type Agent, type Run, type RunStats, type BridgeHealth } from '@/lib/api';

interface DashState {
  health: BridgeHealth | null;
  agents: Agent[];
  runs: Run[];
  stats: RunStats | null;
  loading: boolean;
  lastRefresh: Date | null;
}

function StatCard({ icon, label, value, sub, color }: {
  icon: string; label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div style={{
      background: 'var(--tm-surface)', border: '1px solid var(--tm-border)',
      borderRadius: '12px', padding: '16px', boxShadow: '0 1px 3px rgba(0,0,0,.05)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
        <span className="material-symbols-outlined" style={{ fontSize: '22px', color: color || 'var(--tm-accent)' }}>{icon}</span>
        <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--tm-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>LIVE</span>
      </div>
      <p style={{ fontSize: '28px', fontWeight: 700, color: 'var(--tm-text)', lineHeight: 1, marginBottom: '4px' }}>{value}</p>
      <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--tm-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</p>
      {sub && <p style={{ fontSize: '11px', color: 'var(--tm-text-subtle)', marginTop: '8px' }}>{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string }> = {
    ok:        { bg: 'rgba(0,118,80,.12)', text: '#005b3d' },
    healthy:   { bg: 'rgba(0,118,80,.12)', text: '#005b3d' },
    error:     { bg: 'rgba(220,38,38,.1)',  text: '#dc2626' },
    degraded:  { bg: 'rgba(245,158,11,.1)', text: '#d97706' },
    unknown:   { bg: 'rgba(107,114,128,.1)', text: '#6b7280' },
  };
  const s = map[status] || map.unknown;
  return (
    <span style={{ background: s.bg, color: s.text, fontSize: '10px', fontWeight: 700, padding: '3px 8px', borderRadius: '4px', textTransform: 'capitalize' }}>
      {status}
    </span>
  );
}

function RunStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: '#005b3d', failed: '#dc2626', running: 'var(--tm-accent)', pending: '#d97706',
  };
  return (
    <span style={{ color: map[status] || 'var(--tm-text-muted)', fontSize: '12px', fontWeight: 600 }}>
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [state, setState] = useState<DashState>({
    health: null, agents: [], runs: [], stats: null, loading: true, lastRefresh: null,
  });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    const [health, agents, runsResp, stats] = await Promise.allSettled([
      odinApi.health(),
      odinApi.agents(),
      odinApi.runs(10),
      odinApi.runStats(),
    ]);
    setState({
      health: health.status === 'fulfilled' ? health.value : null,
      agents: agents.status === 'fulfilled' ? agents.value : [],
      runs: runsResp.status === 'fulfilled' ? (runsResp.value?.items ?? []) : [],
      stats: stats.status === 'fulfilled' ? stats.value : null,
      loading: false,
      lastRefresh: new Date(),
    });
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, [load]);

  const { health, agents, runs, stats, loading, lastRefresh } = state;
  const enabledAgents = agents.filter((a) => a.enabled).length;
  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : (user?.email?.[0] ?? 'O').toUpperCase();

  return (
    <AuthGuard>
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--tm-bg)' }}>
        <Sidebar />

        <main style={{ marginLeft: '260px', flex: 1, minHeight: '100vh' }}>
          {/* Top bar */}
          <header style={{
            position: 'sticky', top: 0, zIndex: 30, height: '56px',
            background: 'var(--tm-topbar)', borderBottom: '1px solid var(--tm-topbar-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0 32px',
          }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--tm-accent)', letterSpacing: '-0.01em' }}>
                Command Center
              </h2>
              <p style={{ fontSize: '11px', color: 'var(--tm-text-muted)' }}>
                Real-time orchestration intelligence
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {lastRefresh && (
                <span style={{ fontSize: '11px', color: 'var(--tm-text-subtle)' }}>
                  Updated {lastRefresh.toLocaleTimeString()}
                </span>
              )}
              <button onClick={load} disabled={loading}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--tm-border)',
                  background: 'var(--tm-surface)', color: 'var(--tm-text-2)', cursor: 'pointer',
                  fontSize: '13px', fontWeight: 500,
                }}>
                <span className="material-symbols-outlined" style={{ fontSize: '16px', ...(loading ? { animation: 'slow-spin 1s linear infinite' } : {}) }}>refresh</span>
                Refresh
              </button>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingLeft: '16px', borderLeft: '1px solid var(--tm-border)' }}>
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tm-text)' }}>{user?.name || user?.email}</p>
                  <p style={{ fontSize: '10px', color: 'var(--tm-text-muted)', textTransform: 'uppercase' }}>{user?.role}</p>
                </div>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '8px',
                  background: '#d7dbfd', color: '#585d7a',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '12px', fontWeight: 700,
                }}>{initials}</div>
              </div>
            </div>
          </header>

          <div style={{ padding: '32px', maxWidth: '1440px' }}>
            {/* Stat bento */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '16px', marginBottom: '32px' }}>
              <StatCard icon="smart_toy" label="Total Agents" value={agents.length} sub={`${enabledAgents} enabled`} />
              <StatCard icon="sensors" label="Active Agents" value={enabledAgents} sub="Currently enabled" color="#005b3d" />
              <StatCard icon="history" label="Total Runs" value={stats?.total ?? '—'} sub="All time" color="#585d7a" />
              <StatCard icon="payments" label="Total Cost" value={stats ? `$${(stats.total_cost_usd).toFixed(4)}` : '—'} sub="All time LLM spend" color="#b45309" />
            </div>

            {/* Infrastructure health */}
            <section style={{ marginBottom: '32px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--tm-text)' }}>Infrastructure Health</h3>
                  <p style={{ fontSize: '13px', color: 'var(--tm-text-muted)' }}>Core backend services</p>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
                {[
                  { icon: 'memory', label: 'Odin Bridge', detail: health?.status === 'ok' ? 'Responding' : 'Unreachable', status: health?.status === 'ok' ? 'ok' : 'error' },
                  { icon: 'storage', label: 'PostgreSQL', detail: health?.postgres || 'unknown', status: health?.postgres === 'ok' ? 'ok' : 'degraded' },
                  { icon: 'database', label: 'Redis', detail: health?.redis || 'unknown', status: health?.redis === 'ok' ? 'ok' : 'degraded' },
                ].map(({ icon, label, detail, status }) => (
                  <div key={label} style={{
                    background: 'var(--tm-surface)', border: '1px solid var(--tm-border)',
                    borderRadius: '12px', padding: '16px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: '22px', color: 'var(--tm-text-muted)' }}>{icon}</span>
                      <div>
                        <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--tm-text)' }}>{label}</p>
                        <p style={{ fontSize: '11px', color: 'var(--tm-text-muted)' }}>{detail}</p>
                      </div>
                    </div>
                    <StatusBadge status={status} />
                  </div>
                ))}
              </div>
            </section>

            {/* Two-column: agents + recent runs */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              {/* Agents */}
              <section>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--tm-text)' }}>Agents</h3>
                  <a href="/agents" style={{ fontSize: '12px', color: 'var(--tm-accent)', textDecoration: 'none', fontWeight: 500 }}>View all →</a>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {agents.length === 0 && !loading && (
                    <div style={{ textAlign: 'center', padding: '32px', color: 'var(--tm-text-subtle)', fontSize: '13px', background: 'var(--tm-surface)', borderRadius: '12px', border: '1px solid var(--tm-border)' }}>
                      No agents configured yet
                    </div>
                  )}
                  {agents.slice(0, 6).map((agent) => (
                    <div key={agent.id} style={{
                      background: 'var(--tm-surface)', border: '1px solid var(--tm-border)',
                      borderRadius: '10px', padding: '12px 16px',
                      display: 'flex', alignItems: 'center', gap: '12px',
                      transition: 'border-color .15s',
                      cursor: 'pointer',
                    }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--tm-accent)')}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--tm-border)')}
                    >
                      <div style={{
                        width: '36px', height: '36px', borderRadius: '8px', flexShrink: 0,
                        background: 'var(--tm-accent-bg)', color: 'var(--tm-accent)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>smart_toy</span>
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--tm-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {agent.name}
                        </p>
                        <p style={{ fontSize: '11px', color: 'var(--tm-text-muted)' }}>{agent.transport} · {agent.slug}</p>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '10px', fontWeight: 700, padding: '2px 7px', borderRadius: '4px',
                          background: agent.enabled ? 'rgba(0,118,80,.12)' : 'rgba(107,114,128,.1)',
                          color: agent.enabled ? '#005b3d' : '#6b7280',
                        }}>
                          {agent.enabled ? 'enabled' : 'disabled'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Recent runs */}
              <section>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--tm-text)' }}>Recent Runs</h3>
                  <a href="/runs" style={{ fontSize: '12px', color: 'var(--tm-accent)', textDecoration: 'none', fontWeight: 500 }}>View all →</a>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {runs.length === 0 && !loading && (
                    <div style={{ textAlign: 'center', padding: '32px', color: 'var(--tm-text-subtle)', fontSize: '13px', background: 'var(--tm-surface)', borderRadius: '12px', border: '1px solid var(--tm-border)' }}>
                      No runs yet — start an orchestration!
                    </div>
                  )}
                  {runs.map((run) => (
                    <div key={run.id} style={{
                      background: 'var(--tm-surface)', border: '1px solid var(--tm-border)',
                      borderRadius: '10px', padding: '12px 16px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                        <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--tm-text)', flex: 1, marginRight: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {run.user_message || '(no message)'}
                        </p>
                        <RunStatusBadge status={run.status} />
                      </div>
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--tm-text-muted)' }}>{run.orchestrator_name}</span>
                        <span style={{ fontSize: '11px', color: 'var(--tm-text-subtle)' }}>·</span>
                        <span style={{ fontSize: '11px', color: 'var(--tm-text-subtle)' }}>
                          {new Date(run.started_at).toLocaleTimeString()}
                        </span>
                        {run.duration_ms != null && (
                          <>
                            <span style={{ fontSize: '11px', color: 'var(--tm-text-subtle)' }}>·</span>
                            <span style={{ fontSize: '11px', color: 'var(--tm-text-subtle)' }}>{(run.duration_ms / 1000).toFixed(1)}s</span>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            {/* Run stats by status */}
            {stats && stats.total > 0 && (
              <section style={{ marginTop: '24px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--tm-text)', marginBottom: '16px' }}>Run Status Breakdown</h3>
                <div style={{ display: 'flex', gap: '12px' }}>
                  {Object.entries(stats.by_status).map(([status, count]) => (
                    <div key={status} style={{
                      background: 'var(--tm-surface)', border: '1px solid var(--tm-border)',
                      borderRadius: '10px', padding: '12px 20px', textAlign: 'center',
                    }}>
                      <p style={{ fontSize: '22px', fontWeight: 700, color: 'var(--tm-text)' }}>{count as number}</p>
                      <RunStatusBadge status={status} />
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
