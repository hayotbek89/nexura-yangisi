import React, { useState, useEffect } from 'react'
import { apiFetch, getApiKey } from '../api'

export default function Settings() {
  const [status, setStatus] = useState(null)
  const [host, setHost] = useState('')
  const [apiKey, setApiKey] = useState(getApiKey())
  const [keyMessage, setKeyMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/status').then(r => r.json()).catch(() => null),
      fetch('/api/host').then(r => r.json()).catch(() => null),
    ]).then(([s, h]) => {
      if (s) setStatus(s)
      if (h) setHost(h.host)
    }).catch(() => setError('Serverga ulanishda xatolik'))
      .finally(() => setLoading(false))
  }, [])

  const saveApiKey = async (e) => {
    e.preventDefault()
    const trimmed = apiKey.trim()
    if (trimmed) {
      localStorage.setItem('nexura_api_key', trimmed)
    } else {
      localStorage.removeItem('nexura_api_key')
    }

    try {
      const res = await apiFetch('/api/stats')
      setKeyMessage(res.ok ? 'API key saqlandi va tekshirildi.' : 'API key saqlandi, lekin server rad etdi.')
    } catch {
      setKeyMessage('API key saqlandi. Server bilan tekshirib bo‘lmadi.')
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
        Yuklanmoqda...
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: 'var(--danger)' }}>
        {error}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, marginBottom: 24 }}>Sozlamalar</h2>

      {host && (
        <div style={{
          background: 'var(--bg-card)', borderRadius: 'var(--radius)',
          padding: 16, marginBottom: 24,
          border: '1px solid var(--border)',
        }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Server manzili</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--primary)', wordBreak: 'break-all' }}>
            {host}
          </div>
        </div>
      )}

      <form onSubmit={saveApiKey} style={{
        background: 'var(--bg-card)', borderRadius: 'var(--radius)',
        padding: 16, marginBottom: 24,
        border: '1px solid var(--border)',
      }}>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Backend API key</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="NEXURA_API_KEY"
            style={{
              flex: 1, minWidth: 240, padding: '10px 12px',
              borderRadius: 'var(--radius)', border: '1px solid var(--border)',
              background: 'var(--bg-input)', color: 'var(--text)',
            }}
          />
          <button type="submit" style={{
            padding: '10px 14px', borderRadius: 'var(--radius)',
            border: '1px solid var(--primary)', background: 'var(--primary)',
            color: '#fff', cursor: 'pointer',
          }}>
            Saqlash
          </button>
        </div>
        {keyMessage && (
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{keyMessage}</div>
        )}
      </form>

      <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', padding: 24, marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Tizim holati</h3>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '8px 0', borderBottom: '1px solid var(--border)',
          }}>
            <span>AI Model</span>
            <span style={{ color: status?.ai_ready ? 'var(--success)' : 'var(--text-muted)' }}>
              {status?.ai_ready ? 'Tayyor' : 'Yoqilmagan'}
            </span>
          </div>
          {status?.tools && Object.entries(status.tools).map(([name, info]) => (
            <div key={name} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '8px 0', borderBottom: '1px solid var(--border)',
            }}>
              <span>{name}</span>
              <span style={{ color: (typeof info === 'boolean' ? info : info.available) ? 'var(--success)' : 'var(--danger)' }}>
                {(typeof info === 'boolean' ? info : info.available) ? "O'rnatilgan" : "Yo'q"}
              </span>
            </div>
          ))}
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            padding: '8px 0',
          }}>
            <span>Versiya</span>
            <span style={{ color: 'var(--text-muted)' }}>{status?.version}</span>
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', padding: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Ishlatish</h3>
        <div style={{ fontSize: 14, lineHeight: 2, color: 'var(--text-muted)' }}>
          <p>1. Target URL yoki IP manzilni kiriting</p>
          <p>2. Tabiiy tilda skaner buyrug'ini yozing</p>
          <p>3. "Skanerlashni boshlash" tugmasini bosing</p>
          <p>4. Agentic rejimda AI mustaqil vosita tanlaydi</p>
        </div>
      </div>
    </div>
  )
}
