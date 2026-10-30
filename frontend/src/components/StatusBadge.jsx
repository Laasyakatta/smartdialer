export default function StatusBadge({ value }) {
  if (!value) return <span className="badge badge-CLOSED">—</span>

  const label = String(value).toUpperCase()
  return (
    <span className={`badge badge-${label}`}>
      <span className="badge-dot" />
      {label.replace(/_/g, ' ')}
    </span>
  )
}
