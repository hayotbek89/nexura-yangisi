import React, { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export default function History() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [deleting, setDeleting] = useState(null)

  useEffect(() => {
    apiFetch('/api/history')
      .then(r => r.json())
      .then(d => setSessions(d.reports || []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [])

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (!confirm("Bu skaner yozuvini o'chirishni xohlaysizmi?")) return
    setDeleting(id)
    try {
      const res = await apiFetch(`/api/history/${id}`, { method: 'DELETE' })
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== id))
        if (selected === id) setSelected(null)
      }
    } catch (_) {}
    setDeleting(null)
  }

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
                display: 'flex', alignItems: 'center',
              }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{s.target || 'Noma\'lum'}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                      {s.intent?.substring(0, 80)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {s.date ? new Date(s.date).toLocaleString() : ''}
                    </div>
                    <div style={{ fontSize: 12, color: s.status === 'completed' ? 'var(--success)' : 'var(--warning)', marginTop: 2 }}>
                      {s.status}
                    </div>
                  </div>
                </div>
              </div>
              <button onClick={e => handleDelete(e, s.id)} disabled={deleting === s.id}
                style={{
                  marginLeft: 12, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: 6, color: '#ef4444', padding: '6px 10px', fontSize: 12, cursor: 'pointer',
                  flexShrink: 0, transition: 'all 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.2)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}>
                {deleting === s.id ? '...' : '✕ O\'chirish'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}