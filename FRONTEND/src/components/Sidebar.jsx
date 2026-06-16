import React from 'react'
import styled from 'styled-components'
import ThemeToggle from './ThemeToggle'

const NavButton = styled.button`
  position: relative;
  width: 100%;
  height: 3.5em;
  outline: none;
  transition: 0.1s;
  background-color: transparent;
  border: none;
  font-size: 13px;
  font-weight: bold;
  color: #ddebf0;
  cursor: pointer;
  margin-bottom: 8px;

  #clip {
    --color: ${props => props.active ? '#27c39f' : '#2761c3'};
    position: absolute;
    top: 0;
    left: 0;
    overflow: hidden;
    width: 100%;
    height: 100%;
    border: ${props => props.active ? '2px' : '1px'} solid var(--color);
    box-shadow: inset 0px 0px ${props => props.active ? '20px' : '10px'} 
      ${props => props.active ? '#1a8a6e' : '#195480'};
    -webkit-clip-path: polygon(
      8px 0%, calc(100% - 8px) 0%, 
      100% 8px, 100% calc(100% - 8px), 
      calc(100% - 8px) 100%, 8px 100%, 
      0% calc(100% - 8px), 0% 8px
    );
    display: flex;
    align-items: center;
    padding-left: 16px;
    gap: 10px;
  }

  .corner {
    position: absolute;
    width: 1.2em;
    height: 1.2em;
    background-color: ${props => props.active ? '#27c39f' : '#2761c3'};
    transform: scale(1) rotate(45deg);
    transition: 0.2s;
  }

  #rightTop { top: -0.55em; right: -0.55em; }
  #leftTop { top: -0.55em; left: -0.55em; }
  #leftBottom { bottom: -0.55em; left: -0.55em; }
  #rightBottom { bottom: -0.55em; right: -0.55em; }

  &:hover #clip {
    --color: #27c39f;
    animation: 0.2s ease-in-out 0.3s both greenLight;
  }

  &:hover .corner {
    background-color: #27c39f;
    transform: scale(1.3) rotate(45deg);
    animation: 0.15s ease-in-out both changeColor,
               0.2s linear 0.3s both lightEffect;
  }

  @keyframes changeColor {
    from { background-color: #2761c3; }
    to { background-color: #27c39f; }
  }
  @keyframes lightEffect {
    from { box-shadow: 1px 1px 5px #27c39f; }
    to { box-shadow: 0 0 2px #27c39f; }
  }
  @keyframes greenLight {
    to { box-shadow: inset 0px 0px 25px #27c39f; }
  }
`

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
        <nav style={{ flex: 1, padding: '0 12px' }}>
          {pages.map(p => (
            <NavButton key={p.id} active={page === p.id} onClick={() => onNavigate(p.id)}>
              <div id="clip">
                <div id="leftTop" className="corner" />
                <div id="rightBottom" className="corner" />
                <div id="rightTop" className="corner" />
                <div id="leftBottom" className="corner" />
                <span>{p.icon}</span>
                {p.label}
              </div>
            </NavButton>
          ))}
        </nav>
        <div style={{ padding: '0 12px', display: 'flex', flexDirection: 'column', gap: 8, marginTop: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <ThemeToggle />
          </div>
          <button onClick={() => {
            localStorage.removeItem('nexura_auth');
            window.location.reload();
          }} style={{
            background: 'transparent',
            border: '1px solid #e74c3c',
            color: '#e74c3c',
            fontFamily: 'monospace',
            fontSize: '11px',
            letterSpacing: '2px',
            padding: '8px 12px',
            cursor: 'pointer',
            width: '100%',
          }}>
            ⏻ CHIQISH
          </button>
        </div>
      </aside>
    </>
  )
}
