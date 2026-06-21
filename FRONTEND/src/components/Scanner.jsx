import React, { useState, useRef, useEffect } from 'react'
import { useScanner } from '../ScannerContext'
import { useWindowSize } from '../hooks/useWindowSize'
import { apiFetch } from '../api'
import styled, { keyframes } from 'styled-components'

const minimizeOut = keyframes`
  from {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
  to {
    transform: scale(0.05) translateY(150px);
    opacity: 0;
  }
`
const restoreIn = keyframes`
  from {
    transform: scale(0.05) translateY(150px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
`
const PanelWrapper = styled.div`
  transform-origin: bottom center;
  animation: ${props => props.$closing ? minimizeOut : restoreIn} 0.45s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  ${props => props.$hidden && `
    pointer-events: none;
    position: absolute;
    width: 0;
    height: 0;
    overflow: hidden;
  `}
`
const RestoreButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(39, 195, 159, 0.1);
  border: 1px solid #27c39f;
  border-radius: 8px;
  color: #27c39f;
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    background: rgba(39, 195, 159, 0.2);
  }
`

const StyledWrapper = styled.div`
  .pb-ai-input-wrap {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px;
    border-radius: 999px;
    background: linear-gradient(
      180deg,
      rgba(166, 125, 255, 0.18) 0%,
      rgba(122, 69, 255, 0.12) 100%
    );
    backdrop-filter: blur(14px);
    box-shadow:
      0 0 0 4px rgba(125, 71, 255, 0.08),
      0 0 24px rgba(98, 43, 255, 0.14),
      inset 0 0 6px rgba(255, 255, 255, 0.1);
    overflow: hidden;
    isolation: isolate;
  }
  .pb-ai-input-wrap::before {
    content: "";
    position: absolute;
    inset: 2px;
    border-radius: inherit;
    background: linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.16),
      rgba(255, 255, 255, 0.04) 45%,
      rgba(255, 255, 255, 0)
    );
    pointer-events: none;
    z-index: 1;
  }
  .pb-ai-input-wrap::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background-image: radial-gradient(
        circle at bottom center,
        rgba(255, 255, 255, 0.18) 0%,
        rgba(255, 255, 255, 0.06) 20%,
        transparent 60%
      ),
      radial-gradient(rgba(255, 255, 255, 0.1) 0.8px, transparent 0.8px);
    background-size: 100% 100%, 5px 5px;
    opacity: 0.35;
    mix-blend-mode: overlay;
    pointer-events: none;
    z-index: 2;
  }
  .pb-ai-input {
    position: relative;
    z-index: 3;
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    padding: 0 8px;
    color: var(--text);
    font-size: 13px;
    font-weight: 400;
    letter-spacing: -0.15px;
  }
  .pb-ai-input::placeholder {
    color: var(--text-muted);
    opacity: 0.6;
  }
  .pb-ai-input-btn {
    position: relative;
    z-index: 3;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    border: none;
    outline: none;
    cursor: pointer;
    padding: 10px 14px;
    border-radius: 999px;
    color: #fff;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: -0.15px;
    background: linear-gradient(180deg, #a67dff 0%, #7a45ff 45%, #5d24ff 100%);
    box-shadow:
      0 0 0 3px rgba(125, 71, 255, 0.1),
      0 5px 12px rgba(98, 43, 255, 0.2),
      inset 0 2px 8px rgba(255, 255, 255, 0.16);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .pb-ai-input-btn:hover {
    transform: translateY(-1px);
    box-shadow:
      0 0 0 4px rgba(125, 71, 255, 0.12),
      0 8px 16px rgba(98, 43, 255, 0.24),
      inset 0 2px 8px rgba(255, 255, 255, 0.2);
  }
  .pb-ai-input-btn:active {
    transform: scale(0.97);
  }
  .pb-ai-sparkle {
    font-size: 12px;
    transform: translateY(-1px);
  }
`;

const TerminalBox = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  font-family: Menlo, Consolas, monospace;
  font-size: 14px;
  color: #e6e6e6;
  border-radius: 5px;
  overflow: hidden;
`

const TerminalToolbar = styled.div`
  display: flex;
  height: 30px;
  align-items: center;
  padding: 0 8px;
  background: #212121;
  justify-content: space-between;
`

const Buttons = styled.div`
  display: flex;
  align-items: center;
`

const Dot = styled.button`
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0;
  margin-right: 5px;
  font-size: 8px;
  height: 12px;
  width: 12px;
  border: none;
  border-radius: 100%;
  background: ${p => p.$color || 'linear-gradient(#7d7871 0%, #595953 100%)'};
  cursor: pointer;
`

const TabUser = styled.p`
  color: #d5d0ce;
  margin-left: 6px;
  font-size: 14px;
  line-height: 15px;
`

const AddTab = styled.div`
  border: 1px solid #fff;
  color: #fff;
  padding: 0 6px;
  border-radius: 4px 4px 0 0;
  border-bottom: none;
  cursor: pointer;
`

const TerminalBody = styled.div`
  background: rgba(0, 0, 0, 0.6);
  flex: 1;
  padding-top: 2px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
`

const Prompt = styled.div`
  display: flex;
  align-items: center;
  padding: 4px;
`

const PromptSpan = styled.span`
  margin-left: 4px;
`

const UserSpan = styled(PromptSpan)`
  color: #1eff8e;
`

const LocationSpan = styled(PromptSpan)`
  color: #4878c0;
`

const BlingSpan = styled(PromptSpan)`
  color: #ddd;
`

const Cursor = styled.span`
  display: block;
  height: 14px;
  width: 5px;
  margin-left: 10px;
  animation: curbl 1200ms linear infinite;

  @keyframes curbl {
    0% { background: #fff; }
    49% { background: #fff; }
    60% { background: transparent; }
    99% { background: transparent; }
    100% { background: #fff; }
  }
`

const OutputArea = styled.div`
  padding: 4px;
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 320px);
`

const OutputLine = styled.pre`
  margin: 0;
  color: ${p =>
    p.$log?.startsWith('nexura@scanner') ? '#38bdf8' :
    p.$log?.startsWith('[ERROR]') || p.$log?.startsWith('[FAIL]') ? '#ef4444' :
    p.$log?.startsWith('[STDERR]') ? '#f59e0b' : '#e6e6e6'};
`

const InputRow = styled.div`
  padding: 8px 4px 4px;
`

const TerminalInput2 = styled.input`
  width: 100%;
  padding: 6px;
  background: transparent;
  border: none;
  color: #e6e6e6;
  caret-color: #1eff8e;
  outline: none;
  font-family: Menlo, Consolas, monospace;
  font-size: 12px;

  &::placeholder { color: rgba(255,255,255,0.2); }
`

// Simple helper to format basic markdown (bold, lists, code blocks) safely into HTML
function renderMarkdown(text) {
  if (!text) return ''
  
  let html = text
    // Escape HTML tags first to prevent XSS
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    
    // Code blocks: ```code```
    .replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre style="background: #0f172a; padding: 12px; border-radius: 6px; border: 1px solid var(--border); overflow-x: auto; margin: 10px 0; font-family: monospace; font-size: 13px; color: #38bdf8;">${p1.trim()}</pre>`
    })
    
    // Inline code: `code`
    .replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.25); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #f43f5e;">$1</code>')
    
    // Bold: **text**
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    
    // Unordered lists: - item
    .replace(/^\s*-\s+(.+)$/gm, '<li style="margin-left: 20px; margin-bottom: 4px;">$1</li>')
    
    // Line breaks
    .replace(/\n/g, '<br />')

  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

export default function Scanner() {
  const { scanning, setScanning, setFindings, setReportUrl, setScanId,
    chatLogs, setChatLogs, chatLoading, setChatLoading,
    terminalLogs, setTerminalLogs, terminalLoading, setTerminalLoading } = useScanner()
  const winWidth = useWindowSize()
  
  // AI Chat States
  const [chatInput, setChatInput] = useState('')
  const [modelLoaded, setModelLoaded] = useState(null)
  const [chatSessions, setChatSessions] = useState([])
  const [chatSessionId, setChatSessionId] = useState(() => {
    return localStorage.getItem('nexura_chat_session') || ''
  })
  const [showSidebar, setShowSidebar] = useState(true)
  const [chatMinimized, setChatMinimized] = useState(false)
  const [chatClosing, setChatClosing] = useState(false)
  const [terminalMinimized, setTerminalMinimized] = useState(false)
  const [terminalClosing, setTerminalClosing] = useState(false)

  const handleMinimizeChat = () => {
    setChatClosing(true)
    setTimeout(() => {
      setChatMinimized(true)
      setChatClosing(false)
    }, 450)
  }
  const handleRestoreChat = () => {
    setChatMinimized(false)
  }
  const handleMinimizeTerminal = () => {
    setTerminalClosing(true)
    setTimeout(() => {
      setTerminalMinimized(true)
      setTerminalClosing(false)
    }, 450)
  }
  const handleRestoreTerminal = () => {
    setTerminalMinimized(false)
  }
  
  // Terminal States
  const [terminalInput, setTerminalInput] = useState('')

  // Refs for auto-scroll
  const chatEndRef = useRef(null)
  const terminalEndRef = useRef(null)

  // Polling for AI status every 30s
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status')
        if (res.ok) {
          const data = await res.json()
          setModelLoaded(!!data.model_loaded)
        } else {
          setModelLoaded(false)
        }
      } catch (err) {
        console.error('Status fetch error:', err)
        setModelLoaded(false)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  // Load sessions list
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const res = await apiFetch('/api/chat/sessions')
        if (res.ok) {
          const data = await res.json()
          setChatSessions(data.sessions || [])
        }
      } catch (e) {
        console.warn('Chat sessions load failed:', e)
      }
    }
    loadSessions()
  }, [])

  // Load chat history on mount or session switch
  useEffect(() => {
    if (modelLoaded === null) return

    const loadHistory = async () => {
      if (!chatSessionId) {
        setChatLogs([{
          role: 'ai',
          content: modelLoaded
            ? "Assalomu alaykum! Men NEXURA AI yordamchisiman. Menga skanerlash buyrug'ingizni yozing, masalan: 'example.com saytining zaifliklarini tekshir'"
            : "Assalomu alaykum! Hozirda AI yordamchisi vaqtincha mavjud emas. Terminal orqali to'g'ridan-to'g'ri skanerlash buyruqlarini ishlatishingiz mumkin. Masalan: nmap -F example.com",
          timestamp: new Date(),
        }])
        return
      }

      try {
        const res = await apiFetch(`/api/chat/history?session_id=${encodeURIComponent(chatSessionId)}`)
        if (res.ok) {
          const data = await res.json()
          if (data.messages && data.messages.length > 0) {
            const formatted = data.messages.map(m => ({
              role: m.role === 'user' ? 'user' : 'ai',
              content: m.parts?.[0]?.text || '',
              timestamp: new Date(m.created_at || Date.now()),
            }))
            setChatLogs(formatted)
            return
          }
        }
      } catch (e) {
        console.warn('Chat history load failed:', e)
      }
      setChatLogs([{
        role: 'ai',
        content: modelLoaded
          ? "Assalomu alaykum! Men NEXURA AI yordamchisiman. Menga skanerlash buyrug'ingizni yozing, masalan: 'example.com saytining zaifliklarini tekshir'"
          : "Assalomu alaykum! Hozirda AI yordamchisi vaqtincha mavjud emas. Terminal orqali to'g'ridan-to'g'ri skanerlash buyruqlarini ishlatishingiz mumkin. Masalan: nmap -F example.com",
        timestamp: new Date(),
      }])
    }

    loadHistory()
  }, [modelLoaded, chatSessionId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatLogs, chatLoading])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [terminalLogs])

  // Session management
  const switchSession = (sid) => {
    setChatSessionId(sid)
    localStorage.setItem('nexura_chat_session', sid)
    setShowSidebar(false)
  }

  const createNewSession = () => {
    const sid = 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem('nexura_chat_session', sid)
    setChatSessionId(sid)
    setChatLogs([])
    setShowSidebar(false)
  }

  // Submit message to AI assistant
  const handleChatSubmit = async (e) => {
    e.preventDefault()
    if (!chatInput.trim() || chatLoading) return

    const userMsg = chatInput.trim()
    setChatInput('')

    // Auto-create session if needed
    let sid = chatSessionId
    if (!sid) {
      sid = 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
      localStorage.setItem('nexura_chat_session', sid)
      setChatSessionId(sid)
    }

    setChatLogs(prev => [...prev, { role: 'user', content: userMsg, timestamp: new Date() }])

    if (modelLoaded === false) {
      setChatLogs(prev => [...prev, {
        role: 'ai',
        content: "AI hozir offline. Terminal orqali ishlashingiz mumkin.",
        timestamp: new Date()
      }])
      return
    }

    // Simple greetings — skip loading
    const simpleWords = ['salom', 'xayr', 'rahmat', 'yaxshimisan', 'nima gap', 'nma gap']
    const isSimple = simpleWords.some(w => userMsg.toLowerCase().includes(w))

    if (!isSimple) {
      setChatLoading(true)
      setScanning(true)
    }

    try {
      const res = await apiFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, session_id: sid }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `Server xatosi (${res.status})`)
      }

      const data = await res.json()
      
      // Update global states if a scan was performed
      if (data.scan_data) {
        const sd = data.scan_data
        if (sd.report_html) setReportUrl(sd.report_html)
        if (sd.id) setScanId(sd.id)
        if (sd.results) {
          let crit = 0, high = 0, med = 0, low = 0
          sd.results.forEach(r => {
            r.vulnerabilities?.forEach(v => {
              const sev = v.severity?.toLowerCase()
              if (sev === 'critical') crit++
              else if (sev === 'high') high++
              else if (sev === 'medium') med++
              else low++
            })
          })
          setFindings({ critical: crit, high, medium: med, low })
        }
      }

      setChatLogs(prev => [...prev, {
        role: 'ai',
        content: data.response,
        scanData: data.scan_data,
        timestamp: new Date()
      }])
    } catch (err) {
      setChatLogs(prev => [...prev, {
        role: 'ai',
        content: `Xatolik yuz berdi: ${err.message}`,
        timestamp: new Date()
      }])
    } finally {
      setChatLoading(false)
      setScanning(false)
    }
  }

  // Submit command to secure web terminal
  const handleTerminalSubmit = async (e) => {
    e.preventDefault()
    if (!terminalInput.trim() || terminalLoading) return

    const cmd = terminalInput.trim()
    setTerminalInput('')
    
    // Add command to log
    setTerminalLogs(prev => [...prev, `nexura@scanner:~$ ${cmd}`])
    
    // Handle local clear command
    if (cmd.toLowerCase() === 'clear') {
      setTerminalLogs([])
      return
    }

    setTerminalLoading(true)
    
    try {
      const res = await apiFetch('/api/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cmd }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `Server aloqa xatosi (${res.status})`)
      }

      const data = await res.json()
      
      if (data.error) {
        setTerminalLogs(prev => [...prev, `[ERROR]: ${data.error}`])
      } else {
        if (data.output) {
          setTerminalLogs(prev => [...prev, data.output])
        }
        if (data.error_log) {
          setTerminalLogs(prev => [...prev, `[STDERR]: ${data.error_log}`])
        }
        if (data.code !== 0 && !data.output) {
          setTerminalLogs(prev => [...prev, `Exit code: ${data.code}`])
        }
      }
    } catch (err) {
      setTerminalLogs(prev => [...prev, `[FAIL]: ${err.message}`])
    } finally {
      setTerminalLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16 }}>
      {/* Title Header */}
      <div style={{ textAlign: 'center', marginBottom: 4 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, marginBottom: 2 }}>
          NEXURA
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          AI Kiberxavfsizlik yordamchisi va interaktiv terminal muhiti
        </p>
      </div>

      {/* Main Split Grid */}
      <div style={{
        display: 'flex',
        flexDirection: winWidth < 1024 ? 'column' : 'row',
        gap: 20,
        flex: 1,
        minHeight: 'calc(100vh - 150px)',
      }}>
        {/* LEFT COLUMN: AI Chat Assistant */}
        {!chatMinimized ? (
        <PanelWrapper $closing={chatClosing} style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'row',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          overflow: 'hidden',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
        }}>
          {/* CHAT HISTORY SIDEBAR */}
          <div style={{
            width: showSidebar ? 220 : 0,
            minWidth: showSidebar ? 220 : 0,
            overflow: 'hidden',
            background: 'var(--bg-input)',
            borderRight: showSidebar ? '1px solid var(--border)' : 'none',
            display: 'flex',
            flexDirection: 'column',
            transition: 'width 0.2s, min-width 0.2s',
          }}>
            <div style={{
              padding: 12,
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 6,
            }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
                Chatlar
              </span>
              <button onClick={createNewSession} style={{
                background: 'var(--primary)',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                padding: '4px 8px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}>
                + Yangi
              </button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
              {chatSessions.length === 0 && (
                <div style={{ padding: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
                  Hozircha chatlar yo'q
                </div>
              )}
              {chatSessions.map((s, i) => {
                const isActive = s.session_id === chatSessionId
                const label = s.first_msg
                  ? s.first_msg.replace('T', ' ').slice(0, 16)
                  : `Chat ${i + 1}`
                return (
                  <div key={s.session_id} onClick={() => switchSession(s.session_id)} style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    background: isActive ? 'rgba(24,95,165,0.15)' : 'transparent',
                    borderLeft: isActive ? '3px solid var(--primary)' : '3px solid transparent',
                    fontSize: 12,
                    color: isActive ? 'var(--primary)' : 'var(--text)',
                    fontWeight: isActive ? 600 : 400,
                    transition: 'all 0.15s',
                  }}>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {label}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                      {s.msg_count} xabar
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Chat Main Area */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            {/* Chat Header */}
            <div style={{
              background: 'var(--bg-input)',
              padding: '12px 16px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span onClick={handleMinimizeChat} style={{ width: 12, height: 12, borderRadius: '50%', background: '#ee411a', cursor: 'pointer', display: 'inline-block', transition: 'transform 0.15s' }}
                  onMouseEnter={e => e.target.style.transform = 'scale(1.3)'}
                  onMouseLeave={e => e.target.style.transform = 'scale(1)'} />
                <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#f5a623', display: 'inline-block' }} />
                <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c39f', display: 'inline-block' }} />
              </div>
              <button onClick={() => setShowSidebar(s => !s)} style={{
                background: 'none',
                border: '1px solid var(--border)',
                borderRadius: 4,
                padding: '4px 6px',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                fontSize: 14,
                display: 'flex',
                alignItems: 'center',
              }}>
                ☰
              </button>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>NEXURA AI Assistant</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                  <span style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: modelLoaded ? '#22c55e' : '#f59e0b',
                    display: 'inline-block'
                  }} />
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {modelLoaded ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>
              {scanning && (
                <span style={{
                  marginLeft: 'auto',
                  fontSize: 12,
                  color: 'var(--primary)',
                  background: 'rgba(24,95,165,0.15)',
                  padding: '4px 8px',
                  borderRadius: 4,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)',
                    animation: 'pulse 1.5s infinite'
                  }} />
                  AI Skanerlashda...
                </span>
              )}
            </div>

          {/* Chat Messages Log */}
          <div style={{
            flex: 1,
            padding: 16,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            maxHeight: 'calc(100vh - 300px)',
          }}>
            {chatLogs.map((log, idx) => (
              <div key={idx} style={{
                alignSelf: log.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                display: 'flex',
                flexDirection: 'column',
              }}>
                <div style={{
                  background: log.role === 'user' ? 'var(--primary)' : 'var(--bg-input)',
                  color: log.role === 'user' ? '#fff' : 'var(--text)',
                  padding: '12px 16px',
                  borderRadius: log.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                  fontSize: 14,
                  lineHeight: '1.5',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                }}>
                  {renderMarkdown(log.content)}
                  
                  {/* Render Scan Results Card inside AI response */}
                  {log.scanData && (
                    <div style={{
                      marginTop: 12,
                      background: 'rgba(15,23,42,0.6)',
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                      padding: 12,
                      fontSize: 13,
                    }}>
                      <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                        <span>📊 Skanerlash Tafsilotlari</span>
                        <span style={{ color: 'var(--success)' }}>Yakunlandi</span>
                      </div>
                      <div style={{ marginBottom: 4 }}><strong>Target:</strong> {log.scanData.target}</div>
                      
                      {/* Technologies display */}
                      {log.scanData.technologies && (
                        <div style={{ marginBottom: 8, fontSize: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {log.scanData.technologies.cms && (
                            <span style={{ background: 'rgba(124,58,237,0.2)', color: 'var(--critical)', padding: '2px 6px', borderRadius: 4 }}>
                              CMS: {log.scanData.technologies.cms}
                            </span>
                          )}
                          {log.scanData.technologies.server && (
                            <span style={{ background: 'rgba(59,130,246,0.2)', color: 'var(--primary)', padding: '2px 6px', borderRadius: 4 }}>
                              Server: {log.scanData.technologies.server}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Tools run summary */}
                      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 8 }}>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>Ishlatilgan vositalar:</div>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {log.scanData.results?.map((r, i) => (
                            <div key={i} style={{
                              background: 'var(--bg-card)',
                              padding: '4px 8px',
                              borderRadius: 4,
                              fontSize: 11,
                              border: '1px solid var(--border)',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 6
                            }}>
                              <span style={{ width: 6, height: 6, borderRadius: '50%', background: r.success ? 'var(--success)' : 'var(--danger)' }} />
                              {r.tool?.toUpperCase()}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Download Link */}
                      {log.scanData.report_html && (
                        <div style={{ marginTop: 12, textAlign: 'center' }}>
                          <a href={log.scanData.report_html} target="_blank" rel="noopener noreferrer"
                            style={{
                              display: 'block',
                              background: 'var(--primary)',
                              color: '#fff',
                              textDecoration: 'none',
                              padding: '8px 12px',
                              borderRadius: 6,
                              fontWeight: 700,
                              fontSize: 12,
                              transition: 'opacity 0.15s',
                            }}
                            onMouseOver={e => e.currentTarget.style.opacity = 0.9}
                            onMouseOut={e => e.currentTarget.style.opacity = 1}
                          >
                            Batafsil HTML Hisobotni Ochish &rarr;
                          </a>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <span style={{
                  fontSize: 10,
                  color: 'var(--text-muted)',
                  alignSelf: log.role === 'user' ? 'flex-end' : 'flex-start',
                  marginTop: 4,
                  marginRight: log.role === 'user' ? 4 : 0,
                  marginLeft: log.role === 'ai' ? 4 : 0,
                }}>
                  {log.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
            
            {chatLoading && (
              <div style={{ alignSelf: 'flex-start', background: 'var(--bg-input)', padding: '12px 16px', borderRadius: '12px 12px 12px 2px', display: 'flex', gap: 4, alignItems: 'center' }}>
                <span className="dot" style={{ width: 8, height: 8, background: 'var(--text-muted)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both' }} />
                <span className="dot" style={{ width: 8, height: 8, background: 'var(--text-muted)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.2s' }} />
                <span className="dot" style={{ width: 8, height: 8, background: 'var(--text-muted)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.4s' }} />
                <style>{`
                  @keyframes bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1.0); }
                  }
                  @keyframes pulse {
                    0%, 100% { opacity: 0.5; }
                    50% { opacity: 1; }
                  }
                `}</style>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Area */}
          <form onSubmit={handleChatSubmit} style={{
            padding: 12,
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-card)',
          }}>
            <StyledWrapper>
              <div className="pb-ai-input-wrap">
                <input
                  type="text"
                  className="pb-ai-input"
                  placeholder="Buyruq yozing..."
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  disabled={chatLoading}
                />
                <button className="pb-ai-input-btn" type="submit" disabled={chatLoading || !chatInput.trim()}>
                  <span>Yuborish</span>
                  <span className="pb-ai-sparkle">✦</span>
                </button>
              </div>
            </StyledWrapper>
          </form>
        </div>{/* End Chat Main Area */}
        </PanelWrapper>
        ) : (
          <RestoreButton onClick={handleRestoreChat}>
            <span>💬</span> AI Chat'ni ochish
          </RestoreButton>
        )}

        {/* RIGHT COLUMN: Terminal */}
        {!terminalMinimized ? (
        <PanelWrapper $closing={terminalClosing} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <TerminalBox>
          <TerminalToolbar>
            <Buttons>
              <Dot $color="#ee411a" onClick={handleMinimizeTerminal} />
              <Dot />
              <Dot />
            </Buttons>
            <TabUser>00Kubi@admin: ~</TabUser>
            <AddTab>+</AddTab>
          </TerminalToolbar>
          <TerminalBody>
            <Prompt>
              <UserSpan>00Kubi@admin:</UserSpan>
              <LocationSpan>~</LocationSpan>
              <BlingSpan>$</BlingSpan>
              <Cursor />
            </Prompt>
            <OutputArea>
              {terminalLogs.length === 0 && !terminalLoading && (
                <OutputLine $log="">Welcome to NEXURA Security Terminal</OutputLine>
              )}
              {terminalLogs.map((log, idx) => (
                <OutputLine key={idx} $log={log}>{log}</OutputLine>
              ))}
              {terminalLoading && (
                <OutputLine $log="">Buyruq bajarilmoqda, kuting...</OutputLine>
              )}
              <div ref={terminalEndRef} />
            </OutputArea>
            <InputRow>
              <form onSubmit={handleTerminalSubmit}>
                <TerminalInput2
                  value={terminalInput}
                  onChange={e => setTerminalInput(e.target.value)}
                  placeholder="nmap -F target.com"
                  disabled={terminalLoading}
                  autoFocus
                />
              </form>
            </InputRow>
          </TerminalBody>
        </TerminalBox>
        </PanelWrapper>
        ) : (
          <RestoreButton onClick={handleRestoreTerminal}>
            <span>⌨</span> Terminalni ochish
          </RestoreButton>
        )}
      </div>
    </div>
  )
}
