import React, { useState, useRef, useEffect } from 'react'
import { useScanner } from '../ScannerContext'

import { apiFetch } from '../api'
import styled, { keyframes } from 'styled-components'

const genieClose = keyframes`
  0% {
    transform: scale(1) translateY(0);
    opacity: 1;
    filter: blur(0px);
  }
  100% {
    transform: scale(0.1) translateY(200px);
    opacity: 0;
    filter: blur(20px);
  }
`
const genieOpen = keyframes`
  0% {
    transform: scale(0.1) translateY(200px);
    opacity: 0;
    filter: blur(20px);
  }
  60% {
    transform: scale(1.03) translateY(-10px);
    opacity: 1;
    filter: blur(2px);
  }
  80% {
    transform: scale(0.98) translateY(2px);
  }
  100% {
    transform: scale(1) translateY(0);
    opacity: 1;
    filter: blur(0px);
  }
`
const PanelWrapper = styled.div`
  transform-origin: bottom center;
  animation: ${props => props.$closing ? genieClose : genieOpen} 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  will-change: transform, opacity, filter;
  backface-visibility: hidden;
  perspective: 1000px;
  overflow: hidden;
  min-height: 0;
`

const PanelsContainer = styled.div`
  display: flex;
  flex-direction: row;
  gap: 20px;
  width: 100%;
  max-width: 1600px;
  flex: 1;
  min-height: 0;
  height: 100%;
  align-items: stretch;
  overflow: hidden;
  margin: 0 auto;
  @media (max-width: 1200px) {
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
  }
`
const Panel = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  @media (max-width: 1200px) {
    min-height: 500px;
    flex: none;
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
    display: flex;
    align-items: center;
    justify-content: center;
  }
`;

const TerminalBox = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  font-family: 'JetBrains Mono', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  color: #f8fafc;
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), inset 0 0 0 1px rgba(255, 255, 255, 0.05);
`

const TerminalToolbar = styled.div`
  display: flex;
  height: 44px;
  align-items: center;
  padding: 0 16px;
  background: rgba(30, 41, 59, 0.4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  justify-content: space-between;
  flex-shrink: 0;
  user-select: none;
`

const Buttons = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`

const Dot = styled.button`
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: none;
  background: ${p => p.$color || 'rgba(255, 255, 255, 0.2)'};
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s;
  position: relative;

  &:hover {
    opacity: 0.8;
  }

  &::after {
    content: "${p => p.$icon || ''}";
    font-size: 7px;
    color: rgba(0,0,0,0.5);
    font-weight: bold;
    display: none;
  }

  &:hover::after {
    display: block;
  }
`

const AddTab = styled.div`
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.6);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 18px;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
`

const TerminalBody = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.2);
`

const OutputArea = styled.div`
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
`

const OutputLine = styled.div`
  margin-bottom: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
  color: ${p =>
    p.$log?.includes('nexura@scanner:~$') ? '#38bdf8' :
    p.$log?.startsWith('[ERROR]') || p.$log?.startsWith('[FAIL]') ? '#f87171' :
    p.$log?.startsWith('[STDERR]') ? '#fbbf24' : '#e2e8f0'};
`

const TerminalInput2 = styled.input`
  width: 100%;
  padding: 0 8px;
  background: transparent;
  border: none;
  color: #fff;
  caret-color: #38bdf8;
  outline: none;
  font-family: inherit;
  font-size: inherit;

  &::placeholder { color: rgba(255,255,255,0.15); }
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

const MAX_CHATS = 20

export default function Scanner() {
  const { scanning, setScanning, setFindings, setReportUrl, setScanId,
    chatLogs, setChatLogs, chatLoading, setChatLoading,
    chatMinimized, setChatMinimized, chatClosing, setChatClosing,
    terminalVisible, setTerminalVisible, terminalClosing, setTerminalClosing } = useScanner()
  
  // AI Chat States
  const [chatInput, setChatInput] = useState('')
  const [modelLoaded, setModelLoaded] = useState(null)
  const [chatSessions, setChatSessions] = useState([])
  const [chatSessionId, setChatSessionId] = useState(() => {
    return localStorage.getItem('nexura_chat_session') || ''
  })
  const [showSidebar, setShowSidebar] = useState(true)
  const [deletingIds, setDeletingIds] = useState([])
  const [terminals, setTerminals] = useState([
    { id: 'term_1', logs: [], loading: false, input: '' },
  ])
  const [activeTerminal, setActiveTerminal] = useState('term_1')
  const [toast, setToast] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const toggleChat = () => {
    if (chatMinimized) {
      setChatMinimized(false)
    } else {
      setChatClosing(true)
      setTimeout(() => {
        setChatMinimized(true)
        setChatClosing(false)
      }, 600)
    }
  }

  const handleMinimizeTerminal = () => {
    setTerminalClosing(true)
    setTimeout(() => {
      setTerminalVisible(false)
      setTerminalClosing(false)
    }, 600)
  }

  const appendToTerminal = (termId, lines) => {
    setTerminals(prev => prev.map(t =>
      t.id === termId
        ? { ...t, logs: [...t.logs, ...(Array.isArray(lines) ? lines : [lines])] }
        : t
    ))
  }

  const addTerminal = () => {
    const id = 'term_' + Date.now() + '_' + Math.random().toString(36).slice(2, 4)
    setTerminals(prev => [...prev, { id, logs: [], loading: false, input: '' }])
    setActiveTerminal(id)
  }

  const closeTerminal = (id) => {
    setTerminals(prev => {
      const filtered = prev.filter(t => t.id !== id)
      if (filtered.length === 0) {
        const newId = 'term_' + Date.now()
        return [{ id: newId, logs: [], loading: false, input: '' }]
      }
      return filtered
    })
  }



  const handleTerminalSubmit = async (e, termId) => {
    e.preventDefault()
    const term = terminals.find(t => t.id === termId)
    if (!term || !term.input.trim() || term.loading) return

    const cmd = term.input.trim()
    setTerminals(prev => prev.map(t =>
      t.id === termId ? { ...t, input: '' } : t
    ))
    
    appendToTerminal(termId, [`nexura@scanner:~$ ${cmd}`])
    
    if (cmd.toLowerCase() === 'clear') {
      setTerminals(prev => prev.map(t =>
        t.id === termId ? { ...t, logs: [] } : t
      ))
      return
    }

    setTerminals(prev => prev.map(t =>
      t.id === termId ? { ...t, loading: true } : t
    ))
    
    // Avtomatik yopish mantiqi
    setChatClosing(true)
    setTerminalClosing(true)
    setTimeout(() => {
      setChatMinimized(true)
      setTerminalVisible(false)
      setChatClosing(false)
      setTerminalClosing(false)
      setScanning(true)
    }, 600)

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
      const lines = []
      if (data.error) {
        lines.push(`[ERROR]: ${data.error}`)
      } else {
        if (data.output) lines.push(data.output)
        if (data.error_log) lines.push(`[STDERR]: ${data.error_log}`)
        if (data.code !== 0 && !data.output) lines.push(`Exit code: ${data.code}`)
      }
      appendToTerminal(termId, lines)
    } catch (err) {
      appendToTerminal(termId, [`[FAIL]: ${err.message}`])
    } finally {
      setTerminals(prev => prev.map(t =>
        t.id === termId ? { ...t, loading: false } : t
      ))
    }
  }

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
  }, [terminals])

  // Session management
  const switchSession = (sid) => {
    setChatSessionId(sid)
    localStorage.setItem('nexura_chat_session', sid)
    setShowSidebar(false)
  }

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  // Enforce 20-chat limit: remove oldest if at max
  const enforceChatLimit = (prev) => {
    if (prev.length >= MAX_CHATS) {
      const oldest = prev[0]
      apiFetch(`/api/chat/history?session_id=${encodeURIComponent(oldest.session_id)}`, { method: 'DELETE' }).catch(() => {})
      showToast('Chatlar soni chegarasi (20) — eng eski chat o\'chirildi')
      return prev.slice(1)
    }
    return prev
  }

  const createNewSession = () => {
    setChatSessions(prev => enforceChatLimit(prev))
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
      // Avtomatik yopish mantiqi
      setChatClosing(true)
      setTerminalClosing(true)
      setTimeout(() => {
        setChatMinimized(true)
        setTerminalVisible(false)
        setChatClosing(false)
        setTerminalClosing(false)
        setScanning(true)
      }, 600)
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

  // Confirm delete handler
  const handleConfirmDelete = async () => {
    if (!confirmDelete) return
    const { label, session_id } = confirmDelete
    setConfirmDelete(null)

    if (session_id === '__all__') {
      setDeletingIds(chatSessions.map(s => s.session_id))
      setTimeout(async () => {
        for (const s of chatSessions) {
          try { await apiFetch(`/api/chat/history?session_id=${encodeURIComponent(s.session_id)}`, { method: 'DELETE' }) } catch (_) {}
        }
        setChatSessions([])
        setDeletingIds([])
        localStorage.removeItem('nexura_chat_session')
        setChatSessionId('')
        setChatLogs([])
        showToast('Barcha chatlar o\'chirildi')
      }, 300)
      return
    }

    setDeletingIds(prev => [...prev, session_id])
    setTimeout(async () => {
      try {
        await apiFetch(`/api/chat/history?session_id=${encodeURIComponent(session_id)}`, { method: 'DELETE' })
        setChatSessions(prev => prev.filter(x => x.session_id !== session_id))
        setDeletingIds(prev => prev.filter(id => id !== session_id))
        if (session_id === chatSessionId) {
          localStorage.removeItem('nexura_chat_session')
          setChatSessionId('')
          setChatLogs([])
        }
        showToast(`"${label}" chat o'chirildi`)
      } catch (err) {
        setDeletingIds(prev => prev.filter(id => id !== session_id))
        showToast('Xatolik yuz berdi')
      }
    }, 300)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16, paddingBottom: 90, overflow: 'hidden', minHeight: 0 }}>
      {/* Title Header */}
      <div style={{ textAlign: 'center', marginBottom: 0 }}>
        <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 2, letterSpacing: 2 }}>
          NEXURA
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, opacity: 0.8 }}>
          AI kiberxavfsizlik yordamchisi va interaktiv terminal muhiti
        </p>
      </div>



      {/* Main Split Grid */}
      <div style={{
        display: 'flex',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
        justifyContent: 'center',
        alignItems: 'center'
      }}>
        {scanning && <Loader />}

        <PanelsContainer style={{ display: scanning ? 'none' : 'flex' }}>
          {/* LEFT COLUMN: AI Chat Assistant */}
          {!chatMinimized && (
            <Panel style={{ flex: 1.2 }}>
              <PanelWrapper $closing={chatClosing} style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'row',
                background: 'rgba(30, 41, 59, 0.5)',
                backdropFilter: 'blur(30px) saturate(180%)',
                WebkitBackdropFilter: 'blur(30px) saturate(180%)',
                borderRadius: '18px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                overflow: 'hidden',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 0 0 1px rgba(255, 255, 255, 0.1)',
              }}>
                {/* CHAT HISTORY SIDEBAR */}
                <div style={{
                  width: showSidebar ? 240 : 0,
                  minWidth: showSidebar ? 240 : 0,
                  overflow: 'hidden',
                  background: 'rgba(15, 23, 42, 0.3)',
                  borderRight: showSidebar ? '1px solid rgba(255, 255, 255, 0.1)' : 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                }}>
                  <div style={{
                    padding: '20px 16px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}>
                    <span style={{ fontSize: 11, fontWeight: 800, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: 1.5 }}>
                      Chatlar
                    </span>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {chatSessions.length > 0 && (
                        <button onClick={() => setConfirmDelete({ label: null, session_id: '__all__' })} style={{
                          background: 'rgba(239,68,68,0.15)', color: '#ff453a',
                          border: 'none', borderRadius: 6, padding: '5px 8px',
                          fontSize: 12, cursor: 'pointer', transition: 'all 0.2s'
                        }} title="Barchasini tozalash">
                          🗑️
                        </button>
                      )}
                      <button onClick={createNewSession} style={{
                        background: 'rgba(255,255,255,0.1)',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        padding: '5px 10px',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}>
                        + Yangi
                      </button>
                    </div>
                  </div>
                  <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
                    {chatSessions.length === 0 && (
                      <div style={{ padding: 20, fontSize: 12, color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                        Tarix bo'sh
                      </div>
                    )}
                    {chatSessions.map((s, i) => {
                      const isActive = s.session_id === chatSessionId
                      const label = s.first_msg
                        ? s.first_msg.replace('T', ' ').slice(0, 16)
                        : `Chat ${i + 1}`
                      const isDeleting = deletingIds.includes(s.session_id)
                      return (
                        <div key={s.session_id} style={{
                          display: 'flex', alignItems: 'center',
                          background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                          borderRadius: '10px',
                          margin: '2px 0',
                          transition: 'all 0.2s ease',
                          position: 'relative',
                          opacity: isDeleting ? 0 : 1,
                          transform: isDeleting ? 'translateX(-20px)' : 'translateX(0)',
                          maxHeight: isDeleting ? 0 : 65,
                          overflow: 'hidden',
                        }}
                          onMouseEnter={e => {
                            e.currentTarget.style.background = isActive ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)';
                            const btn = e.currentTarget.querySelector('.chat-del-btn');
                            if (btn) btn.style.opacity = '1'
                          }}
                          onMouseLeave={e => {
                            e.currentTarget.style.background = isActive ? 'rgba(255,255,255,0.1)' : 'transparent';
                            const btn = e.currentTarget.querySelector('.chat-del-btn');
                            if (btn) btn.style.opacity = '0'
                          }}
                        >
                          <div onClick={() => switchSession(s.session_id)} style={{
                            flex: 1, padding: '12px 12px', cursor: 'pointer',
                            fontSize: 13, color: isActive ? '#fff' : 'rgba(255,255,255,0.7)',
                            fontWeight: isActive ? 600 : 400, minWidth: 0,
                          }}>
                            <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {label}
                            </div>
                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 4 }}>
                              {s.msg_count} xabar
                            </div>
                          </div>
                          <button className="chat-del-btn" onClick={() => setConfirmDelete({
                            label,
                            session_id: s.session_id,
                          })} style={{
                            background: 'transparent', border: 'none', color: '#ff453a',
                            cursor: 'pointer', padding: '8px', fontSize: 14, borderRadius: 8,
                            opacity: 0, flexShrink: 0, marginRight: 6, transition: 'all 0.2s',
                          }}>
                            ✕
                          </button>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Chat Main Area */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: 'rgba(15, 23, 42, 0.1)' }}>
                  {/* Chat Header */}
                  <div style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 15,
                    flexShrink: 0,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span onClick={toggleChat} style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f56', cursor: 'pointer', boxShadow: '0 0 2px rgba(0,0,0,0.2)', position: 'relative' }} />
                      <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#ffbd2e', boxShadow: '0 0 2px rgba(0,0,0,0.2)' }} />
                      <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c93f', boxShadow: '0 0 2px rgba(0,0,0,0.2)' }} />
                    </div>
                    <button onClick={() => setShowSidebar(s => !s)} style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 8,
                      padding: '6px',
                      cursor: 'pointer',
                      color: 'rgba(255,255,255,0.6)',
                      display: 'flex',
                      alignItems: 'center',
                      transition: 'all 0.2s'
                    }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
                    </button>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 15, color: '#fff' }}>NEXURA AI Assistant</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                        <span style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: modelLoaded ? '#34c759' : '#ff9500',
                          boxShadow: modelLoaded ? '0 0 8px rgba(52, 199, 89, 0.6)' : 'none',
                          display: 'inline-block'
                        }} />
                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>
                          {modelLoaded ? 'Online' : 'Connecting...'}
                        </span>
                      </div>
                    </div>
                    {scanning && (
                      <div style={{
                        marginLeft: 'auto',
                        fontSize: 12,
                        color: '#5856d6',
                        background: 'rgba(88, 86, 214, 0.15)',
                        padding: '6px 12px',
                        borderRadius: 20,
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        border: '1px solid rgba(88, 86, 214, 0.2)'
                      }}>
                        <div className="ai-pulse" style={{
                          width: 8, height: 8, borderRadius: '50%', background: '#5856d6',
                          boxShadow: '0 0 10px #5856d6'
                        }} />
                        Scanning...
                      </div>
                    )}
                  </div>

                  {/* Chat Messages Log */}
                  <div style={{
                    flex: 1,
                    padding: '20px',
                    overflowY: 'auto',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 20,
                    minHeight: 0,
                    scrollbarWidth: 'none'
                  }}>
                    <style>{`
                      .chat-scroll::-webkit-scrollbar { display: none; }
                      .ai-pulse { animation: ai-pulse-anim 1.5s infinite; }
                      @keyframes ai-pulse-anim { 0%, 100% { opacity: 0.5; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.1); } }
                    `}</style>
                    {chatLogs.map((log, idx) => (
                      <div key={idx} style={{
                        alignSelf: log.role === 'user' ? 'flex-end' : 'flex-start',
                        maxWidth: '80%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: log.role === 'user' ? 'flex-end' : 'flex-start',
                      }}>
                        <div style={{
                          background: log.role === 'user'
                            ? 'linear-gradient(135deg, #007aff, #0055ff)'
                            : 'rgba(255, 255, 255, 0.08)',
                          color: '#fff',
                          padding: '12px 18px',
                          borderRadius: log.role === 'user' ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
                          fontSize: 14,
                          lineHeight: '1.6',
                          boxShadow: log.role === 'user'
                            ? '0 4px 15px rgba(0, 122, 255, 0.3)'
                            : '0 4px 15px rgba(0, 0, 0, 0.1)',
                          border: log.role === 'ai' ? '1px solid rgba(255,255,255,0.05)' : 'none',
                        }}>
                          {renderMarkdown(log.content)}

                          {log.scanData && (
                            <div style={{
                              marginTop: 15,
                              background: 'rgba(0, 0, 0, 0.2)',
                              borderRadius: 14,
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              padding: 16,
                              fontSize: 13,
                            }}>
                              <div style={{ fontWeight: 700, color: '#5856d6', marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                                  Scan Natijalari
                                </span>
                                <span style={{ fontSize: 11, background: 'rgba(52, 199, 89, 0.2)', color: '#34c759', padding: '2px 8px', borderRadius: 10 }}>Muvaffaqiyatli</span>
                              </div>
                              <div style={{ marginBottom: 10, color: 'rgba(255,255,255,0.8)' }}>
                                <strong style={{ color: '#fff' }}>Target:</strong> {log.scanData.target}
                              </div>

                              {log.scanData.technologies && (
                                <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                  {log.scanData.technologies.cms && (
                                    <span style={{ background: 'rgba(175, 82, 222, 0.2)', color: '#af52de', padding: '4px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600 }}>
                                      {log.scanData.technologies.cms}
                                    </span>
                                  )}
                                  {log.scanData.technologies.server && (
                                    <span style={{ background: 'rgba(0, 122, 255, 0.2)', color: '#007aff', padding: '4px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600 }}>
                                      {log.scanData.technologies.server}
                                    </span>
                                  )}
                                </div>
                              )}

                              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
                                {log.scanData.results?.map((r, i) => (
                                  <div key={i} style={{
                                    background: 'rgba(255,255,255,0.05)',
                                    padding: '5px 10px',
                                    borderRadius: 8,
                                    fontSize: 11,
                                    color: 'rgba(255,255,255,0.6)',
                                    border: '1px solid rgba(255,255,255,0.05)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 8
                                  }}>
                                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: r.success ? '#34c759' : '#ff3b30' }} />
                                    {r.tool?.toUpperCase()}
                                  </div>
                                ))}
                              </div>

                              {log.scanData.report_html && (
                                <div style={{ marginTop: 15 }}>
                                  <a href={log.scanData.report_html} target="_blank" rel="noopener noreferrer"
                                    style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      gap: 8,
                                      background: 'rgba(255,255,255,0.1)',
                                      color: '#fff',
                                      textDecoration: 'none',
                                      padding: '10px',
                                      borderRadius: 10,
                                      fontWeight: 600,
                                      fontSize: 12,
                                      transition: 'all 0.2s',
                                      border: '1px solid rgba(255,255,255,0.1)'
                                    }}
                                    onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.15)'}
                                    onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                                  >
                                    Hisobotni ko'rish
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                                  </a>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                        <span style={{
                          fontSize: 10,
                          color: 'rgba(255,255,255,0.3)',
                          marginTop: 6,
                          fontWeight: 500,
                        }}>
                          {log.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    ))}

                    {chatLoading && (
                      <div style={{ alignSelf: 'flex-start', background: 'rgba(255, 255, 255, 0.08)', padding: '12px 20px', borderRadius: '20px 20px 20px 4px', display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span className="dot" style={{ width: 6, height: 6, background: 'rgba(255,255,255,0.4)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both' }} />
                        <span className="dot" style={{ width: 6, height: 6, background: 'rgba(255,255,255,0.4)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.2s' }} />
                        <span className="dot" style={{ width: 6, height: 6, background: 'rgba(255,255,255,0.4)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.4s' }} />
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Chat Input Area */}
                  <form onSubmit={handleChatSubmit} style={{
                    padding: '16px 20px',
                    background: 'rgba(15, 23, 42, 0.2)',
                    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                    flexShrink: 0,
                  }}>
                    <StyledWrapper>
                      <div className="pb-ai-input-wrap" style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        padding: '8px',
                        boxShadow: 'none'
                      }}>
                        <input
                          type="text"
                          className="pb-ai-input"
                          placeholder="Savol yoki buyruq..."
                          value={chatInput}
                          onChange={e => setChatInput(e.target.value)}
                          disabled={chatLoading}
                          style={{ fontSize: 14, color: '#fff' }}
                        />
                        <button className="pb-ai-input-btn" type="submit" disabled={chatLoading || !chatInput.trim()} style={{
                          padding: '8px 16px',
                          background: chatInput.trim() ? 'linear-gradient(135deg, #007aff, #0055ff)' : 'rgba(255,255,255,0.1)',
                          boxShadow: chatInput.trim() ? '0 4px 12px rgba(0, 122, 255, 0.3)' : 'none',
                          transition: 'all 0.3s'
                        }}>
                          <span style={{ fontWeight: 600 }}>Yuborish</span>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polyline points="22 2 15 22 11 13 2 9 22 2"/></svg>
                        </button>
                      </div>
                    </StyledWrapper>
                  </form>
                </div>{/* End Chat Main Area */}
              </PanelWrapper>
            </Panel>
          )}

          {/* RIGHT COLUMN: Terminal (multi-tab) */}
          {terminalVisible && (
            <Panel style={{ flex: 1 }}>
              <PanelWrapper $closing={terminalClosing} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <TerminalBox>
                <TerminalToolbar>
                  <Buttons>
                    <Dot $color="#ff5f56" $icon="✕" onClick={handleMinimizeTerminal} />
                    <Dot $color="#ffbd2e" $icon="−" />
                    <Dot $color="#27c93f" $icon="⤢" />
                  </Buttons>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, overflow: 'hidden', margin: '0 20px' }}>
                    {terminals.map((t, idx) => (
                      <div key={t.id} onClick={() => setActiveTerminal(t.id)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          padding: '6px 14px', cursor: 'pointer', borderRadius: '8px 8px 0 0',
                          fontSize: 12, fontWeight: 500,
                          color: t.id === activeTerminal ? '#fff' : 'rgba(255,255,255,0.4)',
                          background: t.id === activeTerminal ? 'rgba(255,255,255,0.1)' : 'transparent',
                          borderBottom: t.id === activeTerminal ? '2px solid #38bdf8' : '2px solid transparent',
                          transition: 'all 0.2s', whiteSpace: 'nowrap',
                          position: 'relative'
                        }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" style={{ opacity: 0.7 }}><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                        <span>session-{idx + 1}</span>
                        {terminals.length > 1 && (
                          <span onClick={(e) => { e.stopPropagation(); closeTerminal(t.id) }}
                            style={{ fontSize: 14, opacity: 0.5, cursor: 'pointer', padding: '0 2px' }}
                            onMouseEnter={e => e.target.style.opacity = 1}
                            onMouseLeave={e => e.target.style.opacity = 0.5}>
                            ×
                          </span>
                        )}
                      </div>
                    ))}
                    <AddTab onClick={addTerminal}>+</AddTab>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#38bdf8', boxShadow: '0 0 8px #38bdf8' }} />
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.3)', letterSpacing: 0.5 }}>ZSH</span>
                  </div>
                </TerminalToolbar>

                <TerminalBody>
                  {terminals.map(t => {
                    const inputId = 'term-input-' + t.id
                    return (
                    <div key={t.id} style={{ display: t.id === activeTerminal ? 'flex' : 'none', flex: 1, flexDirection: 'column', minHeight: 0 }}>
                      <OutputArea>
                        {t.logs.length === 0 && !t.loading && (
                          <OutputLine $log="">
                            <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>NEXURA Security Terminal v2.0.0</span><br/>
                            <span style={{ opacity: 0.5 }}>Type 'help' to list available commands.</span><br/><br/>
                          </OutputLine>
                        )}
                        {t.logs.map((log, idx) => (
                          <OutputLine key={idx} $log={log}>{log}</OutputLine>
                        ))}
                        {t.loading && (
                          <OutputLine $log="" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span className="ai-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#38bdf8' }} />
                            <span style={{ opacity: 0.7 }}>Processing request...</span>
                          </OutputLine>
                        )}
                        <div ref={terminalEndRef} />

                        <div style={{ display: 'flex', alignItems: 'flex-start', padding: '10px 0' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 10, flexShrink: 0 }}>
                            <span style={{ color: '#27c93f', fontWeight: 'bold' }}>➜</span>
                            <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>~</span>
                            <span style={{ color: '#fff', opacity: 0.5 }}>git:(</span>
                            <span style={{ color: '#f87171' }}>main</span>
                            <span style={{ color: '#fff', opacity: 0.5 }}>)</span>
                          </div>
                          <form onSubmit={(e) => handleTerminalSubmit(e, t.id)} style={{ flex: 1 }}>
                            <TerminalInput2
                              id={inputId}
                              value={t.input}
                              onChange={e => {
                                setTerminals(prev => prev.map(term =>
                                  term.id === t.id ? { ...term, input: e.target.value } : term
                                ))
                              }}
                              placeholder="nmap -F target.com"
                              disabled={t.loading}
                              autoFocus
                            />
                          </form>
                        </div>
                      </OutputArea>
                    </div>
                    )
                  })}
                </TerminalBody>
              </TerminalBox>
              </PanelWrapper>
            </Panel>
          )}

        </PanelsContainer>
      </div>

      {/* Confirm Delete Modal */}
      {confirmDelete && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          animation: 'fadeIn 0.2s ease',
        }} onClick={() => setConfirmDelete(null)}>
          <div style={{
            background: '#1a1a2e', border: '1px solid #ef4444', borderRadius: 12,
            padding: 24, maxWidth: 360, width: '90%', boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 28, textAlign: 'center', marginBottom: 12 }}>🗑️</div>
            <div style={{ fontSize: 15, fontWeight: 600, textAlign: 'center', marginBottom: 8, color: '#e6e6e6' }}>
              {confirmDelete.session_id === '__all__'
                ? 'Barcha chatlarni o\'chirmoqchimisiz?'
                : `"${confirmDelete.label}" chatni o'chirmoqchimisiz?`}
            </div>
            <div style={{ fontSize: 12, color: '#999', textAlign: 'center', marginBottom: 20 }}>
              Bu amalni qaytarib bo'lmaydi
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button onClick={() => setConfirmDelete(null)} style={{
                padding: '10px 24px', borderRadius: 8, border: '1px solid #333',
                background: 'transparent', color: '#ccc', fontSize: 13, fontWeight: 600, cursor: 'pointer',
              }}>Bekor qilish</button>
              <button onClick={handleConfirmDelete} style={{
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: '#ef4444', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
              }}>O'chirish</button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 80, left: '50%', transform: 'translateX(-50%)', zIndex: 9998,
          background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)',
          border: '1px solid #27c39f', borderRadius: 8, padding: '10px 20px',
          fontSize: 13, color: '#e6e6e6', boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          animation: 'fadeIn 0.2s ease',
          maxWidth: '90%', textAlign: 'center',
        }}>
          {toast}
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
