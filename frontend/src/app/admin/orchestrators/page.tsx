'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import AuthGuard from '@/components/AuthGuard';
import { odinApi, type OrchestratorFull } from '@/lib/api';

const EMPTY_FORM = {
  name: '', display_name: '', system_prompt: '',
  llm_provider: '', llm_model: '',
  max_iterations: 10, max_parallel_tools: 4, rate_limit_rpm: 30,
  daily_budget_usd: '0', enabled: true,
};

function Badge({ on }: { on: boolean }) {
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
      background: on ? '#4edea318' : '#f8717118', color: on ? '#4edea3' : '#f87171',
    }}>{on ? 'enabled' : 'disabled'}</span>
  );
}

export default function OrchestratorsPage() {
  const [list, setList] = useState<OrchestratorFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<OrchestratorFull | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    odinApi.orchestrators().then(setList).finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  function openCreate() {
    setEditing(null);
    setForm({ ...EMPTY_FORM });
    setError('');
    setShowForm(true);
  }

  function openEdit(o: OrchestratorFull) {
    setEditing(o);
    setForm({
      name: o.name, display_name: o.display_name, system_prompt: o.system_prompt,
      llm_provider: o.llm_provider ?? '', llm_model: o.llm_model ?? '',
      max_iterations: o.max_iterations, max_parallel_tools: o.max_parallel_tools,
      rate_limit_rpm: o.rate_limit_rpm, daily_budget_usd: o.daily_budget_usd,
      enabled: o.enabled,
    });
    setError('');
    setShowForm(true);
  }

  async function save() {
    setSaving(true); setError('');
    try {
      const body = {
        ...form,
        llm_provider: form.llm_provider || null,
        llm_model: form.llm_model || null,
        max_iterations: Number(form.max_iterations),
        max_parallel_tools: Number(form.max_parallel_tools),
        rate_limit_rpm: Number(form.rate_limit_rpm),
      };
      if (editing) {
        await odinApi.updateOrchestrator(editing.id, body);
      } else {
        await odinApi.createOrchestrator(body);
      }
      setShowForm(false);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function del(o: OrchestratorFull) {
    if (!confirm(`Delete orchestrator "${o.display_name}"?`)) return;
    await odinApi.deleteOrchestrator(o.id).catch((e) => alert(e.message));
    load();
  }

  const f = (k: keyof typeof form, v: any) => setForm((p) => ({ ...p, [k]: v }));

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
              <span className="material-symbols-outlined" style={{ color: 'var(--tm-accent)', fontSize: 20 }}>account_tree</span>
              <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--tm-text)' }}>Orchestrators</span>
            </div>
            <button onClick={openCreate} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: 'var(--tm-accent)', color: '#fff', fontSize: 13, fontWeight: 600,
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
              New orchestrator
            </button>
          </header>

          <div style={{ padding: 28 }}>
            <div style={{ background: 'var(--tm-surface)', border: '1px solid var(--tm-border)', borderRadius: 12, overflow: 'hidden' }}>
              {/* Table head */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 160px 100px 120px 80px 100px',
                padding: '8px 20px', gap: 12,
                background: 'rgba(255,255,255,.02)', borderBottom: '1px solid var(--tm-border)',
              }}>
                {['Name', 'Model', 'Max iter', 'Rate limit', 'Status', ''].map((h) => (
                  <div key={h} style={{ fontSize: 11, fontWeight: 700, color: 'var(--tm-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</div>
                ))}
              </div>

              {loading ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--tm-text-muted)', fontSize: 13 }}>Loading…</div>
              ) : list.length === 0 ? (
                <div style={{ padding: 60, textAlign: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 40, color: 'var(--tm-text-muted)', display: 'block', marginBottom: 12 }}>account_tree</span>
                  <div style={{ color: 'var(--tm-text-muted)', fontSize: 14, marginBottom: 16 }}>No orchestrators yet</div>
                  <button onClick={openCreate} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--tm-accent)', color: '#fff', fontWeight: 600, fontSize: 13 }}>
                    Create your first orchestrator
                  </button>
                </div>
              ) : list.map((o) => (
                <div key={o.id} style={{
                  display: 'grid', gridTemplateColumns: '1fr 160px 100px 120px 80px 100px',
                  alignItems: 'center', padding: '14px 20px', gap: 12,
                  borderBottom: '1px solid var(--tm-border-subtle)',
                }}>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--tm-text)', fontSize: 13 }}>{o.display_name}</div>
                    <code style={{ fontSize: 11, color: 'var(--tm-text-muted)', background: 'var(--tm-surface-2)', padding: '1px 5px', borderRadius: 4 }}>{o.name}</code>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--tm-text-muted)' }}>
                    {o.llm_model ?? <span style={{ opacity: 0.4 }}>default</span>}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--tm-text-muted)' }}>{o.max_iterations}</div>
                  <div style={{ fontSize: 13, color: 'var(--tm-text-muted)' }}>{o.rate_limit_rpm} rpm</div>
                  <Badge on={o.enabled} />
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button onClick={() => openEdit(o)} title="Edit" style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--tm-text-muted)', padding: 4 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>edit</span>
                    </button>
                    <button onClick={() => del(o)} title="Delete" style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#f87171', padding: 4 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>

      {/* Modal */}
      {showForm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
          <div style={{ background: 'var(--tm-surface)', border: '1px solid var(--tm-border)', borderRadius: 16, width: '100%', maxWidth: 560, maxHeight: '90vh', overflow: 'auto', padding: 32 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--tm-text)', marginBottom: 24 }}>
              {editing ? 'Edit orchestrator' : 'New orchestrator'}
            </h2>

            {error && <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 8, background: '#f8717118', color: '#f87171', fontSize: 13 }}>{error}</div>}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Field label="Slug (used in URL)" disabled={!!editing}>
                <input value={form.name} onChange={(e) => f('name', e.target.value)} placeholder="my-orchestrator" style={inp} />
              </Field>
              <Field label="Display name">
                <input value={form.display_name} onChange={(e) => f('display_name', e.target.value)} placeholder="My Orchestrator" style={inp} />
              </Field>
              <Field label="System prompt">
                <textarea value={form.system_prompt} onChange={(e) => f('system_prompt', e.target.value)} rows={4} placeholder="You are a helpful assistant…" style={{ ...inp, resize: 'vertical', fontFamily: 'inherit' }} />
              </Field>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="LLM provider (optional)">
                  <input value={form.llm_provider} onChange={(e) => f('llm_provider', e.target.value)} placeholder="openai" style={inp} />
                </Field>
                <Field label="LLM model (optional)">
                  <input value={form.llm_model} onChange={(e) => f('llm_model', e.target.value)} placeholder="gpt-4o" style={inp} />
                </Field>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                <Field label="Max iterations">
                  <input type="number" value={form.max_iterations} onChange={(e) => f('max_iterations', e.target.value)} style={inp} />
                </Field>
                <Field label="Parallel tools">
                  <input type="number" value={form.max_parallel_tools} onChange={(e) => f('max_parallel_tools', e.target.value)} style={inp} />
                </Field>
                <Field label="Rate limit (rpm)">
                  <input type="number" value={form.rate_limit_rpm} onChange={(e) => f('rate_limit_rpm', e.target.value)} style={inp} />
                </Field>
              </div>
              <Field label="Enabled">
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.enabled} onChange={(e) => f('enabled', e.target.checked)} style={{ width: 16, height: 16 }} />
                  <span style={{ fontSize: 13, color: 'var(--tm-text)' }}>Active</span>
                </label>
              </Field>
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 28 }}>
              <button onClick={() => setShowForm(false)} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid var(--tm-border)', background: 'transparent', color: 'var(--tm-text)', cursor: 'pointer', fontSize: 13 }}>
                Cancel
              </button>
              <button onClick={save} disabled={saving} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--tm-accent)', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13, opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Saving…' : editing ? 'Save changes' : 'Create'}
              </button>
            </div>
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

function Field({ label, children, disabled }: { label: string; children: React.ReactNode; disabled?: boolean }) {
  return (
    <div style={{ opacity: disabled ? 0.5 : 1 }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--tm-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.4px' }}>{label}</label>
      {children}
    </div>
  );
}
