import React, { useState, useEffect } from 'react'
import styled from 'styled-components'
import { apiFetch } from '../api'

const DownloadBtn = styled.button`
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background-color: rgb(27, 27, 27);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition-duration: .3s;
  box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.11);
  flex-shrink: 0;

  .svgIcon {
    fill: rgb(214, 178, 255);
  }

  .icon2 {
    width: 14px;
    height: 4px;
    border-bottom: 2px solid rgb(182, 143, 255);
    border-left: 2px solid rgb(182, 143, 255);
    border-right: 2px solid rgb(182, 143, 255);
  }

  .tooltip {
    position: absolute;
    right: -90px;
    opacity: 0;
    background-color: rgb(12, 12, 12);
    color: white;
    padding: 4px 8px;
    border-radius: 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition-duration: .2s;
    pointer-events: none;
    letter-spacing: 0.5px;
    font-size: 11px;
    white-space: nowrap;
    z-index: 10;
  }

  .tooltip::before {
    position: absolute;
    content: "";
    width: 10px;
    height: 10px;
    background-color: rgb(12, 12, 12);
    transform: rotate(45deg);
    left: -5%;
  }

  &:hover .tooltip {
    opacity: 1;
    transition-duration: .3s;
  }

  &:hover {
    background-color: rgb(150, 94, 255);
    transition-duration: .3s;
  }

  &:hover .icon2 {
    border-bottom: 2px solid rgb(235, 235, 235);
    border-left: 2px solid rgb(235, 235, 235);
    border-right: 2px solid rgb(235, 235, 235);
  }

  &:hover .svgIcon {
    fill: rgb(255, 255, 255);
    animation: slide-in-top 0.6s cubic-bezier(0.250, 0.460, 0.450, 0.940) both;
  }

  @keyframes slide-in-top {
    0% { transform: translateY(-10px); opacity: 0; }
    100% { transform: translateY(0px); opacity: 1; }
  }
`

export default function Reports() {
  const [files, setFiles] = useState([])
  const [deleting, setDeleting] = useState(null)

  useEffect(() => {
    apiFetch('/api/reports')
      .then(r => r.json())
      .then(d => setFiles(d.files || []))
      .catch(() => setFiles([]))
  }, [])

  const handleDelete = async (name) => {
    if (!confirm(`"${name}" hisobotini o'chirishni xohlaysizmi?`)) return
    setDeleting(name)
    try {
      const res = await apiFetch(`/api/reports/${encodeURIComponent(name)}`, { method: 'DELETE' })
      if (res.ok) {
        setFiles(prev => prev.filter(f => f.name !== name))
      }
    } catch (_) {}
    setDeleting(null)
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, marginBottom: 20 }}>Hisobotlar</h2>
      {files.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Hisobotlar topilmadi</p>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {files.map(f => (
            <div key={f.name}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '8px 12px', background: 'var(--bg-card)', borderRadius: 'var(--radius)',
              }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: 'var(--primary)', fontSize: 14 }}>{f.name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>
                  {f.size} | {f.date}
                </div>
              </div>
              <button onClick={() => handleDelete(f.name)} disabled={deleting === f.name}
                style={{
                  background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: 6, color: '#ef4444', padding: '6px 10px', fontSize: 12, cursor: 'pointer',
                  flexShrink: 0, transition: 'all 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.2)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}>
                {deleting === f.name ? '...' : '✕ O\'chirish'}
              </button>
              <a href={f.path} download target="_blank" rel="noopener noreferrer"
                style={{ textDecoration: 'none', lineHeight: 0 }}>
                <DownloadBtn className="Btn">
                  <svg className="svgIcon" viewBox="0 0 384 512" height="1em" xmlns="http://www.w3.org/2000/svg">
                    <path d="M169.4 470.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 370.8 224 64c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 306.7L54.6 265.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z" />
                  </svg>
                  <span className="icon2" />
                  <span className="tooltip">Yuklab olish</span>
                </DownloadBtn>
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}