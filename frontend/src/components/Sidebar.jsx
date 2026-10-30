import { NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { healthApi } from '../services/api'

const NAV = [
  {
    section: 'Overview',
    links: [
      { to: '/',            label: 'Dashboard',   icon: '◈' },
      { to: '/analytics',   label: 'Analytics',   icon: '⬟' },
    ]
  },
  {
    section: 'Operations',
    links: [
      { to: '/agents',      label: 'Agents',      icon: '👤' },
      { to: '/borrowers',   label: 'Borrowers',   icon: '🏠' },
      { to: '/campaigns',   label: 'Campaigns',   icon: '📋' },
      { to: '/calls',       label: 'Calls',       icon: '📞' },
    ]
  },
  {
    section: 'System',
    links: [
      { to: '/providers',   label: 'Providers',   icon: '📡' },
      { to: '/safety',      label: 'Safety',      icon: '🛡' },
      { to: '/simulation',  label: 'Simulation',  icon: '⚡' },
    ]
  }
]

export default function Sidebar() {
  const [online, setOnline] = useState(null)

  useEffect(() => {
    const check = async () => {
      try {
        await healthApi.check()
        setOnline(true)
      } catch {
        setOnline(false)
      }
    }
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [])

  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <NavLink to="/" className="sidebar-logo">
          <div className="sidebar-logo-icon">📞</div>
          <div>
            <div className="sidebar-logo-text">SmartDialer</div>
            <div className="sidebar-logo-sub">Collections Engine</div>
          </div>
        </NavLink>
      </div>

      <div className="sidebar-nav">
        {NAV.map(group => (
          <div key={group.section}>
            <div className="sidebar-section-label">{group.section}</div>
            {group.links.map(link => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={({ isActive }) =>
                  'sidebar-link' + (isActive ? ' active' : '')
                }
              >
                <span style={{ fontSize: 16, lineHeight: 1 }}>{link.icon}</span>
                <span>{link.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="backend-status">
          <div className={`status-dot ${online === false ? 'offline' : ''}`} />
          {online === null ? 'Connecting…' : online ? 'Backend online' : 'Backend offline'}
        </div>
      </div>
    </nav>
  )
}
