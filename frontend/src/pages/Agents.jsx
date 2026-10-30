import { useState, useEffect, useCallback } from 'react'
import { agentsApi } from '../services/api'
import Header from '../components/Header'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

const STATUSES = ['', 'AVAILABLE', 'OFFLINE', 'RESERVED', 'DIALING', 'CONNECTED', 'WRAP_UP', 'PAUSED']

export default function Agents() {
  const [data, setData]     = useState({ total: 0, items: [] })
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage]     = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: 25 }
      if (status) params.status = status
      const res = await agentsApi.list(params)
      setData(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [status, page])

  useEffect(() => { setPage(1) }, [status])
  useEffect(() => { load() }, [load])

  const filtered = search
    ? data.items.filter(a =>
        a.agent_name?.toLowerCase().includes(search.toLowerCase()) ||
        a.agent_id?.toLowerCase().includes(search.toLowerCase()) ||
        a.team?.toLowerCase().includes(search.toLowerCase())
      )
    : data.items

  const columns = [
    { key: 'agent_id',   label: 'Agent ID',   render: v => <span className="mono">{v}</span> },
    { key: 'agent_name', label: 'Name' },
    { key: 'employee_code', label: 'Emp. Code', render: v => v || '—' },
    { key: 'team',       label: 'Team',        render: v => v || '—' },
    { key: 'vendor_id',  label: 'Vendor',      render: v => v || '—' },
    { key: 'status',     label: 'Status',      render: v => <StatusBadge value={v} /> },
    { key: 'current_call_id', label: 'Current Call', render: v => v ? <span className="mono text-sm">{v}</span> : '—' },
    { key: 'updated_at', label: 'Last Updated', render: v => v ? new Date(v).toLocaleString() : '—' },
  ]

  return (
    <>
      <Header
        title="Agents"
        subtitle={`${data.total.toLocaleString()} agents total`}
        onRefresh={load}
      />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}

        <div className="filter-bar">
          <div className="search-wrap">
            <svg className="search-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M9 3a6 6 0 100 12A6 6 0 009 3zm-8 6a8 8 0 1114.32 4.906l4.387 4.387a1 1 0 01-1.414 1.414l-4.387-4.387A8 8 0 011 9z" clipRule="evenodd" />
            </svg>
            <input
              className="search-input"
              placeholder="Search agents…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              id="agents-search"
            />
          </div>

          <select
            className="form-control"
            style={{ width: 'auto' }}
            value={status}
            onChange={e => setStatus(e.target.value)}
            id="agents-status-filter"
          >
            {STATUSES.map(s => (
              <option key={s} value={s}>{s || 'All Statuses'}</option>
            ))}
          </select>
        </div>

        {loading ? <Loading /> : (
          <div className="card">
            <DataTable columns={columns} data={filtered} emptyText="No agents match the current filter" />
            <div className="pagination">
              <button
                className="btn btn-ghost btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                id="agents-prev-page"
              >← Prev</button>
              <span>Page {page}</span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={data.items.length < 25}
                onClick={() => setPage(p => p + 1)}
                id="agents-next-page"
              >Next →</button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
