import { useState, useEffect, useCallback } from 'react'
import { analyticsApi } from '../services/api'
import Header from '../components/Header'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
  CartesianGrid, Legend
} from 'recharts'

const COLORS = ['#6366f1', '#4ade80', '#f87171', '#fbbf24', '#60a5fa', '#c084fc', '#fb923c', '#2dd4bf']

export default function Analytics() {
  const [campaigns, setCampaigns]     = useState([])
  const [vendors, setVendors]         = useState([])
  const [dispositions, setDispositions] = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [cRes, vRes, dRes] = await Promise.all([
        analyticsApi.campaigns(15),
        analyticsApi.vendors(),
        analyticsApi.dispositions(),
      ])
      setCampaigns(cRes.data || [])
      setVendors(vRes.data || [])
      setDispositions(dRes.data || [])
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const tooltipStyle = {
    contentStyle: { background: 'var(--bg-raised)', border: '1px solid var(--border-bright)', borderRadius: 8 },
    labelStyle:   { color: 'var(--text-secondary)' },
    itemStyle:    { color: 'var(--text-primary)' },
  }

  return (
    <>
      <Header title="Analytics" subtitle="Historical dataset metrics — separated from simulation data" onRefresh={load} />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}
        {loading ? <Loading /> : (
          <>
            {/* Campaign performance */}
            <div className="card mb-16">
              <div className="card-header">
                <span className="card-title">Campaign Performance — Calls Initiated vs Answered</span>
                <span className="badge badge-AVAILABLE" style={{ fontSize: 10 }}>Historical Data</span>
              </div>
              <div className="card-body" style={{ height: 320 }}>
                {campaigns.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={campaigns} margin={{ top: 8, right: 16, left: 0, bottom: 60 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="campaign_name" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
                      <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                      <Tooltip {...tooltipStyle} />
                      <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                      <Bar dataKey="total_calls"   fill="#6366f1" radius={[4,4,0,0]} name="Total Calls" />
                      <Bar dataKey="answered_calls" fill="#4ade80" radius={[4,4,0,0]} name="Answered" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="empty-state"><div className="empty-state-icon">📊</div>No campaign data</div>}
              </div>
            </div>

            <div className="grid-2 mb-16">
              {/* Campaign answer rate */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Answer Rate by Campaign</span>
                </div>
                <div className="card-body" style={{ height: 260 }}>
                  {campaigns.length > 0 ? (
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={campaigns} margin={{ top: 8, right: 8, left: 0, bottom: 50 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="campaign_name" tick={{ fill: 'var(--text-muted)', fontSize: 9 }} angle={-25} textAnchor="end" interval={0} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit="%" domain={[0, 100]} />
                        <Tooltip {...tooltipStyle} formatter={(v) => [`${v}%`, 'Answer Rate']} />
                        <Bar dataKey="answer_rate" fill="#60a5fa" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <div className="empty-state">No data</div>}
                </div>
              </div>

              {/* Call dispositions */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Call Outcome Distribution</span>
                </div>
                <div className="card-body" style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {dispositions.length > 0 ? (
                    <ResponsiveContainer width="100%" height={240}>
                      <PieChart>
                        <Pie data={dispositions.slice(0,8)} dataKey="count" nameKey="status" innerRadius={55} outerRadius={90} paddingAngle={3}>
                          {dispositions.slice(0,8).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip {...tooltipStyle} />
                        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <div className="empty-state">No disposition data</div>}
                </div>
              </div>
            </div>

            {/* Vendor performance */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Telephony Vendor Performance</span>
                <span className="badge badge-AVAILABLE" style={{ fontSize: 10 }}>Historical Data</span>
              </div>
              <div className="card-body">
                {vendors.length > 0 ? (
                  <div style={{ overflowX: 'auto' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Vendor ID</th>
                          <th>Total Calls</th>
                          <th>Answered</th>
                          <th>Answer Rate</th>
                          <th>Failure Rate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {vendors.map((v, i) => (
                          <tr key={i}>
                            <td className="mono">{v.vendor_id || '—'}</td>
                            <td>{v.total_calls?.toLocaleString()}</td>
                            <td>{v.answered_calls?.toLocaleString()}</td>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                                  <div style={{ width: `${v.answer_rate}%`, height: '100%', background: 'var(--green-400)', borderRadius: 3 }} />
                                </div>
                                <span>{v.answer_rate}%</span>
                              </div>
                            </td>
                            <td style={{ color: v.failure_rate > 5 ? 'var(--red-400)' : 'var(--text-secondary)' }}>
                              {v.failure_rate}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <div className="empty-state"><div className="empty-state-icon">📡</div>No vendor data</div>}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
