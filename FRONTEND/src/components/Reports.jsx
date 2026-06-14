import React, { useState, useEffect } from 'react'

export default function Reports() {
  const [files, setFiles] = useState([])

  useEffect(() => {
    fetch('/api/reports')
      .then(r => r.json())
      .then(d => setFiles(d.files || []))
      .catch(() => setFiles([]))
  }, [])

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, marginBottom: 20 }}>Hisobotlar</h2>
      {files.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Hisobotlar topilmadi</p>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {files.map(f => (
            <a key={f.name} href={f.path} target="_blank" rel="noopener noreferrer"
              style={{
                display: 'block', padding: 12, background: 'var(--bg-card)', borderRadius: 'var(--radius)',
                textDecoration: 'none', color: 'var(--text)', fontSize: 14,
              }}>
              <span style={{ color: 'var(--primary)' }}>{f.name}</span>
              <span style={{ color: 'var(--text-muted)', marginLeft: 12, fontSize: 12 }}>
                {f.size} | {f.date}
              </span>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
