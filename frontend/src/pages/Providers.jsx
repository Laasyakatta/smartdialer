import { useState, useEffect, useCallback } from 'react'
import { providersApi } from '../services/api'
import Header from '../components/Header'
import StatusBadge from '../components/StatusBadge'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

export default function Providers() {
  const [providers, setProviders] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [busy, setBusy]           = useState({})
  const [toast, setToast]         = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await providersApi.list()
      setProviders(res.data || [])
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

  const toggleOutage = async (name, isOutage) => {
    setBusy(b => ({ ...b, [name]: true }))
    try {
      await providersApi.toggleOutage(name, isOutage)
      showToast(`${name} ${isOutage ? 'OUTAGE triggered' : 'RESTORED'}`, isOutage ? 'error' : 'success')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed', 'error')
    } finally {
      setBusy(b => ({ ...b, [name]: false }))
    }
  }

  const resetCircuit = async (name) => {
    setBusy(b => ({ ...b, [name + '_cb']: true }))
    try {
      await providersApi.resetCircuit(name)
      showToast(`Circuit breaker for ${name} reset`, 'success')
      load()
    } catch (e) {
      showToast(e?.response?.data?.detail || 'Failed', 'error')
    } finally {
      setBusy(b => ({ ...b, [name + '_cb']: false }))
    }
  }

  const circuitColor = (state) => {
    if (state === 'CLOSED')    return 'var(--green-400)'
    if (state === 'HALF_OPEN') return 'var(--yellow-400)'
    return 'var(--red-400)'
  }

  return (
    <>
      <Header title="Provider Monitoring" subtitle="Real-time telecom provider health and circuit breaker states" onRefresh={load} />
      <div className="page-content">
        {error && <ErrorMessage message={error} onRetry={load} />}
        {loading ? <Loading /> : (
          <>
            <div className="grid-2 mb-16">
              {providers.map(prov => (
                <div key={prov.name} className="card">
                  <div className="card-header">
                    <div className="flex-center gap-8">
                      <span style={{ fontSize: 20 }}>📡</span>
                      <span className="card-title">{prov.name === 'mock_a' ? 'Provider A (Fast / Reliable)' : 'Provider B (Slower / Duplicates)'}</span>
                    </div>
                    <StatusBadge value={prov.is_outage ? 'FAILED' : prov.can_execute ? 'AVAILABLE' : 'OFFLINE'} />
                  </div>
                  <div className="card-body">
                    <div className="provider-meta">
                      <div className="provider-row">
                        <span>Circuit State</span>
                        <span style={{ fontWeight: 600, color: circuitColor(prov.circuit_state) }}>
                          {prov.circuit_state}
                        </span>
                      </div>
                      <div className="provider-row">
                        <span>Failure Count</span>
                        <span style={{ color: prov.failures > 0 ? 'var(--red-400)' : 'var(--text-secondary)' }}>
                          {prov.failures}
                        </span>
                      </div>
                      <div className="provider-row">
                        <span>Can Execute</span>
                        <span style={{ color: prov.can_execute ? 'var(--green-400)' : 'var(--red-400)' }}>
                          {prov.can_execute ? '✓ Yes' : '✗ No'}
                        </span>
                      </div>
                      <div className="provider-row">
                        <span>Outage Active</span>
                        <span style={{ color: prov.is_outage ? 'var(--red-400)' : 'var(--text-muted)' }}>
                          {prov.is_outage ? '⚠ YES' : 'No'}
                        </span>
                      </div>
                    </div>

                    <div className="flex gap-8 mt-12">
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={prov.is_outage || busy[prov.name]}
                        onClick={() => toggleOutage(prov.name, true)}
                        id={`outage-start-${prov.name}`}
                      >⚡ Inject Outage</button>

                      <button
                        className="btn btn-success btn-sm"
                        disabled={!prov.is_outage || busy[prov.name]}
                        onClick={() => toggleOutage(prov.name, false)}
                        id={`outage-restore-${prov.name}`}
                      >✓ Restore</button>

                      <button
                        className="btn btn-ghost btn-sm"
                        disabled={busy[prov.name + '_cb']}
                        onClick={() => resetCircuit(prov.name)}
                        id={`reset-circuit-${prov.name}`}
                      >↺ Reset CB</button>
                    </div>

                    {prov.name === 'mock_a' && (
                      <div style={{ marginTop: 10, padding: '8px 10px', background: 'var(--bg-raised)', borderRadius: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                        Characteristics: ~2% failure rate, fast responses, ordered events
                      </div>
                    )}
                    {prov.name === 'mock_b' && (
                      <div style={{ marginTop: 10, padding: '8px 10px', background: 'var(--bg-raised)', borderRadius: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                        Characteristics: ~15% failure rate, 10% duplicate events, 10% out-of-order events
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="card-header"><span className="card-title">Circuit Breaker Explanation</span></div>
              <div className="card-body">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                  {[
                    { state: 'CLOSED', desc: 'Normal operation. Calls flow freely. Failures increment counter.', color: 'var(--green-400)' },
                    { state: 'OPEN', desc: 'Circuit tripped after 5 failures. All calls blocked. Recovery timer running.', color: 'var(--red-400)' },
                    { state: 'HALF_OPEN', desc: 'Recovery probe. 3 consecutive successes required to close circuit.', color: 'var(--yellow-400)' },
                  ].map(s => (
                    <div key={s.state} style={{ background: 'var(--bg-raised)', borderRadius: 8, padding: 12, borderLeft: `3px solid ${s.color}` }}>
                      <div style={{ fontWeight: 600, color: s.color, marginBottom: 6 }}>{s.state}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.desc}</div>
                    </div>
                  ))}
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
