import { useState, useEffect, useCallback } from 'react'
import { safetyApi, agentsApi } from '../services/api'
import Header from '../components/Header'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function SafetyController() {
  const [status, setStatus]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [toast, setToast]     = useState(null)
  const [dropping, setDropping] = useState(false)
  const [dropCount, setDropCount] = useState(10)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await safetyApi.getStatus()
      setStatus(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const showToast = (msg, type = 'info') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const simulateDrop = async () => {
    setDropping(true)
    try {
      const res = await agentsApi.disconnectBatch(dropCount)
      showToast(`Disconnected ${res.data.actual_dropped} agents — safety should react`, 'error')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed', 'error')
    } finally {
      setDropping(false)
    }
  }

  const ac = status?.agent_capacity
  const cc = status?.call_capacity
  const providers = status?.providers_health || []

  return (
    <>
      <Header title="Safety Controller" subtitle="Independent hard-limit guard between pacing engine and allocator" onRefresh={load} />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}
        {loading ? <Loading /> : status && (
          <>
            {/* Safety guard status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, padding: '12px 16px', background: status.system_ready_to_dial ? 'var(--green-bg)' : 'var(--red-bg)', border: `1px solid ${status.system_ready_to_dial ? 'rgba(74,222,128,.2)' : 'rgba(248,113,113,.2)'}`, borderRadius: 10 }}>
              <span style={{ fontSize: 22 }}>{status.system_ready_to_dial ? '✅' : '🛑'}</span>
              <div>
                <div style={{ fontWeight: 600, color: status.system_ready_to_dial ? 'var(--green-400)' : 'var(--red-400)' }}>
                  System {status.system_ready_to_dial ? 'Ready to Dial' : 'NOT Ready — Safety Gate Engaged'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  Safety guard: <strong style={{ color: 'var(--green-400)' }}>ACTIVE</strong>
                  &nbsp;·&nbsp;
                  Bypass allowed: <strong style={{ color: 'var(--red-400)' }}>NEVER</strong>
                  &nbsp;(architectural invariant)
                </div>
              </div>
            </div>

            {/* Agent capacity */}
            <div className="stat-grid" style={{ marginBottom: 20 }}>
              <StatCard label="Available Agents"  value={ac?.available}              icon="🟢" color="green" />
              <StatCard label="Reserved"           value={ac?.reserved}               icon="🟡" color="yellow" />
              <StatCard label="Dialing"            value={ac?.dialing}                icon="📞" color="blue" />
              <StatCard label="Connected"          value={ac?.connected}              icon="✅" color="green" />
              <StatCard label="Usable Headroom"    value={ac?.usable_slots_headroom}  icon="🎯" color="brand" sub="Available − In-flight" />
              <StatCard label="In-Flight Calls"    value={cc?.in_flight_pre_connect}  icon="⚡" color="yellow" sub="Reserved+Initiated+Ringing" />
              <StatCard label="Connected Talkers"  value={cc?.connected_talkers}      icon="🔊" color="purple" />
            </div>

            {/* Safety formula explanation */}
            <div className="card mb-16">
              <div className="card-header"><span className="card-title">Hard Capacity Formula (Invariant)</span></div>
              <div className="card-body">
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, padding: '10px 14px', background: 'var(--bg-raised)', borderRadius: 8, borderLeft: '3px solid var(--brand-500)' }}>
                  APPROVE iff outstanding_calls ≤ available_agent_slots<br />
                  outstanding_calls = RESERVED + INITIATED + RINGING<br />
                  <br />
                  Current: {cc?.in_flight_pre_connect} in-flight ≤ {ac?.available} available → {cc?.in_flight_pre_connect <= ac?.available ? '✓ APPROVE' : '✗ REJECT'}
                </div>
                <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
                  This constraint cannot be relaxed by the predictive engine. The Safety Controller is a stateless,
                  independent boundary that always enforces hard capacity before calls are allocated.
                </div>
              </div>
            </div>

            {/* Provider health */}
            <div className="card mb-16">
              <div className="card-header"><span className="card-title">Provider Health Gate</span></div>
              <div className="card-body">
                <div className="grid-2">
                  {providers.map(p => (
                    <div key={p.name} style={{ background: 'var(--bg-raised)', borderRadius: 8, padding: 12 }}>
                      <div style={{ fontWeight: 600, marginBottom: 8 }}>{p.name}</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <div className="flex-between text-sm">
                          <span style={{ color: 'var(--text-muted)' }}>Circuit</span>
                          <StatusBadge value={p.circuit_state} />
                        </div>
                        <div className="flex-between text-sm">
                          <span style={{ color: 'var(--text-muted)' }}>Can Execute</span>
                          <span style={{ color: p.can_execute ? 'var(--green-400)' : 'var(--red-400)', fontWeight: 600 }}>
                            {p.can_execute ? 'Yes' : 'No'}
                          </span>
                        </div>
                        <div className="flex-between text-sm">
                          <span style={{ color: 'var(--text-muted)' }}>Outage</span>
                          <span style={{ color: p.is_outage ? 'var(--red-400)' : 'var(--text-muted)' }}>
                            {p.is_outage ? '⚠ Active' : 'None'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Agent drop simulation */}
            <div className="card">
              <div className="card-header"><span className="card-title">Failure Simulation — Sudden Agent Drop</span></div>
              <div className="card-body">
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
                  Instantly disconnect N available agents to test the Safety Controller's capacity enforcement
                  and observe how the system reacts to sudden agent availability drops.
                </p>
                <div className="flex-center gap-12">
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">Agents to Drop</label>
                    <input
                      type="number"
                      className="form-control"
                      style={{ width: 100 }}
                      min={1}
                      max={500}
                      value={dropCount}
                      onChange={e => setDropCount(parseInt(e.target.value) || 1)}
                      id="drop-count-input"
                    />
                  </div>
                  <button
                    className="btn btn-danger"
                    onClick={simulateDrop}
                    disabled={dropping}
                    id="simulate-agent-drop-btn"
                    style={{ marginTop: 18 }}
                  >
                    {dropping ? '⏳ Dropping…' : '⚡ Simulate Agent Drop'}
                  </button>
                </div>
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
