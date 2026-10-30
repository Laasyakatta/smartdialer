export default function Loading({ text = 'Loading…' }) {
  return (
    <div className="loading-overlay">
      <div className="spinner" />
      <span className="loading-text">{text}</span>
    </div>
  )
}
