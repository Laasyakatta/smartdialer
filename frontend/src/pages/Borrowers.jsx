import { useState, useEffect, useCallback } from 'react'
import { borrowersApi } from '../services/api'
import Header from '../components/Header'
import DataTable from '../components/DataTable'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function Borrowers() {
  const [data, setData]         = useState({ total: 0, items: [] })
  const [eligibleOnly, setElig] = useState(false)
  const [search, setSearch]     = useState('')
  const [page, setPage]         = useState(1)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, page_size: 25 }
      if (eligibleOnly) params.eligible_only = true
      const res = await borrowersApi.list(params)
      setData(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [eligibleOnly, page])

  useEffect(() => { setPage(1) }, [eligibleOnly])
  useEffect(() => { load() }, [load])

  const filtered = search
    ? data.items.filter(b =>
        b.borrower_id?.toLowerCase().includes(search.toLowerCase()) ||
        b.name?.toLowerCase().includes(search.toLowerCase()) ||
        b.city?.toLowerCase().includes(search.toLowerCase())
      )
    : data.items

  const columns = [
    { key: 'borrower_id',   label: 'Borrower ID',   render: v => <span className="mono">{v}</span> },
    { key: 'name',          label: 'Name' },
    { key: 'phone_masked',  label: 'Phone (Masked)', render: v => <span className="mono">{v || '—'}</span> },
    { key: 'email_masked',  label: 'Email (Masked)', render: v => <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{v || '—'}</span> },
    { key: 'city',          label: 'City',           render: v => v || '—' },
    { key: 'state',         label: 'State',          render: v => v || '—' },
    {
      key: 'is_eligible',
      label: 'Eligible',
      render: v => (
        <span className={`badge ${v ? 'badge-AVAILABLE' : 'badge-OFFLINE'}`}>
          <span className="badge-dot" />
          {v ? 'Eligible' : 'Ineligible'}
        </span>
      )
    },
    { key: 'ineligibility_reason', label: 'Reason',   render: v => v || '—' },
    { key: 'current_active_call_id', label: 'Active Call', render: v => v ? <span className="mono text-sm">{v}</span> : '—' },
  ]

  return (
    <>
      <Header
        title="Borrowers"
        subtitle={`${data.total.toLocaleString()} borrowers · PII masked`}
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
              placeholder="Search borrowers…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              id="borrowers-search"
            />
          </div>

          <label className="flex-center gap-8" style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 13 }}>
            <input
              type="checkbox"
              checked={eligibleOnly}
              onChange={e => setElig(e.target.checked)}
              id="borrowers-eligible-filter"
            />
            Eligible Only
          </label>
        </div>

        {loading ? <Loading /> : (
          <div className="card">
            <DataTable columns={columns} data={filtered} emptyText="No borrowers match the current filter" />
            <div className="pagination">
              <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)} id="borrowers-prev">← Prev</button>
              <span>Page {page}</span>
              <button className="btn btn-ghost btn-sm" disabled={data.items.length < 25} onClick={() => setPage(p => p + 1)} id="borrowers-next">Next →</button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
