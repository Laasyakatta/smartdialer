export default function Header({ title, subtitle, actions, onRefresh }) {
  return (
    <header className="header">
      <div>
        <div className="header-title">{title}</div>
        {subtitle && <div className="header-sub">{subtitle}</div>}
      </div>
      <div className="header-right">
        {actions}
        {onRefresh && (
          <button className="refresh-btn" onClick={onRefresh} id="header-refresh-btn">
            <span>↻</span>
            Refresh
          </button>
        )}
      </div>
    </header>
  )
}
