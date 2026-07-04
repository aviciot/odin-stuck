'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import { odinApi, type AccessToken, type OrchestratorFull } from '@/lib/api';

function Badge({ on }: { on: boolean }) {
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
      background: on ? '#4edea318' : '#f8717118', color: on ? '#4edea3' : '#f87171',
    }}>{on ? 'active' : 'disabled'}</span>
  );
}

function CopyBox({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <div style={{ marginTop: 16, background: 'var(--tm-surface-2)', border: '1px solid var(--tm-accent)', borderRadius: 10, padding: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--tm-accent)', marginBottom: 8 }}>
        Token created — copy it now, it won't be shown again
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <code style={{ flex: 1, fontSize: 11, color: 'var(--tm-text)', wordBreak: 'break-all', fontFamily: 'monospace' }}>{value}</code>
        <button onClick={copy} style={{ flexShrink: 0, padding: '6px 12px', borderRadius: 6, border: 'none', cursor: 'pointer', background: copied ? '#4edea3' : 'var(--tm-accent)', color: '#fff', fontSize: 12, fontWeight: 600 }}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    </div>
  );
}

export default function TokensPage() {
  const [list, setList] = useState<AccessToken[]>([]);
  const [orchestrators, setOrchestrators] = useState<OrchestratorFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newToken, setNewToken] = useState('');
  const [form, setForm] = useState({ label: '', user_id: 1, orchestrator_id: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    Promise.all([odinApi.tokens(), odinApi.orchestrators()])
      .then(([t, o]) => { setList(t); setOrchestrators(o); })
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  function openCreate() {
    setForm({ label: '', user_id: 1, orchestrator_id: '' });
    setNewToken('');
    setError('');
    setShowForm(true);
  }

  async function save() {
    setSaving(true); setError('');
    try {
      const body: any = { label: form.label, user_id: Number(form.user_id) };
      if (form.orchestrator_id) body.orchestrator_id = form.orchestrator_id;
      const created = await odinApi.createToken(body);
      setNewToken(created.token ?? '');
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggle(t: AccessToken) {
    await odinApi.updateToken(t.id, { enabled: !t.enabled }).catch((e) => alert(e.message));
    load();
  }

  async function del(t: AccessToken) {
    if (!confirm(`Delete token "${t.label}"?`)) return;
    await odinApi.deleteToken(t.id).catch((e) => alert(e.message));
    load();
  }

  const orchName = (id: string | null) =>
    id ? (orchestrators.find((o) => o.id === id)?.display_name ?? id.slice(0, 8)) : 'All orchestrators';

  function fmt(dt: string | null) {
    return dt ? new Date(dt).toLocaleDateString() : '—';
  }

  return (
    <AuthGuard>
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--tm-bg)' }}>
        <Sidebar />
        <main style={{ marginLeft: 260, flex: 1 }}>
          <header style={{
            position: 'sticky', top: 0, zIndex: 30, height: 56,
            background: 'var(--tm-topbar)', borderBottom: '1px solid var(--tm-topbar-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 28px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="material-symbols-outlined" style={{ color: 'var(--tm-accent)', fontSize: 20 }}>key</span>
              <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--tm-text)' }}>Access Tokens</span>
            </div>
            <button onClick={openCreate} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: 'var(--tm-accent)', color: '#fff', fontSize: 13, fontWeight: 600,
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
              New token
            </button>
          </header>

          <div style={{ padding: 28 }}>
            {newToken && (
              <div style={{ marginBottom: 20 }}>
                <CopyBox value={newToken} />
              </div>
            )}

            <div style={{ background: 'var(--tm-surface)', border: '1px solid var(--tm-border)', borderRadius: 12, overflow: 'hidden' }}>
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 180px 140px 100px 80px 80px',
                padding: '8px 20px', gap: 12,
                background: 'rgba(255,255,255,.02)', borderBottom: '1px solid var(--tm-border)',
              }}>
                {['Label', 'Scope', 'Expires', 'Last used', 'Status', ''].map((h) => (
                  <div key={h} style={{ fontSize: 11, fontWeight: 700, color: 'var(--tm-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</div>
                ))}
              </div>

              {loading ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--tm-text-muted)', fontSize: 13 }}>Loading…</div>
              ) : list.length === 0 ? (
                <div style={{ padding: 60, textAlign: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 40, color: 'var(--tm-text-muted)', display: 'block', marginBottom: 12 }}>key</span>
                  <div style={{ color: 'var(--tm-text-muted)', fontSize: 14, marginBottom: 16 }}>No access tokens yet</div>
                  <button onClick={openCreate} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--tm-accent)', color: '#fff', fontWeight: 600, fontSize: 13 }}>
                    Create first token
                  </button>
                </div>
              ) : list.map((t) => (
                <div key={t.id} style={{
                  display: 'grid', gridTemplateColumns: '1fr 180px 140px 100px 80px 80px',
                  alignItems: 'center', padding: '14px 20px', gap: 12,
                  borderBottom: '1px solid var(--tm-border-subtle)',
                }}>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--tm-text)', fontSize: 13 }}>{t.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--tm-text-muted)' }}>user #{t.user_id}</div>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--tm-text-muted)' }}>{orchName(t.orchestrator_id)}</div>
                  <div style={{ fontSize: 12, color: 'var(--tm-text-muted)' }}>{fmt(t.expires_at)}</div>
                  <div style={{ fontSize: 12, color: 'var(--tm-text-muted)' }}>{fmt(t.last_used_at)}</div>
                  <Badge on={t.enabled} />
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button onClick={() => toggle(t)} title={t.enabled ? 'Disable' : 'Enable'} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--tm-text-muted)', padding: 4 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{t.enabled ? 'toggle_on' : 'toggle_off'}</span>
                    </button>
                    <button onClick={() => del(t)} title="Delete" style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#f87171', padding: 4 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>

      {showForm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
          <div style={{ background: 'var(--tm-surface)', border: '1px solid var(--tm-border)', borderRadius: 16, width: '100%', maxWidth: 440, padding: 32 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--tm-text)', marginBottom: 24 }}>New access token</h2>

            {error && <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 8, background: '#f8717118', color: '#f87171', fontSize: 13 }}>{error}</div>}

            {newToken ? (
              <>
                <CopyBox value={newToken} />
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
                  <button onClick={() => { setShowForm(false); setNewToken(''); }} style={{ padding: '8px 18px', borderRadius: 8, border: 'none', background: 'var(--tm-accent)', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>Done</button>
                </div>
              </>
            ) : (
              <>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <label style={lbl}>Label</label>
                    <input value={form.label} onChange={(e) => setForm((p) => ({ ...p, label: e.target.value }))} placeholder="CI pipeline token" style={inp} />
                  </div>
                  <div>
                    <label style={lbl}>Scope (orchestrator)</label>
                    <select value={form.orchestrator_id} onChange={(e) => setForm((p) => ({ ...p, orchestrator_id: e.target.value }))} style={inp}>
                      <option value="">All orchestrators</option>
                      {orchestrators.map((o) => <option key={o.id} value={o.id}>{o.display_name}</option>)}
                    </select>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 28 }}>
                  <button onClick={() => setShowForm(false)} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid var(--tm-border)', background: 'transparent', color: 'var(--tm-text)', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
                  <button onClick={save} disabled={saving || !form.label} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--tm-accent)', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13, opacity: saving || !form.label ? 0.6 : 1 }}>
                    {saving ? 'Creating…' : 'Create token'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </AuthGuard>
  );
}

const inp: React.CSSProperties = {
  width: '100%', background: 'var(--tm-surface-2)', border: '1px solid var(--tm-border)',
  borderRadius: 8, padding: '8px 12px', color: 'var(--tm-text)', fontSize: 13,
  boxSizing: 'border-box',
};
const lbl: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--tm-text-muted)',
  marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.4px',
};
