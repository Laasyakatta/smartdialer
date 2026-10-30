import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Loading from './components/Loading'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Agents = lazy(() => import('./pages/Agents'))
const Borrowers = lazy(() => import('./pages/Borrowers'))
const Campaigns = lazy(() => import('./pages/Campaigns'))
const Calls = lazy(() => import('./pages/Calls'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Providers = lazy(() => import('./pages/Providers'))
const SafetyController = lazy(() => import('./pages/SafetyController'))
const Simulation = lazy(() => import('./pages/Simulation'))

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <div className="main-area">
          <Suspense fallback={<div className="page-content"><Loading /></div>}>
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
          </Suspense>
        </div>
      </div>
    </BrowserRouter>
  )
}
