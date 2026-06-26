import React, { useState, useEffect } from 'react'
import { apiFetch } from '../api'

export default function GitHub() {
  const [tab, setTab] = useState('export')
  const [sessions, setSessions] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [token, setToken] = useState(() => localStorage.getItem('nexura_github_token') || '')
  const [repoName, setRepoName] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    apiFetch('/api/history').then(r => r.json()).then(d => {
      setSessions(d.reports || [])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    localStorage.setItem('nexura_github_token', token)
  }, [token])

  const handleExport = async () => {
    if (!token || !repoName) return
    if (!selectedId) return
    setLoading(true)
    setResult(null)
    try {
      const res = await apiFetch('/api/github/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, repo_name: repoName, session_id: selectedId }),
      })
      const data = await res.json()
      setResult({ type: data.success ? 'success' : 'error', message: data.error || data.message || data.repo_url || 'OK', url: data.repo_url })
    } catch (err) {
      setResult({ type: 'error', message: err.message })
    }
    setLoading(false)
  }

  const handleScan = async () => {
    if (!token || !repoUrl) return
    setLoading(true)
    setResult(null)
    try {
      const res = await apiFetch('/api/github/scan-repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, repo_url: repoUrl }),
      })
      const data = await res.json()
      setResult({ type: data.success ? 'success' : 'error', data })
    } catch (err) {
      setResult({ type: 'error', message: err.message })
    }
    setLoading(false)
  }

  const activeStyle = (isActive) => ({
    padding: '10px 24px', border: 'none', borderRadius: 8, cursor: 'pointer',
    fontWeight: 700, fontSize: 13,
    background: isActive ? 'var(--primary)' : 'var(--bg-input)',
    color: isActive ? '#fff' : 'var(--text)',
    transition: 'all 0.15s',
  })

  const cardStyle = {
    background: 'var(--bg-card)', borderRadius: 'var(--radius)',
    border: '1px solid var(--border)', padding: 20, marginTop: 16,
  }

  const inputStyle = {
    width: '100%', padding: '10px 14px', background: 'var(--bg)',
    border: '1px solid var(--border)', borderRadius: 6,
    color: 'var(--text)', fontSize: 13, outline: 'none', marginBottom: 12,
    boxSizing: 'border-box',
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <span style={{ fontSize: 28 }}>🐙</span>
        <h2 style={{ fontSize: 24, margin: 0 }}>GitHub Integratsiyasi</h2>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <button style={activeStyle(tab === 'export')} onClick={() => { setTab('export'); setResult(null) }}>Zaifliklarni yuklash</button>
        <button style={activeStyle(tab === 'scan')} onClick={() => { setTab('scan'); setResult(null) }}>Repo ni skanerlash</button>
      </div>

      <div style={{ ...cardStyle, borderTop: `3px solid var(--primary)` }}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>GitHub Token (classic personal access token)</label>
          <input type="password" value={token} onChange={e => setToken(e.target.value)} placeholder="ghp_..." style={inputStyle} />
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Token da <strong>repo</strong> va <strong>public_repo</strong> skoplari yoqilgan bo'lishi kerak</div>
        </div>

        {tab === 'export' ? (
          <>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Skaner natijasini tanlang</label>
              <select value={selectedId} onChange={e => setSelectedId(e.target.value)} style={inputStyle}>
                <option value="">-- Natijani tanlang --</option>
                {sessions.map(s => (
                  <option key={s.id} value={s.id}>{s.target || s.id} — {s.date || ''}</option>
                ))}
              </select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Yangi repo nomi</label>
              <input value={repoName} onChange={e => setRepoName(e.target.value)} placeholder="masalan: security-report" style={inputStyle} />
            </div>
            <button onClick={handleExport} disabled={loading || !token || !repoName || !selectedId} style={{
              padding: '12px 24px', background: loading ? 'var(--text-muted)' : '#27c39f',
              color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer', width: '100%',
            }}>
              {loading ? 'Yuklanmoqda...' : "🐙 GitHub'ga yuklash"}
            </button>
          </>
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>GitHub repo manzili</label>
              <input value={repoUrl} onChange={e => setRepoUrl(e.target.value)} placeholder="https://github.com/user/repo yoki user/repo" style={inputStyle} />
            </div>
            <button onClick={handleScan} disabled={loading || !token || !repoUrl} style={{
              padding: '12px 24px', background: loading ? 'var(--text-muted)' : '#27c39f',
              color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer', width: '100%',
            }}>
              {loading ? 'Skanerlanmoqda...' : "🔍 Repo ni tekshirish"}
            </button>
          </>
        )}
      </div>

      {result && (
        <div style={{ ...cardStyle, borderLeft: `4px solid ${result.type === 'success' ? '#27c39f' : '#ef4444'}` }}>
          {result.type === 'error' && (
            <div style={{ color: '#ef4444', fontSize: 14 }}>
              <strong>Xatolik:</strong> {result.message}
            </div>
          )}
          {result.type === 'success' && result.url && (
            <div>
              <div style={{ color: '#27c39f', fontSize: 14, marginBottom: 8 }}>✅ Hisobot muvaffaqiyatli yuklandi</div>
              <a href={result.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', fontSize: 14 }}>{result.url} &rarr;</a>
            </div>
          )}
          {result.data && result.data.success && (
            <div>
              <div style={{ color: '#27c39f', fontSize: 14, marginBottom: 12 }}>✅ Skanerlash yakunlandi</div>
              {result.data.summary && (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                  {[
                    { label: 'Fayllar', value: result.data.summary.total_files },
                    { label: 'Tekshirilgan', value: result.data.summary.scanned_files },
                    { label: 'Maxfiy kalitlar', value: result.data.summary.secrets_found, color: result.data.summary.secrets_found > 0 ? '#ef4444' : '#27c39f' },
                    { label: 'Signal', value: result.data.summary.alerts, color: result.data.summary.alerts > 0 ? '#f59e0b' : '#27c39f' },
                    { label: '⭐', value: result.data.summary.stars },
                    { label: 'Til', value: result.data.summary.language },
                  ].map((item, i) => (
                    <div key={i} style={{
                      background: 'var(--bg-input)', padding: '10px 16px', borderRadius: 6,
                      textAlign: 'center', minWidth: 80,
                    }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>{item.label}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: item.color || 'var(--text)' }}>{item.value}</div>
                    </div>
                  ))}
                </div>
              )}
              {result.data.issues && result.data.issues.map((issue, i) => {
                const sevColor = { info: '#6b7280', good: '#27c39f', warning: '#f59e0b', medium: '#f59e0b', low: '#3b82f6', high: '#ef4444', critical: '#dc2626' }
                const color = sevColor[issue.severity] || '#6b7280'
                return (
                  <div key={i} style={{
                    padding: '10px 14px', marginBottom: 6, borderRadius: 6,
                    background: 'var(--bg-input)', borderLeft: `3px solid ${color}`,
                    fontSize: 13,
                  }}>
                    <div style={{ fontWeight: 600, marginBottom: 2, color: 'var(--text)' }}>{issue.title}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{issue.detail}</div>
                  </div>
                )
              })}
              {result.data.alerts && result.data.alerts.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: '#ef4444' }}>⚠️ Xavfli topilmalar</div>
                  {result.data.alerts.map((a, i) => (
                    <div key={i} style={{
                      padding: '10px 14px', marginBottom: 6, borderRadius: 6,
                      background: 'rgba(239,68,68,0.08)', borderLeft: '3px solid #ef4444',
                      fontSize: 13,
                    }}>
                      <div style={{ fontWeight: 600, marginBottom: 2, color: '#ef4444' }}>[{a.severity.toUpperCase()}] {a.title}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{a.detail}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {result.data && !result.data.success && (
            <div style={{ color: '#ef4444', fontSize: 14 }}>
              <strong>Xatolik:</strong> {result.data.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
