import { useState, useEffect, useCallback } from 'react'
import { simulationApi } from '../services/api'
import Header from '../components/Header'
import StatusBadge from '../components/StatusBadge'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import {
  BarChart, Bar, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts'

export default function Simulation() {
  const [scenarios, setScenarios]   = useState([])
  const [history, setHistory]       = useState([])
  const [result, setResult]         = useState(null)
  const [loading, setLoading]       = useState(true)
  const [running, setRunning]       = useState(false)
  const [error, setError]           = useState(null)
  const [toast, setToast]           = useState(null)

  const [form, setForm] = useState({
    scenario: 'Scenario A',
    dialing_mode: 'PROGRESSIVE',
    agent_count: 30,
    cycles: 4,
    provider_name: 'mock_a',
    seed: 42,
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [sRes, hRes] = await Promise.all([
        simulationApi.listScenarios(),
        simulationApi.history(10),
      ])
      setScenarios(sRes.data || [])
      setHistory(hRes.data || [])
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  const runSim = async () => {
    setRunning(true)
    setResult(null)
    setError(null)
    try {
      const res = await simulationApi.run(form)
      setResult(res.data)
      showToast('Simulation completed', 'success')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Simulation failed', 'error')
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setRunning(false)
    }
  }

  const tooltipStyle = {
    contentStyle: { background: 'var(--bg-raised)', border: '1px solid var(--border-bright)', borderRadius: 8 },
    labelStyle:   { color: 'var(--text-secondary)' },
    itemStyle:    { color: 'var(--text-primary)' },
  }

  const chartData = result ? [
    { name: 'Initiated',  value: result.calls_initiated },
    { name: 'Answered',   value: result.calls_answered  },
    { name: 'Completed',  value: result.calls_completed },
    { name: 'Failed',     value: result.calls_failed    },
    { name: 'Abandoned',  value: result.calls_abandoned },
  ] : []

  const safetyData = result ? [
    { name: 'Approvals',   value: result.safety_approvals   },
    { name: 'Reductions',  value: result.safety_reductions  },
    { name: 'Rejections',  value: result.safety_rejections  },
  ] : []

  const selectedScenario = scenarios.find(s => s.name === form.scenario)

  return (
    <>
      <Header title="Simulation" subtitle="Run isolated dialing scenarios — data never mingles with historical records" onRefresh={load} />
      <div className="page-content">
        {error && <ErrorMessage message={error} />}
        {loading ? <Loading /> : (
          <>
            <div className="grid-2 mb-16">
              {/* Config form */}
              <div className="card">
                <div className="card-header"><span className="card-title">Simulation Configuration</span></div>
                <div className="card-body">
                  <div className="sim-grid">
                    <div className="form-group">
                      <label className="form-label">Scenario</label>
                      <select
                        className="form-control"
                        value={form.scenario}
                        onChange={e => setForm(f => ({ ...f, scenario: e.target.value }))}
                        id="sim-scenario"
                      >
                        {scenarios.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Dialing Mode</label>
                      <select
                        className="form-control"
                        value={form.dialing_mode}
                        onChange={e => setForm(f => ({ ...f, dialing_mode: e.target.value }))}
                        id="sim-mode"
                      >
                        <option value="PROGRESSIVE">Progressive</option>
                        <option value="PREDICTIVE">Predictive</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Agent Count</label>
                      <input
                        type="number" className="form-control" min={1} max={500}
                        value={form.agent_count}
                        onChange={e => setForm(f => ({ ...f, agent_count: parseInt(e.target.value) || 1 }))}
                        id="sim-agent-count"
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Cycles</label>
                      <input
                        type="number" className="form-control" min={1} max={20}
                        value={form.cycles}
                        onChange={e => setForm(f => ({ ...f, cycles: parseInt(e.target.value) || 1 }))}
                        id="sim-cycles"
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Provider</label>
                      <select
                        className="form-control"
                        value={form.provider_name}
                        onChange={e => setForm(f => ({ ...f, provider_name: e.target.value }))}
                        id="sim-provider"
                      >
                        <option value="mock_a">Provider A (Reliable)</option>
                        <option value="mock_b">Provider B (Noisy)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Random Seed</label>
                      <input
                        type="number" className="form-control"
                        value={form.seed}
                        onChange={e => setForm(f => ({ ...f, seed: parseInt(e.target.value) || 0 }))}
                        id="sim-seed"
                      />
                    </div>
                  </div>

                  {selectedScenario && (
                    <div style={{ padding: '8px 12px', background: 'var(--bg-raised)', borderRadius: 8, marginBottom: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                      <strong style={{ color: 'var(--text-secondary)' }}>{selectedScenario.name}</strong>: {selectedScenario.description}
                      &nbsp;· Answer rate: {(selectedScenario.base_answer_rate * 100).toFixed(0)}%
                      &nbsp;· Avg talk: {selectedScenario.base_talk_time}s
                    </div>
                  )}

                  <button
                    className="btn btn-primary w-full"
                    onClick={runSim}
                    disabled={running}
                    id="run-simulation-btn"
                  >
                    {running ? '⏳ Running Simulation…' : '▶ Run Simulation'}
                  </button>
                </div>
              </div>

              {/* Result panel */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Last Result</span>
                  {result && <StatusBadge value={result.status} />}
                </div>
                <div className="card-body">
                  {running && <Loading text="Running simulation…" />}
                  {!running && !result && (
                    <div className="empty-state">
                      <div className="empty-state-icon">⚡</div>
                      Run a simulation to see results here
                    </div>
                  )}
                  {result && !running && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      {[
                        { label: 'Calls Initiated',    value: result.calls_initiated },
                        { label: 'Calls Answered',     value: result.calls_answered  },
                        { label: 'Calls Completed',    value: result.calls_completed },
                        { label: 'Calls Failed',       value: result.calls_failed    },
                        { label: 'Abandoned',          value: result.calls_abandoned },
                        { label: 'Max Concurrent',     value: result.max_concurrent_calls },
                        { label: 'Agent Utilization',  value: `${(result.agent_utilization * 100).toFixed(1)}%` },
                        { label: 'Avg Wait (s)',        value: result.avg_wait_time_sec?.toFixed(1) },
                        { label: 'Safety Approvals',   value: result.safety_approvals   },
                        { label: 'Safety Reductions',  value: result.safety_reductions  },
                        { label: 'Safety Rejections',  value: result.safety_rejections  },
                      ].map(item => (
                        <div key={item.label} style={{ background: 'var(--bg-raised)', borderRadius: 6, padding: '8px 10px' }}>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 2 }}>{item.label}</div>
                          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{item.value}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Charts */}
            {result && (
              <div className="grid-2 mb-16">
                <div className="card">
                  <div className="card-header"><span className="card-title">Call Outcomes</span></div>
                  <div className="card-body" style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <Tooltip {...tooltipStyle} />
                        <Bar dataKey="value" fill="#6366f1" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><span className="card-title">Safety Decisions</span></div>
                  <div className="card-body" style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={safetyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <Tooltip {...tooltipStyle} />
                        <Bar dataKey="value" fill="#4ade80" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}

            {/* Simulation history */}
            <div className="card">
              <div className="card-header"><span className="card-title">Simulation History (Last 10)</span></div>
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Mode</th>
                      <th>Calls Init.</th>
                      <th>Answered</th>
                      <th>Agent Util.</th>
                      <th>Approvals</th>
                      <th>Reductions</th>
                      <th>Rejections</th>
                      <th>Status</th>
                      <th>Run At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.length === 0 ? (
                      <tr><td colSpan={10} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>No simulations run yet</td></tr>
                    ) : history.map(h => (
                      <tr key={h.simulation_id}>
                        <td>{h.scenario}</td>
                        <td><StatusBadge value={h.dialing_mode} /></td>
                        <td>{h.calls_initiated}</td>
                        <td>{h.calls_answered}</td>
                        <td>{(h.agent_utilization * 100).toFixed(1)}%</td>
                        <td style={{ color: 'var(--green-400)' }}>{h.safety_approvals}</td>
                        <td style={{ color: 'var(--yellow-400)' }}>{h.safety_reductions}</td>
                        <td style={{ color: 'var(--red-400)' }}>{h.safety_rejections}</td>
                        <td><StatusBadge value={h.status} /></td>
                        <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{h.created_at ? new Date(h.created_at).toLocaleString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
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
