import React, { useState, useEffect } from 'react'
import { ScannerProvider } from './ScannerContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { useWindowSize } from './hooks/useWindowSize'
import ErrorBoundary from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'
import Scanner from './components/Scanner'
import History from './components/History'
import Reports from './components/Reports'
import Settings from './components/Settings'
import GitHub from './components/GitHub'
import BackgroundPattern from './components/BackgroundPattern'
import AccessKeyGate from './components/AccessKeyGate'
import TermsOfServiceModal from './components/TermsOfServiceModal'
import './App.css'

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => !!localStorage.getItem('nexura_auth'))
  const [tosAccepted, setTosAccepted] = useState(false)
  const [tosChecked, setTosChecked] = useState(false)
  const [page, setPage] = useState('scanner')
  const [menuOpen, setMenuOpen] = useState(false)
  const winWidth = useWindowSize()
  const isMobile = winWidth < 768

  useEffect(() => {
    if (authenticated && !tosChecked) {
      fetch('/api/tos/status')
        .then(r => r.json())
        .then(d => { setTosAccepted(d.accepted); setTosChecked(true) })
        .catch(() => { setTosAccepted(false); setTosChecked(true) })
    }
  }, [authenticated, tosChecked])

  const handleAccess = () => {
    localStorage.setItem('nexura_auth', 'true')
    setAuthenticated(true)
    setTosChecked(false)
  }

  const handleTosAccept = () => {
    setTosAccepted(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('nexura_auth')
    localStorage.removeItem('nexura_api_key')
    setAuthenticated(false)
  }

  if (!authenticated) {
    return (
      <ThemeProvider>
        <AccessKeyGate onAccess={handleAccess} />
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider>
      {authenticated && tosChecked && !tosAccepted && (
        <TermsOfServiceModal onAccept={handleTosAccept} />
      )}
      <BackgroundPattern />
      <ScannerProvider>
        <ErrorBoundary>
          <Sidebar page={page} onNavigate={(p) => { setPage(p); setMenuOpen(false) }} menuOpen={menuOpen} onToggle={() => setMenuOpen(!menuOpen)} onLogout={handleLogout} />
          <div style={{
            flex: 1, padding: '24px', overflow: 'auto',
            marginLeft: isMobile ? 0 : undefined,
          }}>
            <div style={{ display: isMobile ? 'block' : 'none', marginBottom: 16 }}>
              <button onClick={() => setMenuOpen(!menuOpen)}
                style={{
                  padding: '8px 16px', borderRadius: 'var(--radius)', border: '1px solid var(--border)',
                  background: 'var(--bg-card)', color: 'var(--text)', cursor: 'pointer', fontSize: 18,
                }}>
                {menuOpen ? '✕ Menyu' : '☰ Menyu'}
              </button>
            </div>
            {page === 'scanner' && <Scanner />}
            {page === 'history' && <History />}
            {page === 'reports' && <Reports />}
            {page === 'github' && <GitHub />}
            {page === 'settings' && <Settings />}
          </div>
        </ErrorBoundary>
      </ScannerProvider>
    </ThemeProvider>
  )
}
