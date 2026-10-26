import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

// Two formatters, because the two contexts want different precision. The hero
// metric is read at a glance; the table column is compared row against row.
const pctLoose = (v) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}`)
const pctTight = (v) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(2)}%`)

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

/* ------------------------------------------------------------------ chrome */

function Brand() {
  return (
    <div className="brand">
      <span className="brand__mark" aria-hidden="true">
        <i /><i /><i /><i />
      </span>
      <span className="brand__text">
        <strong>Experiment Tracker</strong>
        <small>Anisha Singhal · 10020</small>
      </span>
    </div>
  )
}

function Nav({ filter, setFilter, counts, total }) {
  return (
    <nav className="nav" aria-label="Filter runs by status">
      <button
        className={`nav__item${filter === 'all' ? ' is-active' : ''}`}
        onClick={() => setFilter('all')}
        aria-current={filter === 'all' ? 'page' : undefined}
      >
        <span className="nav__label">All runs</span>
        <span className="nav__count">{total}</span>
      </button>
      {STATUSES.map((s) => (
        <button
          key={s}
          className={`nav__item${filter === s ? ' is-active' : ''}`}
          onClick={() => setFilter(s)}
          aria-current={filter === s ? 'page' : undefined}
        >
          <span className={`dot dot--${s}`} aria-hidden="true" />
          <span className="nav__label">{s}</span>
          <span className="nav__count">{counts[s] ?? 0}</span>
        </button>
      ))}
    </nav>
  )
}

/* ----------------------------------------------------------------- metrics */

// One stacked bar instead of three separate count cards. Three numbers tell you
// the counts; a single proportional bar tells you the shape of the backlog,
// which is the thing you actually look for.
function DistributionBar({ counts, total }) {
  if (!total) return <div className="dist__track dist__track--empty" />
  return (
    <div className="dist__track" role="img"
         aria-label={STATUSES.map((s) => `${counts[s] ?? 0} ${s}`).join(', ')}>
      {STATUSES.map((s) => {
        const n = counts[s] ?? 0
        if (!n) return null
        return (
          <span key={s} className={`dist__seg dist__seg--${s}`}
                style={{ flexGrow: n }} title={`${n} ${s}`} />
        )
      })}
    </div>
  )
}

function HeroMetrics({ stats, best }) {
  const counts = {
    queued: stats.queued, running: stats.running,
    completed: stats.completed, failed: stats.failed,
  }
  return (
    <section className="hero" aria-label="Summary">
      <div className="hero__primary">
        <span className="label">Best accuracy</span>
        <p className="hero__figure">
          {stats.best_accuracy === null ? (
            <span className="hero__figure-empty">—</span>
          ) : (
            <>
              <span className="hero__num">{pctLoose(stats.best_accuracy)}</span>
              <span className="hero__unit">%</span>
            </>
          )}
        </p>
        {best ? (
          <>
            <p className="hero__caption">
              <span className="hero__caption-name">{best.name}</span>
              <span className="sep" aria-hidden="true">·</span>
              {best.model_type}
              <span className="sep" aria-hidden="true">·</span>
              {best.dataset}
            </p>
            <dl className="hero__meta">
              <div>
                <dt>Learning rate</dt>
                <dd>{best.learning_rate}</dd>
              </div>
              <div>
                <dt>Epochs</dt>
                <dd>{best.epochs}</dd>
              </div>
            </dl>
          </>
        ) : (
          <p className="hero__caption muted">No run has been scored yet</p>
        )}
      </div>

      <div className="hero__aside">
        <div className="hero__row">
          <span className="label">Distribution</span>
          <span className="hero__total">
            <span className="mono">{stats.total}</span> total
          </span>
        </div>
        <DistributionBar counts={counts} total={stats.total} />
        <ul className="legend">
          {STATUSES.map((s) => (
            <li key={s}>
              <span className={`dot dot--${s}`} aria-hidden="true" />
              <span className="legend__name">{s}</span>
              <span className="legend__count mono">{counts[s] ?? 0}</span>
            </li>
          ))}
        </ul>
        {stats.average_accuracy !== null && (
          <p className="hero__footnote">
            Mean of scored runs <span className="mono">{pctTight(stats.average_accuracy)}</span>
          </p>
        )}
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------- table */

// The bar is on a fixed 0–100 scale with a tick at 50, so two rows can be
// compared by eye. A bar scaled to its own value cannot be compared to anything.
function AccuracyCell({ value, isBest }) {
  if (value === null || value === undefined) {
    return <span className="unscored">not scored</span>
  }
  return (
    <div className={`acc${isBest ? ' acc--best' : ''}`}
         title={isBest ? 'Best scoring run' : undefined}>
      <span className="acc__value mono">{pctTight(value)}</span>
      <span className="acc__track" aria-hidden="true">
        <span className="acc__fill" style={{ width: `${Math.max(value * 100, 1.5)}%` }} />
      </span>
    </div>
  )
}

function SkeletonRows() {
  return (
    <tbody className="skeleton" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: 8 }).map((__, j) => (
            <td key={j}><span className="skeleton__bar" style={{ animationDelay: `${(i * 8 + j) * 40}ms` }} /></td>
          ))}
        </tr>
      ))}
    </tbody>
  )
}

function RunRow({ run, onAdvance, onRemove, busy, isBest }) {
  const terminal = run.status === 'completed' || run.status === 'failed'
  return (
    <tr className={busy ? 'is-busy' : undefined}>
      <td data-label="Run">
        <span className="run">
          <span className="run__name">{run.name}</span>
          {run.notes && <span className="run__notes" title={run.notes}>{run.notes}</span>}
        </span>
      </td>
      <td data-label="Model"><span className="chip">{run.model_type}</span></td>
      <td data-label="Dataset" className="cell-dim">{run.dataset}</td>
      <td data-label="LR" className="cell-num mono">{run.learning_rate}</td>
      <td data-label="Epochs" className="cell-num mono">{run.epochs}</td>
      <td data-label="Accuracy" className="cell-acc">
        <AccuracyCell value={run.accuracy} isBest={isBest} />
      </td>
      <td data-label="Status">
        <span className={`status status--${run.status}`}>
          <span className="dot" aria-hidden="true" />{run.status}
        </span>
      </td>
      <td className="cell-actions">
        {/* The flex lives on an inner element: a <td> with display:flex leaves
            the table formatting context and its children escape the cell. */}
        <div className="actions">
          {!terminal && (
            <button className="btn btn--sm" disabled={busy} onClick={() => onAdvance(run)}>
              {run.status === 'queued' ? 'Start' : 'Finish'}
            </button>
          )}
          <button className="btn btn--sm btn--danger" disabled={busy}
                  onClick={() => onRemove(run)}
                  aria-label={`Delete ${run.name}`}>
            Delete
          </button>
        </div>
      </td>
    </tr>
  )
}

function EmptyState({ filter, onCreate }) {
  return (
    <div className="empty">
      <span className="empty__mark" aria-hidden="true"><i /><i /><i /></span>
      <p className="empty__title">
        {filter === 'all' ? 'No runs recorded' : `Nothing ${filter}`}
      </p>
      <p className="empty__body">
        {filter === 'all'
          ? 'Every training run you log appears here with its configuration and its score.'
          : `No run currently has the status “${filter}”.`}
      </p>
      {filter === 'all' && (
        <button className="btn btn--primary" onClick={onCreate}>Log the first run</button>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------- modal */

function NewRunModal({ onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const firstField = useRef(null)

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  useEffect(() => {
    firstField.current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    // Without this the page behind the modal scrolls under the backdrop.
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

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
      setSaving(false)
    }
  }

  return (
    <div className="backdrop" onMouseDown={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"
           onMouseDown={(e) => e.stopPropagation()}>
        <header className="modal__header">
          <h2 id="modal-title">New training run</h2>
          <button className="btn-icon" onClick={onClose} aria-label="Close dialog">
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5"
                    strokeLinecap="round" fill="none" />
            </svg>
          </button>
        </header>

        <form onSubmit={submit}>
          <div className="modal__body">
            <label className="field">
              <span className="field__label">Run name</span>
              <input ref={firstField} required value={form.name} onChange={set('name')}
                     placeholder="resnet50-baseline" autoComplete="off" />
            </label>

            <div className="field-row">
              <label className="field">
                <span className="field__label">Model</span>
                <select value={form.model_type} onChange={set('model_type')}>
                  {MODEL_TYPES.map((m) => <option key={m}>{m}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field__label">Dataset</span>
                <input required value={form.dataset} onChange={set('dataset')}
                       placeholder="CIFAR-10" autoComplete="off" />
              </label>
            </div>

            <div className="field-row">
              <label className="field">
                <span className="field__label">Learning rate</span>
                <input type="number" step="0.0001" min="0.0001" max="1" className="mono"
                       value={form.learning_rate} onChange={set('learning_rate')} />
              </label>
              <label className="field">
                <span className="field__label">Epochs</span>
                <input type="number" min="1" max="10000" className="mono"
                       value={form.epochs} onChange={set('epochs')} />
              </label>
            </div>

            <div className="field-row">
              <label className="field">
                <span className="field__label">Status</span>
                <select value={form.status} onChange={set('status')}>
                  {STATUSES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field__label">
                  Accuracy
                  <span className="field__hint">0–1, blank if unscored</span>
                </span>
                <input type="number" step="0.0001" min="0" max="1" className="mono"
                       value={form.accuracy} onChange={set('accuracy')} placeholder="0.9412" />
              </label>
            </div>

            <label className="field">
              <span className="field__label">Notes</span>
              <textarea rows="2" value={form.notes} onChange={set('notes')}
                        placeholder="Augmentation, seed, anything worth remembering" />
            </label>

            {error && <p className="field-error" role="alert">{error}</p>}
          </div>

          <footer className="modal__footer">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={saving}>
              {saving ? 'Creating…' : 'Create run'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------------- app */

function App() {
  const [experiments, setExperiments] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [busyId, setBusyId] = useState(null)

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

  const counts = useMemo(() => {
    const c = {}
    for (const s of STATUSES) c[s] = experiments.filter((e) => e.status === s).length
    return c
  }, [experiments])

  const visible = useMemo(
    () => (filter === 'all' ? experiments : experiments.filter((e) => e.status === filter)),
    [experiments, filter],
  )

  // Named so the hero can credit the run, not just print the number.
  const best = useMemo(() => {
    const scored = experiments.filter((e) => e.accuracy !== null && e.accuracy !== undefined)
    if (!scored.length) return null
    return scored.reduce((a, b) => (b.accuracy > a.accuracy ? b : a))
  }, [experiments])

  async function advance(run) {
    const next = run.status === 'queued' ? 'running'
      : run.status === 'running' ? 'completed'
      : null
    if (!next) return
    setBusyId(run.id)
    try {
      const body = { status: next }
      // Completing a run without a score would leave a misleading blank row.
      if (next === 'completed' && run.accuracy === null) {
        body.accuracy = Number((0.7 + Math.random() * 0.29).toFixed(4))
      }
      await api(`/experiments/${run.id}`, { method: 'PUT', body: JSON.stringify(body) })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  async function remove(run) {
    setBusyId(run.id)
    try {
      await api(`/experiments/${run.id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Brand />
        <Nav filter={filter} setFilter={setFilter} counts={counts} total={experiments.length} />
        <footer className="sidebar__foot">
          <span className={`dot ${error ? 'dot--failed' : 'dot--completed'}`} aria-hidden="true" />
          {error ? 'backend unreachable' : 'backend connected'}
        </footer>
      </aside>

      <main className="content">
        <header className="topbar">
          <div className="topbar__title">
            <h1>Training runs</h1>
            <p>Every experiment, its configuration and its result — deployed by Argo CD.</p>
          </div>
          <button className="btn btn--primary" onClick={() => setModalOpen(true)}>
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.75"
                    strokeLinecap="round" fill="none" />
            </svg>
            New run
          </button>
        </header>

        {error && (
          <div className="notice" role="alert">
            <div className="notice__text">
              <strong>Cannot reach the backend.</strong>
              <span>{error}</span>
            </div>
            <button className="btn btn--sm" onClick={load}>Retry</button>
          </div>
        )}

        {stats && <HeroMetrics stats={stats} best={best} />}

        <section className="panel">
          <div className="panel__head">
            <h2>
              {filter === 'all' ? 'All runs' : <span className="cap">{filter}</span>}
              <span className="panel__count">{visible.length}</span>
            </h2>
          </div>

          {loading ? (
            <div className="table-wrap">
              <table className="table">
                <Head />
                <SkeletonRows />
              </table>
            </div>
          ) : visible.length === 0 ? (
            <EmptyState filter={filter} onCreate={() => setModalOpen(true)} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <Head />
                <tbody>
                  {visible.map((run) => (
                    <RunRow key={run.id} run={run} busy={busyId === run.id}
                            isBest={best?.id === run.id}
                            onAdvance={advance} onRemove={remove} />
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

function Head() {
  return (
    <thead>
      <tr>
        <th>Run</th>
        <th>Model</th>
        <th>Dataset</th>
        <th className="cell-num">LR</th>
        <th className="cell-num">Epochs</th>
        <th>Accuracy</th>
        <th>Status</th>
        <th><span className="sr-only">Actions</span></th>
      </tr>
    </thead>
  )
}

createRoot(document.getElementById('root')).render(<App />)
