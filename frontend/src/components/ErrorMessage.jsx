export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-box" role="alert">
      <span>⚠</span>
      <span>{message || 'An error occurred.'}</span>
      {onRetry && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={onRetry} style={{ marginLeft: 'auto' }}>
          Retry
        </button>
      )}
    </div>
  )
}
