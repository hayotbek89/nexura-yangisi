import React, { useState } from 'react'
import { ScannerProvider } from './ScannerContext'
import ErrorBoundary from './components/ErrorBoundary'
import Sidebar from './components/Sidebar'
import Scanner from './components/Scanner'
import History from './components/History'
import Reports from './components/Reports'
import Settings from './components/Settings'
import AccessKeyGate from './components/AccessKeyGate'
import './App.css'

export default function App() {
  const [page, setPage] = useState('scanner')
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    localStorage.removeItem('nexura_auth');
    window.location.reload();
  }

  return (
    <AccessKeyGate>
      <ScannerProvider>
        <ErrorBoundary>
          <Sidebar page={page} onNavigate={(p) => { setPage(p); setMenuOpen(false) }} menuOpen={menuOpen} onToggle={() => setMenuOpen(!menuOpen)} />
          <div style={{
            flex: 1, padding: '24px', overflow: 'auto',
            marginLeft: window.innerWidth < 768 ? 0 : undefined,
          }}>
            <div style={{ display: window.innerWidth < 768 ? 'block' : 'none', marginBottom: 16 }}>
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
            {page === 'settings' && <Settings />}
          </div>
        </ErrorBoundary>
      </ScannerProvider>
    </AccessKeyGate>
  )
}
