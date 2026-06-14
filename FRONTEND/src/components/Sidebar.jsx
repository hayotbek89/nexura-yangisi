import React from 'react'

const pages = [
  { id: 'scanner', label: 'Scanner', icon: '⚡' },
  { id: 'history', label: 'Tarix', icon: '📋' },
  { id: 'reports', label: 'Hisobotlar', icon: '📊' },
  { id: 'settings', label: 'Sozlamalar', icon: '⚙️' },
]

export default function Sidebar({ page, onNavigate, menuOpen, onToggle }) {
  const isMobile = window.innerWidth < 768

  const sidebarStyle = {
    width: 220,
    background: 'var(--bg-card)',
    padding: '24px 0',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.2s',
  }

  const mobileStyle = isMobile ? {
    position: 'fixed',
    top: 0,
    left: 0,
    bottom: 0,
    zIndex: 1000,
    transform: menuOpen ? 'translateX(0)' : 'translateX(-100%)',
    boxShadow: menuOpen ? '0 0 20px rgba(0,0,0,0.5)' : 'none',
  } : {}

  return (
    <>
      {isMobile && menuOpen && (
        <div onClick={onToggle}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 999 }} />
      )}
      <aside style={{ ...sidebarStyle, ...mobileStyle }}>
        <div style={{ padding: '0 20px', marginBottom: 32 }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--primary)' }}>NEXURA</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>v2.0.0</div>
        </div>
        <nav style={{ flex: 1 }}>
          {pages.map(p => (
            <button key={p.id} onClick={() => onNavigate(p.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, width: '100%', padding: '12px 20px',
                border: 'none', background: page === p.id ? 'var(--primary)' : 'transparent',
                color: page === p.id ? '#fff' : 'var(--text-muted)', cursor: 'pointer',
                fontSize: 14, textAlign: 'left',
              }}>
              <span>{p.icon}</span>
              {p.label}
            </button>
          ))}
        </nav>
      </aside>
    </>
  )
}
