import { useState, useEffect, useCallback } from 'react'
import { kpisApi, analyticsApi } from '../services/api'
import Header from '../components/Header'
import StatCard from '../components/StatCard'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
  LineChart, Line, CartesianGrid, Legend
} from 'recharts'

const PIE_COLORS = ['#6366f1','#4ade80','#f87171','#fbbf24','#60a5fa','#c084fc','#fb923c']

function fmt(n) {
  if (n == null) return '—'
  return typeof n === 'number' ? n.toLocaleString() : n
}

export default function Dashboard() {
  const [kpis, setKpis] = useState(null)
  const [campaigns, setCampaigns] = useState([])
  const [dispositions, setDispositions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [kRes, cRes, dRes] = await Promise.all([
        kpisApi.getOverview(),
        analyticsApi.campaigns(8),
        analyticsApi.dispositions(),
      ])
      setKpis(kRes.data)
      setCampaigns(cRes.data || [])
      setDispositions(dRes.data || [])
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Agent state distribution from kpis
  const agentPie = kpis
    ? [
        { name: 'Available', value: kpis.available_agents },
        { name: 'Offline',   value: kpis.offline_agents   },
        { name: 'Other',     value: Math.max(0, kpis.total_agents - kpis.available_agents - kpis.offline_agents) },
      ].filter(d => d.value > 0)
    : []

  return (
    <>
      <Header
        title="Dashboard"
        subtitle="Real-time collections operations overview"
        onRefresh={load}
      />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}
        {loading ? <Loading /> : kpis && (
          <>
            {/* KPI row */}
            <div className="stat-grid">
              <StatCard label="Total Calls"     value={fmt(kpis.total_calls)}     icon="📞" color="brand" />
              <StatCard label="Answered"         value={fmt(kpis.answered_calls)}  icon="✅" color="green" />
              <StatCard label="Answer Rate"      value={`${kpis.overall_answer_rate}%`} icon="📈" color="blue" />
              <StatCard label="Avg Talk Time"    value={`${kpis.avg_talk_duration_sec}s`} icon="⏱" color="purple" />
              <StatCard label="Total Agents"     value={fmt(kpis.total_agents)}    icon="👤" color="brand" />
              <StatCard label="Available Agents" value={fmt(kpis.available_agents)} icon="🟢" color="green" />
              <StatCard label="Total Borrowers"  value={fmt(kpis.total_borrowers)}  icon="🏠" color="orange" />
              <StatCard label="Eligible"         value={fmt(kpis.eligible_borrowers)} icon="🎯" color="yellow" />
              <StatCard label="Total Campaigns"  value={fmt(kpis.total_campaigns)} icon="📋" color="blue" />
              <StatCard label="Total Accounts"   value={fmt(kpis.total_accounts)}  icon="🗂" color="purple" />
              <StatCard label="Failure Rate"     value={`${kpis.failure_rate}%`}   icon="⚠" color="red" />
              <StatCard label="Attempts/Borrower" value={fmt(kpis.attempts_per_borrower)} icon="🔄" color="orange" />
            </div>

            <div className="grid-2" style={{ marginBottom: 24 }}>
              {/* Agent distribution pie */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Agent Status Distribution</span>
                </div>
                <div className="card-body" style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {agentPie.length > 0 ? (
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie data={agentPie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={88} paddingAngle={3}>
                          {agentPie.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                        </Pie>
                        <Tooltip
                          contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-bright)', borderRadius: 8 }}
                          labelStyle={{ color: 'var(--text-secondary)' }}
                          itemStyle={{ color: 'var(--text-primary)' }}
                        />
                        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <span className="text-muted">No agent data</span>}
                </div>
              </div>

              {/* Call dispositions pie */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Call Outcome Breakdown</span>
                </div>
                <div className="card-body" style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {dispositions.length > 0 ? (
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie
                          data={dispositions.slice(0, 8)}
                          dataKey="count"
                          nameKey="status"
                          innerRadius={50}
                          outerRadius={85}
                          paddingAngle={3}
                        >
                          {dispositions.slice(0, 8).map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                        </Pie>
                        <Tooltip
                          contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-bright)', borderRadius: 8 }}
                          labelStyle={{ color: 'var(--text-secondary)' }}
                          itemStyle={{ color: 'var(--text-primary)' }}
                        />
                        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <span className="text-muted">No disposition data</span>}
                </div>
              </div>
            </div>

            {/* Campaign performance bar chart */}
            <div className="card" style={{ marginBottom: 24 }}>
              <div className="card-header">
                <span className="card-title">Campaign Performance — Answer Rate (%)</span>
              </div>
              <div className="card-body" style={{ height: 280 }}>
                {campaigns.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={campaigns} margin={{ top: 8, right: 16, left: 0, bottom: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis
                        dataKey="campaign_name"
                        tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                        angle={-30}
                        textAnchor="end"
                        interval={0}
                      />
                      <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit="%" />
                      <Tooltip
                        contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-bright)', borderRadius: 8 }}
                        labelStyle={{ color: 'var(--text-secondary)' }}
                        itemStyle={{ color: 'var(--text-primary)' }}
                      />
                      <Bar dataKey="answer_rate" fill="#6366f1" radius={[4, 4, 0, 0]} name="Answer Rate %" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div className="empty-state"><div className="empty-state-icon">📊</div><span>No campaign data available</span></div>}
              </div>
            </div>

            {/* Call outcomes detail */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Historical KPI Summary</span>
              </div>
              <div className="card-body">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
                  {[
                    { label: 'No Answer Rate', value: `${kpis.no_answer_rate}%`, color: 'var(--yellow-400)' },
                    { label: 'Busy Rate',       value: `${kpis.busy_rate}%`,       color: 'var(--orange-400)' },
                    { label: 'Voicemail Rate',  value: `${kpis.voicemail_rate}%`,  color: 'var(--blue-400)' },
                    { label: 'Failure Rate',    value: `${kpis.failure_rate}%`,    color: 'var(--red-400)' },
                    { label: 'Offline Agents',  value: fmt(kpis.offline_agents),   color: 'var(--red-400)' },
                  ].map(item => (
                    <div key={item.label} style={{ background: 'var(--bg-raised)', borderRadius: 8, padding: '10px 14px' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{item.label}</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: item.color, fontVariantNumeric: 'tabular-nums' }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
