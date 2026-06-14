import React, { useState } from 'react'
import { useScanner } from '../ScannerContext'

function Spinner() {
  return (
    <span style={{
      display: 'inline-block', width: 16, height: 16,
      border: '2px solid var(--bg-input)', borderTop: '2px solid var(--primary)',
      borderRadius: '50%', animation: 'spin 0.8s linear infinite',
    }}>
      <style>{'@keyframes spin { to { transform: rotate(360deg) } }'}</style>
    </span>
  )
}

function ScanError({ message, onRetry }) {
  return (
    <div style={{
      background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
      borderRadius: 'var(--radius)', padding: 16, marginBottom: 16,
    }}>
      <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: 4 }}>Xatolik</div>
      <div style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12 }}>{message}</div>
      {onRetry && (
        <button onClick={onRetry}
          style={{
            padding: '8px 20px', borderRadius: 'var(--radius)', border: 'none',
            background: 'var(--danger)', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>
          Qayta urinish
        </button>
      )}
    </div>
  )
}

export default function Scanner() {
  const { url, setUrl, scanning, setScanning, results, findings, reportUrl, setReportUrl, setScanId, setFindings, agentic, setAgentic } = useScanner()
  const [prompt, setPrompt] = useState('')
  const [mode, setMode] = useState('prompt')
  const [error, setError] = useState(null)

  const startScan = async () => {
    if (!url.trim()) return
    setScanning(true)
    setError(null)
    setReportUrl(null)
    setScanId(null)

    try {
      const body = mode === 'quick'
        ? { target: url.trim() }
        : { prompt: prompt || `${url.trim()} ni zaifliklarga tekshir`, target: url.trim(), agentic }

      const endpoint = mode === 'quick' ? '/api/quick-scan' : '/api/chat'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || errData.detail || `Server xatosi (${res.status})`)
      }

      const data = await res.json()

      if (data.report_html) setReportUrl(data.report_html)
      if (data.id) setScanId(data.id)

      if (data.results) {
        let crit = 0, high = 0, med = 0, low = 0
        data.results.forEach(r => {
          r.vulnerabilities?.forEach(v => {
            if (v.severity === 'critical') crit++
            else if (v.severity === 'high') high++
            else if (v.severity === 'medium') med++
            else low++
          })
        })
        setFindings({ critical: crit, high, medium: med, low })
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, marginBottom: 4 }}>
          NEXURA <span style={{ color: 'var(--primary)' }}>Scanner</span>
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>
          AI yordamida veb-sayt va tarmoq zaifliklarini aniqlang
        </p>
      </div>

      {error && <ScanError message={error} onRetry={() => setError(null)} />}

      <div style={{
        background: 'var(--bg-card)', borderRadius: 'var(--radius)',
        padding: '24px', marginBottom: 24,
      }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {['prompt', 'quick'].map(m => (
            <button key={m} onClick={() => setMode(m)}
              style={{
                flex: 1, padding: '10px 16px', borderRadius: 'var(--radius)', border: 'none',
                cursor: 'pointer', fontSize: 14, fontWeight: 600,
                background: mode === m ? 'var(--primary)' : 'var(--bg-input)',
                color: '#fff', transition: 'background 0.15s',
              }}>{m === 'prompt' ? 'AI Scanner' : 'Quick Scan'}</button>
          ))}
        </div>

        <input value={url} onChange={e => setUrl(e.target.value)}
          placeholder="Target URL yoki IP (masalan: example.com)"
          onKeyDown={e => e.key === 'Enter' && !scanning && startScan()}
          style={{
            width: '100%', padding: '12px 16px', borderRadius: 'var(--radius)',
            border: '1px solid var(--border)', background: 'var(--bg-input)',
            color: 'var(--text)', fontSize: 15, marginBottom: 12,
          }} />

        {mode === 'prompt' && (
          <>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
              placeholder="Tabiiy tilda buyruq (masalan: 80-portni tekshir, SQL injection bormi?)"
              rows={3}
              style={{
                width: '100%', padding: '12px 16px', borderRadius: 'var(--radius)',
                border: '1px solid var(--border)', background: 'var(--bg-input)',
                color: 'var(--text)', fontSize: 14, resize: 'vertical', marginBottom: 12,
              }} />
            <label style={{
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 14,
              color: 'var(--text-muted)', cursor: 'pointer', marginBottom: 12,
            }}>
              <input type="checkbox" checked={agentic} onChange={e => setAgentic(e.target.checked)} />
              Agentic rejim (AI mustaqil vosita tanlaydi)
            </label>
          </>
        )}

        <button onClick={startScan} disabled={scanning || !url.trim()}
          style={{
            width: '100%', padding: '14px', borderRadius: 'var(--radius)', border: 'none',
            cursor: scanning || !url.trim() ? 'not-allowed' : 'pointer',
            fontSize: 16, fontWeight: 700,
            background: scanning ? 'var(--bg-input)' : 'var(--primary)',
            color: '#fff', opacity: scanning || !url.trim() ? 0.6 : 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          }}>
          {scanning ? <><Spinner /> Skanerlash...</> : 'Skanerlashni boshlash'}
        </button>
      </div>

      {findings.critical > 0 || findings.high > 0 || findings.medium > 0 ? (
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          {Object.entries(findings).map(([sev, count]) => count > 0 && (
            <div key={sev} style={{
              flex: 1, padding: 16, borderRadius: 'var(--radius)',
              background: sev === 'critical' ? 'rgba(124,58,237,0.15)' :
                sev === 'high' ? 'rgba(239,68,68,0.15)' :
                sev === 'medium' ? 'rgba(245,158,11,0.15)' :
                'rgba(34,197,94,0.15)',
              textAlign: 'center', minWidth: 100,
            }}>
              <div style={{
                fontSize: 28, fontWeight: 700,
                color: sev === 'critical' ? 'var(--critical)' :
                  sev === 'high' ? 'var(--danger)' :
                  sev === 'medium' ? 'var(--warning)' : 'var(--success)',
              }}>{count}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: 4 }}>
                {sev === 'critical' ? 'Critical' : sev === 'high' ? 'High' : sev === 'medium' ? 'Medium' : 'Low'}
              </div>
            </div>
          ))}
        </div>
      ) : findings.low > 0 && (
        <div style={{ textAlign: 'center', padding: 16, color: 'var(--success)', fontSize: 14 }}>
          Past xavf — {findings.low} ta kuzatuv
        </div>
      )}

      {results.length > 0 && (
        <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', padding: 24 }}>
          <h3 style={{ marginBottom: 16, fontSize: 18 }}>Natijalar</h3>
          {results.map((r, i) => (
            <div key={i} style={{
              marginBottom: 12, padding: 12,
              background: 'var(--bg-input)', borderRadius: 'var(--radius)',
            }}>
              <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--primary)' }}>
                {r.tool?.toUpperCase()}
                <span style={{
                  fontSize: 12, color: r.success ? 'var(--success)' : 'var(--danger)',
                  marginLeft: 8, fontWeight: 400,
                }}>{r.success ? 'bajarildi' : 'xatolik'}</span>
              </div>
              {r.vulnerabilities?.map((v, j) => (
                <div key={j} style={{
                  padding: '6px 0', fontSize: 14,
                  display: 'flex', gap: 8, alignItems: 'start',
                  borderBottom: '1px solid var(--border)',
                }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 4, fontSize: 11,
                    fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0,
                    background: v.severity === 'critical' ? 'var(--critical)' :
                      v.severity === 'high' ? 'var(--danger)' :
                      v.severity === 'medium' ? 'var(--warning)' : 'var(--success)',
                    color: '#fff',
                  }}>{v.severity}</span>
                  <span>{v.name}</span>
                </div>
              ))}
              {(!r.vulnerabilities || r.vulnerabilities.length === 0) && (
                <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Zaiflik topilmadi</div>
              )}
            </div>
          ))}
        </div>
      )}

      {reportUrl && (
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <a href={reportUrl} target="_blank" rel="noopener noreferrer"
            style={{
              display: 'inline-block', padding: '12px 32px',
              borderRadius: 'var(--radius)', border: '1px solid var(--primary)',
              color: 'var(--primary)', textDecoration: 'none', fontSize: 14,
              fontWeight: 600,
            }}>
            Hisobotni ochish &rarr;
          </a>
        </div>
      )}
    </div>
  )
}
