import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard       from './pages/Dashboard'
import Agents          from './pages/Agents'
import Borrowers       from './pages/Borrowers'
import Campaigns       from './pages/Campaigns'
import Calls           from './pages/Calls'
import Analytics       from './pages/Analytics'
import Providers       from './pages/Providers'
import SafetyController from './pages/SafetyController'
import Simulation      from './pages/Simulation'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <div className="main-area">
          <Routes>
            <Route path="/"           element={<Dashboard />}        />
            <Route path="/agents"     element={<Agents />}           />
            <Route path="/borrowers"  element={<Borrowers />}        />
            <Route path="/campaigns"  element={<Campaigns />}        />
            <Route path="/calls"      element={<Calls />}            />
            <Route path="/analytics"  element={<Analytics />}        />
            <Route path="/providers"  element={<Providers />}        />
            <Route path="/safety"     element={<SafetyController />} />
            <Route path="/simulation" element={<Simulation />}       />
            <Route path="*"           element={
              <div className="page-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div className="empty-state">
                  <div className="empty-state-icon">🔍</div>
                  <div>Page not found</div>
                </div>
              </div>
            } />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
