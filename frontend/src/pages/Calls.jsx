import { useState, useEffect, useCallback } from 'react'
import { callsApi, campaignsApi } from '../services/api'
import Header from '../components/Header'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

const STATES = ['', 'QUEUED', 'RESERVED', 'INITIATED', 'RINGING', 'ANSWERED', 'CONNECTED', 'COMPLETED', 'FAILED', 'CANCELLED']

export default function Calls() {
  const [data, setData]       = useState({ total: 0, items: [] })
  const [state, setState]     = useState('')
  const [simOnly, setSimOnly] = useState(null)
  const [page, setPage]       = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  const [dialForm, setDialForm] = useState({ campaign_id: '', provider_name: 'mock_a', batch_size: 5, answer_probability: 0.20, talk_time_sec: 60 })
  const [dialMode, setDialMode] = useState('progressive')
  const [campaigns, setCampaigns] = useState([])
  const [toast, setToast]   = useState(null)
  const [dialling, setDialling] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: 25 }
      if (state) params.state = state
      if (simOnly !== null) params.is_simulation = simOnly
      const [cRes, res] = await Promise.all([
        campaignsApi.list({ page_size: 100 }),
        callsApi.list(params),
      ])
      setCampaigns(cRes.data.items || [])
      setData(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [state, simOnly, page])

  useEffect(() => { setPage(1) }, [state, simOnly])
  useEffect(() => { load() }, [load])

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  const triggerDial = async () => {
    if (!dialForm.campaign_id) { showToast('Select a campaign first', 'error'); return }
    setDialling(true)
    try {
      const fn = dialMode === 'progressive' ? callsApi.triggerProgressive : callsApi.triggerPredictive
      const res = await fn(dialForm)
      showToast(`Cycle complete — ${JSON.stringify(res.data).slice(0, 80)}`, 'success')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Dial failed', 'error')
    } finally {
      setDialling(false)
    }
  }

  const columns = [
    { key: 'call_id',       label: 'Call ID',     render: v => <span className="mono" style={{ fontSize: 11 }}>{v.slice(0, 12)}…</span> },
    { key: 'borrower_id',   label: 'Borrower',    render: v => <span className="mono">{v.slice(0, 10)}…</span> },
    { key: 'agent_id',      label: 'Agent',       render: v => v ? <span className="mono">{v.slice(0, 10)}…</span> : '—' },
    { key: 'provider_name', label: 'Provider' },
    { key: 'state',         label: 'State',       render: v => <StatusBadge value={v} /> },
    { key: 'terminal_reason', label: 'Reason',    render: v => v || '—' },
    { key: 'duration_sec',  label: 'Duration',    render: v => v ? `${v}s` : '—' },
    { key: 'queued_at',     label: 'Queued At',   render: v => v ? new Date(v).toLocaleTimeString() : '—' },
    { key: 'is_simulation', label: 'Sim?',        render: v => v ? <span style={{ color: 'var(--yellow-400)', fontSize: 11 }}>SIM</span> : '—' },
  ]

  return (
    <>
      <Header title="Calls" subtitle={`${data.total.toLocaleString()} calls`} onRefresh={load} />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}

        {/* Dial trigger */}
        <div className="card mb-16">
          <div className="card-header"><span className="card-title">Trigger Dial Cycle</span></div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 12, marginBottom: 12 }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Mode</label>
                <select className="form-control" value={dialMode} onChange={e => setDialMode(e.target.value)} id="dial-mode">
                  <option value="progressive">Progressive</option>
                  <option value="predictive">Predictive</option>
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Campaign</label>
                <select
                  className="form-control"
                  value={dialForm.campaign_id}
                  onChange={e => setDialForm(f => ({ ...f, campaign_id: e.target.value }))}
                  id="dial-campaign"
                >
                  <option value="">— Select —</option>
                  {campaigns.map(c => <option key={c.campaign_id} value={c.campaign_id}>{c.campaign_name}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Provider</label>
                <select className="form-control" value={dialForm.provider_name} onChange={e => setDialForm(f => ({ ...f, provider_name: e.target.value }))} id="dial-provider">
                  <option value="mock_a">Provider A</option>
                  <option value="mock_b">Provider B</option>
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Batch Size</label>
                <input className="form-control" type="number" min={1} max={50} value={dialForm.batch_size}
                  onChange={e => setDialForm(f => ({ ...f, batch_size: parseInt(e.target.value) || 1 }))} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Answer Rate (0-1)</label>
                <input className="form-control" type="number" min={0} max={1} step={0.05} value={dialForm.answer_probability}
                  onChange={e => setDialForm(f => ({ ...f, answer_probability: parseFloat(e.target.value) || 0 }))} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Talk Time (s)</label>
                <input className="form-control" type="number" min={5} value={dialForm.talk_time_sec}
                  onChange={e => setDialForm(f => ({ ...f, talk_time_sec: parseInt(e.target.value) || 30 }))} />
              </div>
            </div>
            <button className="btn btn-primary" onClick={triggerDial} disabled={dialling} id="trigger-dial-btn">
              {dialling ? '⏳ Running…' : `▶ Run ${dialMode} cycle`}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="filter-bar">
          <select className="form-control" style={{ width: 'auto' }} value={state} onChange={e => setState(e.target.value)} id="calls-state-filter">
            {STATES.map(s => <option key={s} value={s}>{s || 'All States'}</option>)}
          </select>
          <select className="form-control" style={{ width: 'auto' }} value={simOnly === null ? '' : String(simOnly)} onChange={e => setSimOnly(e.target.value === '' ? null : e.target.value === 'true')} id="calls-sim-filter">
            <option value="">All (Historical + Sim)</option>
            <option value="false">Historical Only</option>
            <option value="true">Simulation Only</option>
          </select>
        </div>

        {loading ? <Loading /> : (
          <div className="card">
            <DataTable columns={columns} data={data.items} emptyText="No calls match the current filter" />
            <div className="pagination">
              <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span>Page {page}</span>
              <button className="btn btn-ghost btn-sm" disabled={data.items.length < 25} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          </div>
        )}
      </div>

      {toast && (
        <div className="toast-wrap">
          <div className={`toast ${toast.type}`}>{toast.msg}</div>
        </div>
      )}
    </>
  )
}
