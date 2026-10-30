import { useState, useEffect, useCallback } from 'react'
import { campaignsApi } from '../services/api'
import Header from '../components/Header'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function Campaigns() {
  const [data, setData]       = useState({ total: 0, items: [] })
  const [activeOnly, setActiveOnly] = useState(false)
  const [page, setPage]       = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [toast, setToast]     = useState(null)
  const [busy, setBusy]       = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await campaignsApi.list({ page, page_size: 25, active_only: activeOnly })
      setData(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [activeOnly, page])

  useEffect(() => { setPage(1) }, [activeOnly])
  useEffect(() => { load() }, [load])

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const doStart = async (id) => {
    setBusy(b => ({ ...b, [id]: true }))
    try {
      await campaignsApi.start(id)
      showToast('Campaign started', 'success')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed', 'error')
    } finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  const doPause = async (id) => {
    setBusy(b => ({ ...b, [id]: true }))
    try {
      await campaignsApi.pause(id)
      showToast('Campaign paused', 'info')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed', 'error')
    } finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  const setMode = async (id, mode) => {
    setBusy(b => ({ ...b, [id + mode]: true }))
    try {
      await campaignsApi.setMode(id, mode)
      showToast(`Mode set to ${mode}`, 'success')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed', 'error')
    } finally {
      setBusy(b => ({ ...b, [id + mode]: false }))
    }
  }

  const columns = [
    { key: 'campaign_id',          label: 'ID',       render: v => <span className="mono">{v}</span> },
    { key: 'campaign_name',        label: 'Name' },
    { key: 'channel',              label: 'Channel',  render: v => v || '—' },
    { key: 'dialing_mode',         label: 'Mode',     render: v => <StatusBadge value={v} /> },
    { key: 'is_active',            label: 'Status',   render: v => <StatusBadge value={v ? 'ACTIVE' : 'OFFLINE'} /> },
    { key: 'max_concurrent_calls', label: 'Max Calls' },
    { key: 'target_answer_rate',   label: 'Target AR', render: v => `${(v * 100).toFixed(0)}%` },
    {
      key: '_actions',
      label: 'Controls',
      render: (_, row) => (
        <div className="flex gap-4">
          <button
            className="btn btn-success btn-sm"
            disabled={row.is_active || busy[row.campaign_id]}
            onClick={() => doStart(row.campaign_id)}
            id={`start-${row.campaign_id}`}
          >▶</button>
          <button
            className="btn btn-danger btn-sm"
            disabled={!row.is_active || busy[row.campaign_id]}
            onClick={() => doPause(row.campaign_id)}
            id={`pause-${row.campaign_id}`}
          >⏸</button>
          <button
            className="btn btn-ghost btn-sm"
            disabled={busy[row.campaign_id + 'PROGRESSIVE']}
            onClick={() => setMode(row.campaign_id, 'PROGRESSIVE')}
            title="Set Progressive"
          >P</button>
          <button
            className="btn btn-ghost btn-sm"
            disabled={busy[row.campaign_id + 'PREDICTIVE']}
            onClick={() => setMode(row.campaign_id, 'PREDICTIVE')}
            title="Set Predictive"
          >AI</button>
        </div>
      )
    },
  ]

  return (
    <>
      <Header
        title="Campaigns"
        subtitle={`${data.total.toLocaleString()} campaigns · Start, Pause, Switch Mode`}
        onRefresh={load}
      />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}

        <div className="filter-bar">
          <label className="flex-center gap-8" style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 13 }}>
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={e => setActiveOnly(e.target.checked)}
              id="campaigns-active-filter"
            />
            Active Only
          </label>
        </div>

        {loading ? <Loading /> : (
          <div className="card">
            <DataTable columns={columns} data={data.items} emptyText="No campaigns found" />
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
