export default function StatCard({ label, value, sub, icon, color = 'brand', iconBg }) {
  const bgMap = {
    brand: 'rgba(99,102,241,0.15)',
    green: 'var(--green-bg)',
    red:   'var(--red-bg)',
    yellow:'var(--yellow-bg)',
    blue:  'var(--blue-bg)',
    purple:'var(--purple-bg)',
    orange:'var(--orange-bg)',
  }

  const fgMap = {
    brand: 'var(--brand-400)',
    green: 'var(--green-400)',
    red:   'var(--red-400)',
    yellow:'var(--yellow-400)',
    blue:  'var(--blue-400)',
    purple:'var(--purple-400)',
    orange:'var(--orange-400)',
  }

  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <span className="stat-label">{label}</span>
        {icon && (
          <div
            className="stat-icon"
            style={{ background: iconBg || bgMap[color] || bgMap.brand }}
          >
            <span style={{ color: fgMap[color] || fgMap.brand, fontSize: 15 }}>{icon}</span>
          </div>
        )}
      </div>
      <div className="stat-value">{value ?? '—'}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}
