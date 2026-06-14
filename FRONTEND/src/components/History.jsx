import React, { useState, useEffect } from 'react'

export default function History() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetch('/api/history')
      .then(r => r.json())
      .then(d => setSessions(d.reports || []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Yuklanmoqda...</div>

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, marginBottom: 20 }}>Skaner tarixi</h2>
      {sessions.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Hali skaner natijalari yo'q</p>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {sessions.map(s => (
            <div key={s.id} onClick={() => setSelected(selected === s.id ? null : s.id)}
              style={{
                background: 'var(--bg-card)', borderRadius: 'var(--radius)', padding: 16,
                cursor: 'pointer', border: selected === s.id ? '1px solid var(--primary)' : '1px solid transparent',
              }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{s.target || 'Noma\'lum'}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                    {s.intent?.substring(0, 80)}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {s.timestamp ? new Date(s.timestamp).toLocaleString() : ''}
                  </div>
                  <div style={{ fontSize: 12, color: s.status === 'completed' ? 'var(--success)' : 'var(--warning)', marginTop: 2 }}>
                    {s.status}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
