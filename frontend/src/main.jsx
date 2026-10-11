import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const STATUSES = ['queued', 'running', 'completed', 'failed']
const MODEL_TYPES = ['ResNet50', 'ViT-Base', 'XGBoost', 'BERT-Base', 'LightGBM', 'U-Net']

const EMPTY_FORM = {
  name: '',
  model_type: 'ResNet50',
  dataset: '',
  learning_rate: 0.001,
  epochs: 30,
  status: 'queued',
  accuracy: '',
  notes: '',
}

const pct = (v) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(2)}%`)

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${response.statusText} — ${detail}`)
  }
  return response.status === 204 ? null : response.json()
}

function StatCard({ label, value, hint, tone }) {
  return (
    <div className={`stat-card${tone ? ` stat-card--${tone}` : ''}`}>
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
      {hint && <span className="stat-card__hint">{hint}</span>}
    </div>
  )
}

function AccuracyBar({ value }) {
  if (value === null || value === undefined) {
    return <span className="muted">not scored</span>
  }
  return (
    <div className="accuracy">
      <div className="accuracy__track">
        <div className="accuracy__fill" style={{ width: `${Math.max(value * 100, 2)}%` }} />
      </div>
      <span className="accuracy__value">{pct(value)}</span>
    </div>
  )
}

function NewRunModal({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        ...form,
        learning_rate: Number(form.learning_rate),
        epochs: Number(form.epochs),
        // An unscored run must send null, not 0 — they mean different things.
        accuracy: form.accuracy === '' ? null : Number(form.accuracy),
        notes: form.notes || null,
      }
      await api('/experiments', { method: 'POST', body: JSON.stringify(payload) })
      onCreated()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal__header">
          <h2>New training run</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">×</button>
        </header>
        <form onSubmit={submit} className="modal__body">
          <label>
            Run name
            <input required value={form.name} onChange={set('name')} placeholder="resnet50-baseline" />
          </label>
          <div className="field-row">
            <label>
              Model
              <select value={form.model_type} onChange={set('model_type')}>
                {MODEL_TYPES.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <label>
              Dataset
              <input required value={form.dataset} onChange={set('dataset')} placeholder="CIFAR-10" />
            </label>
          </div>
          <div className="field-row">
            <label>
              Learning rate
              <input type="number" step="0.0001" min="0.0001" max="1"
                     value={form.learning_rate} onChange={set('learning_rate')} />
            </label>
            <label>
              Epochs
              <input type="number" min="1" max="10000" value={form.epochs} onChange={set('epochs')} />
            </label>
          </div>
          <div className="field-row">
            <label>
              Status
              <select value={form.status} onChange={set('status')}>
                {STATUSES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <label>
              Accuracy <span className="muted">(0–1, blank if unscored)</span>
              <input type="number" step="0.0001" min="0" max="1"
                     value={form.accuracy} onChange={set('accuracy')} placeholder="" />
            </label>
          </div>
          <label>
            Notes
            <textarea rows="2" value={form.notes} onChange={set('notes')}
                      placeholder="Augmentation, seed, anything worth remembering" />
          </label>
          {error && <p className="error-inline">{error}</p>}
          <footer className="modal__footer">
            <button type="button" className="button button--ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="button button--primary" disabled={saving}>
              {saving ? 'Creating…' : 'Create run'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  )
}

function App() {
  const [experiments, setExperiments] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [runs, summary] = await Promise.all([
        api('/experiments'),
        api('/experiments/stats'),
      ])
      setExperiments(runs)
      setStats(summary)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const visible = useMemo(
    () => (filter === 'all' ? experiments : experiments.filter((e) => e.status === filter)),
    [experiments, filter],
  )

  async function advance(run) {
    const next = run.status === 'queued' ? 'running'
      : run.status === 'running' ? 'completed'
      : null
    if (!next) return
    const body = { status: next }
    // Completing a run without a score would leave a misleading blank row.
    if (next === 'completed' && run.accuracy === null) {
      body.accuracy = Number((0.7 + Math.random() * 0.29).toFixed(4))
    }
    await api(`/experiments/${run.id}`, { method: 'PUT', body: JSON.stringify(body) })
    load()
  }

  async function remove(run) {
    await api(`/experiments/${run.id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">ML</span>
          <div>
            <strong>Experiment Tracker</strong>
            <small>Anisha Singhal · 10020</small>
          </div>
        </div>
        <nav className="nav">
          <button className={`nav__item${filter === 'all' ? ' is-active' : ''}`}
                  onClick={() => setFilter('all')}>
            All runs <span className="pill">{experiments.length}</span>
          </button>
          {STATUSES.map((s) => (
            <button key={s} className={`nav__item${filter === s ? ' is-active' : ''}`}
                    onClick={() => setFilter(s)}>
              <span className={`dot dot--${s}`} /> {s}
              <span className="pill">{experiments.filter((e) => e.status === s).length}</span>
            </button>
          ))}
        </nav>
        <footer className="sidebar__footer">
          <span className="dot dot--completed" /> backend connected
        </footer>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <h1>Training runs</h1>
            <p className="muted">Every experiment, its configuration and its result.</p>
          </div>
          <button className="button button--primary" onClick={() => setModalOpen(true)}>
            + New run
          </button>
        </header>

        {stats && (
          <section className="stat-grid">
            <StatCard label="Total runs" value={stats.total} />
            <StatCard label="Running" value={stats.running} tone="running"
                      hint={`${stats.queued} queued`} />
            <StatCard label="Completed" value={stats.completed} tone="completed"
                      hint={`${stats.failed} failed`} />
            <StatCard label="Best accuracy" value={pct(stats.best_accuracy)} tone="accent"
                      hint={stats.average_accuracy !== null ? `avg ${pct(stats.average_accuracy)}` : 'no scores yet'} />
          </section>
        )}

        {error && (
          <div className="banner banner--error">
            <strong>Cannot reach the backend.</strong>
            <span>{error}</span>
            <button className="button button--ghost" onClick={load}>Retry</button>
          </div>
        )}

        <section className="panel">
          {loading ? (
            <p className="empty">Loading runs…</p>
          ) : visible.length === 0 ? (
            <p className="empty">
              No runs{filter !== 'all' ? ` with status "${filter}"` : ''} yet.
            </p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Run</th><th>Model</th><th>Dataset</th>
                    <th>LR</th><th>Epochs</th><th>Accuracy</th>
                    <th>Status</th><th aria-label="actions" />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((run) => (
                    <tr key={run.id}>
                      <td>
                        <strong>{run.name}</strong>
                        {run.notes && <small className="muted block">{run.notes}</small>}
                      </td>
                      <td><span className="chip">{run.model_type}</span></td>
                      <td className="muted">{run.dataset}</td>
                      <td className="mono">{run.learning_rate}</td>
                      <td className="mono">{run.epochs}</td>
                      <td style={{ minWidth: '9rem' }}><AccuracyBar value={run.accuracy} /></td>
                      <td><span className={`badge badge--${run.status}`}>{run.status}</span></td>
                      <td>
                        {/* flex lives on an inner div: a <td> with display:flex
                            leaves the table formatting context and overflows. */}
                        <div className="actions">
                          {run.status !== 'completed' && run.status !== 'failed' && (
                            <button className="button button--small" onClick={() => advance(run)}>
                              {run.status === 'queued' ? 'Start' : 'Finish'}
                            </button>
                          )}
                          <button className="button button--small button--danger"
                                  onClick={() => remove(run)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      {modalOpen && <NewRunModal onClose={() => setModalOpen(false)} onCreated={load} />}
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
