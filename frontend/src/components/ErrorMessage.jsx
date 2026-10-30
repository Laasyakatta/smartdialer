export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-box">
      <span>⚠</span>
      <span>{message || 'An error occurred.'}</span>
      {onRetry && (
        <button className="btn btn-ghost btn-sm" onClick={onRetry} style={{ marginLeft: 'auto' }}>
          Retry
        </button>
      )}
    </div>
  )
}
