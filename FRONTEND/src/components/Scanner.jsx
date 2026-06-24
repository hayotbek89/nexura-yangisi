import React, { useState, useRef, useEffect } from 'react'
import { useScanner } from '../ScannerContext'

import { apiFetch } from '../api'
import styled, { keyframes } from 'styled-components'

const genieClose = keyframes`
  0% {
    clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%);
    transform: scale(1) translate3d(0, 0, 0);
    opacity: 1;
  }
  100% {
    clip-path: polygon(45% 0%, 55% 0%, 50% 100%, 50% 100%);
    transform: scale(0.05) translate3d(0, 250px, 0);
    opacity: 0;
  }
`
const genieOpen = keyframes`
  0% {
    clip-path: polygon(45% 0%, 55% 0%, 50% 100%, 50% 100%);
    transform: scale(0.05) translate3d(0, 250px, 0);
    opacity: 0;
  }
  100% {
    clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%);
    transform: scale(1) translate3d(0, 0, 0);
    opacity: 1;
  }
`
const PanelWrapper = styled.div`
  transform-origin: bottom center;
  animation: ${props => props.$closing ? genieClose : genieOpen} 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  will-change: transform, opacity;
  backface-visibility: hidden;
  perspective: 1000px;
  overflow: hidden;
  min-height: 0;
`

const dockBounce = keyframes`
  0%, 100% { transform: translateY(0) scale(1); }
  30% { transform: translateY(-18px) scale(1.1); }
  50% { transform: translateY(0) scale(0.95); }
  70% { transform: translateY(-8px) scale(1.05); }
  85% { transform: translateY(0) scale(1); }
`
const PanelsContainer = styled.div`
  display: flex;
  flex-direction: row;
  gap: 16px;
  width: 100%;
  flex: 1;
  min-height: 0;
  height: 100%;
  align-items: stretch;
  overflow: hidden;
  @media (max-width: 1024px) {
    flex-direction: column;
    height: auto;
    min-height: auto;
    flex: none;
  }
`
const Panel = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  @media (max-width: 1024px) {
    height: 50vh;
    flex: none;
    min-height: 300px;
  }
`
const Dock = styled.div`
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(15, 21, 37, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid #2761c3;
  border-radius: 16px;
  z-index: 100;
  ${props => props.$empty && `display: none;`}
`
const DockItem = styled.button`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: rgba(39, 195, 159, 0.1);
  border: 1px solid #27c39f;
  border-radius: 10px;
  color: #27c39f;
  font-size: 11px;
  cursor: pointer;
  transform: scale(${props => props.$scale || 1}) translateY(${props => props.$scale > 1 ? -(props.$scale - 1) * 20 : 0}px);
  transition: transform 0.15s cubic-bezier(0.25, 0.1, 0.25, 1);
  transform-origin: bottom center;
  animation: ${props => props.$justAdded ? dockBounce : 'none'} 0.6s cubic-bezier(0.25, 0.46, 0.45, 1.4);
  &:hover {
    background: rgba(39, 195, 159, 0.2);
    box-shadow: 0 4px 12px rgba(39, 195, 159, 0.3);
  }
  &:active {
    transform: scale(${props => (props.$scale || 1) * 0.95}) translateY(0);
  }
`
const DockIcon = styled.div`
  font-size: 20px;
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
  flex-shrink: 0;
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
  min-height: 0;
  overflow: hidden;
`



const OutputArea = styled.div`
  padding: 4px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: #27c39f33 transparent;
  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb { background: #27c39f55; border-radius: 2px; }
`

const OutputLine = styled.pre`
  margin: 0;
  color: ${p =>
    p.$log?.startsWith('nexura@scanner') ? '#38bdf8' :
    p.$log?.startsWith('[ERROR]') || p.$log?.startsWith('[FAIL]') ? '#ef4444' :
    p.$log?.startsWith('[STDERR]') ? '#f59e0b' : '#e6e6e6'};
`

const TerminalInput2 = styled.input`
  width: 100%;
  padding: 6px;
  background: transparent;
  border: none;
  color: #e6e6e6;
  caret-color: #e6e6e6;
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
    terminals, setTerminals, activeTerminal, setActiveTerminal,
    terminalScrolledUp, setTerminalScrolledUp,
    appendToTerminal, addTerminal, closeTerminal } = useScanner()
  
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
  const [chatJustMinimized, setChatJustMinimized] = useState(false)
  const [terminalJustMinimized, setTerminalJustMinimized] = useState(false)
  const [mouseX, setMouseX] = useState(null)
  const dockRef = useRef(null)

  const handleDockMouseMove = (e) => {
    const rect = dockRef.current.getBoundingClientRect()
    setMouseX(e.clientX - rect.left)
  }
  const handleDockMouseLeave = () => {
    setMouseX(null)
  }

  const handleMinimizeChat = () => {
    setChatClosing(true)
    setTimeout(() => {
      setChatMinimized(true)
      setChatClosing(false)
      setChatJustMinimized(true)
      setTimeout(() => setChatJustMinimized(false), 600)
    }, 600)
  }
  const handleRestoreChat = () => {
    setChatMinimized(false)
  }
  const handleMinimizeTerminal = () => {
    setTerminalClosing(true)
    setTimeout(() => {
      setTerminalMinimized(true)
      setTerminalClosing(false)
      setTerminalJustMinimized(true)
      setTimeout(() => setTerminalJustMinimized(false), 600)
    }, 600)
  }
  const handleRestoreTerminal = () => {
    setTerminalMinimized(false)
  }

  const getItemScale = (itemIndex, totalItems, itemWidth = 90) => {
    if (mouseX === null) return 1
    const itemCenter = itemIndex * itemWidth + itemWidth / 2
    const distance = Math.abs(mouseX - itemCenter)
    const maxDistance = 150
    if (distance > maxDistance) return 1
    return 1 + (1 - distance / maxDistance) * 0.4
  }
  
  // QuickScan (Option B)
  const [qsTarget, setQsTarget] = useState('')
  const [qsTool, setQsTool] = useState('nmap')
  const [availableTools, setAvailableTools] = useState([])
  const [qsLoading, setQsLoading] = useState(false)
  const [showQuickScan, setShowQuickScan] = useState(false)

  // Chat tool selection (Option A)
  const [pendingTarget, setPendingTarget] = useState(null)

  useEffect(() => {
    apiFetch('/api/tools').then(r => r.json()).then(d => {
      setAvailableTools((d.tools || []).filter(t => t.available))
    }).catch(() => {})
  }, [])

  // Build command from tool + target (mirrors backend TOOL_TEMPLATES + _clean_target)
  const TOOL_TEMPLATES = {
    nmap: 'nmap -sV -sC -O -T4 {host}',
    nuclei: 'nuclei -u {target} -severity low,medium,high,critical',
    nikto: 'nikto -h {target}',
    sqlmap: 'sqlmap -u {target} --batch --random-agent',
    gobuster: 'gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt -t 50',
    whatweb: 'whatweb {target}',
    amass: 'amass enum -d {host}',
  }
  const cleanTarget = (target, tool) => {
    let host = target.replace(/^https?:\/\//, '').replace(/[/?#].*$/, '')
    if (['nmap', 'amass'].includes(tool)) return host
    if (['nuclei', 'nikto', 'whatweb', 'gobuster'].includes(tool)) {
      const scheme = target.startsWith('https://') ? 'https://' : target.startsWith('http://') ? 'http://' : 'https://'
      return scheme + host
    }
    if (tool === 'sqlmap') return target
    return host
  }
  const termSubmitRefs = useRef({})

  const runScanWithTool = (target, tool) => {
    const template = TOOL_TEMPLATES[tool]
    if (!template) return
    const host = cleanTarget(target, tool)
    const cmd = template.replace('{target}', target).replace('{host}', host)
    // Set the command into the active terminal's input
    setTerminals(prev => prev.map(t =>
      t.id === activeTerminal ? { ...t, input: cmd } : t
    ))
    setQsLoading(true)
    setPendingTarget(null)
    // Auto-submit the terminal form on next render
    setTimeout(() => {
      const form = termSubmitRefs.current[activeTerminal]
      if (form) form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))
      setQsLoading(false)
    }, 100)
  }

  // Detect domain/IP/URL pattern for Option A
  const TARGET_RE = /([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|https?:\/\/[^\s]+/

  // Terminal refs
  const termRefs = useRef({})

  const activeTerm = terminals.find(t => t.id === activeTerminal) || terminals[0]

  // Refs for auto-scroll
  const chatEndRef = useRef(null)

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

  // Smart auto-scroll: only scroll down if user is already near bottom
  const handleTerminalScroll = (termId, e) => {
    const el = e.currentTarget
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
    setTerminalScrolledUp(prev => ({ ...prev, [termId]: !isNearBottom }))
  }
  useEffect(() => {
    const term = terminals.find(t => t.id === activeTerminal)
    if (!term || terminalScrolledUp[activeTerminal]) return
    const ref = termRefs.current[activeTerminal]
    if (ref) ref.scrollIntoView({ behavior: 'smooth' })
  }, [activeTerminal, terminals])

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

    // Option A: detect target in user message → show tool selection
    const matchTarget = userMsg.match(TARGET_RE)
    if (matchTarget) {
      setPendingTarget(matchTarget[0].replace(/\/+$/, ''))
    } else {
      setPendingTarget(null)
    }

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

      // Auto-execute scan if AI detected tool + target
      if (data.scan_action) {
        const { tool, target: scanTarget } = data.scan_action
        appendToActiveTerminal([`[NEXURA] AI ${tool.toUpperCase()} skanerlashni boshladi: ${scanTarget}`])
        runScanWithTool(scanTarget, tool)
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

  const SCAN_TOOLS = ['nmap', 'nuclei', 'nikto', 'sqlmap', 'gobuster', 'whatweb', 'amass']

  // Submit command to secure web terminal
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
      let fullOutput = ''
      if (data.error) {
        lines.push(`[ERROR]: ${data.error}`)
        fullOutput = data.error
      } else {
        if (data.output) lines.push(data.output)
        if (data.error_log) lines.push(`[STDERR]: ${data.error_log}`)
        if (data.code !== 0 && !data.output) lines.push(`Exit code: ${data.code}`)
        fullOutput = [data.output, data.error_log].filter(Boolean).join('\n')
      }
      appendToTerminal(termId, lines)

      // Detect scan command → send to Claude for analysis
      const firstWord = cmd.split(/\s+/)[0]?.toLowerCase()
      if (fullOutput && SCAN_TOOLS.includes(firstWord)) {
        let sid = chatSessionId
        if (!sid) {
          sid = 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
          localStorage.setItem('nexura_chat_session', sid)
          setChatSessionId(sid)
        }
        try {
          const analyzeRes = await apiFetch('/api/chat/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scan_output: fullOutput.slice(0, 30000),
              tool: firstWord,
              target: cmd.split(/\s+/).slice(-1)[0],
              session_id: sid,
            }),
          })
          if (analyzeRes.ok) {
            const analyzeData = await analyzeRes.json()
            setChatLogs(prev => [...prev, {
              role: 'ai',
              content: analyzeData.analysis,
              timestamp: new Date(),
            }])
          }
        } catch (_) {}
      }
    } catch (err) {
      appendToTerminal(termId, [`[FAIL]: ${err.message}`])
    } finally {
      setTerminals(prev => prev.map(t =>
        t.id === termId ? { ...t, loading: false } : t
      ))
    }
  }

  const appendToActiveTerminal = (lines) => {
    appendToTerminal(activeTerminal, lines)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16, paddingBottom: 80, overflow: 'hidden', minHeight: 0 }}>
      {/* Title Header */}
      <div style={{ textAlign: 'center', marginBottom: 4 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, marginBottom: 2 }}>
          NEXURA
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          AI Kiberxavfsizlik yordamchisi va interaktiv terminal muhiti
        </p>
      </div>

      {/* Option B: QuickScan Panel */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)',
        overflow: 'hidden', marginBottom: showQuickScan ? 0 : 0,
      }}>
        <div onClick={() => setShowQuickScan(!showQuickScan)} style={{
          padding: '10px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--bg-input)', userSelect: 'none',
        }}>
          <span style={{ fontSize: 16 }}>{showQuickScan ? '▾' : '▸'}</span>
          <span style={{ fontWeight: 600, fontSize: 13 }}>⚡ Tezkor skanerlash</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>— domen/IP kiriting va vositani tanlang</span>
        </div>
        {showQuickScan && (
          <div style={{ padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <input type="text" value={qsTarget} onChange={e => setQsTarget(e.target.value)}
              placeholder="example.com yoki 192.168.1.1"
              style={{
                flex: 1, minWidth: 200, padding: '8px 12px', background: 'var(--bg)', border: '1px solid var(--border)',
                borderRadius: 6, color: 'var(--text)', fontSize: 13, outline: 'none',
              }} />
            <select value={qsTool} onChange={e => setQsTool(e.target.value)}
              style={{
                padding: '8px 12px', background: 'var(--bg)', border: '1px solid var(--border)',
                borderRadius: 6, color: 'var(--text)', fontSize: 13, cursor: 'pointer', outline: 'none',
              }}>
              {availableTools.map(t => (
                <option key={t.name} value={t.name}>{t.label} — {t.description}</option>
              ))}
            </select>
            <button onClick={() => runScanWithTool(qsTarget.trim(), qsTool)} disabled={qsLoading || !qsTarget.trim()}
              style={{
                padding: '8px 20px', background: qsLoading ? 'var(--text-muted)' : 'var(--primary)',
                color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600,
                cursor: qsLoading ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
              }}>
              {qsLoading ? 'Skanerlanmoqda...' : 'Ishga tushirish'}
            </button>
          </div>
        )}
      </div>

      {/* Main Split Grid */}
      <div style={{
        display: 'flex',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
      }}>
        <PanelsContainer>
          {/* LEFT COLUMN: AI Chat Assistant */}
          {!chatMinimized && (
            <Panel style={{ flex: terminalMinimized ? 2 : 1 }}>
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
                    flexShrink: 0,
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
            overflowX: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            minHeight: 0,
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
                  flexShrink: 0,
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
                {/* Option A: Tool selection buttons */}
                {pendingTarget && availableTools.length > 0 && (
                  <div style={{
                    padding: '8px 12px', borderTop: '1px solid var(--border)',
                    background: 'rgba(39,195,159,0.05)',
                  }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                      {pendingTarget} — qaysi vosita bilan skanerlaymiz?
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {availableTools.map(t => (
                        <button key={t.name} onClick={() => { runScanWithTool(pendingTarget, t.name); setShowQuickScan(false); setPendingTarget(null) }}
                          style={{
                            padding: '6px 12px', background: 'rgba(24,95,165,0.15)', border: '1px solid var(--primary)',
                            borderRadius: 6, color: 'var(--primary)', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = 'rgba(24,95,165,0.3)'}
                          onMouseLeave={e => e.currentTarget.style.background = 'rgba(24,95,165,0.15)'}>
                          {t.label}
                        </button>
                      ))}
                      <button onClick={() => setPendingTarget(null)}
                        style={{
                          padding: '6px 12px', background: 'transparent', border: '1px solid var(--border)',
                          borderRadius: 6, color: 'var(--text-muted)', fontSize: 11, cursor: 'pointer',
                        }}>
                        Bekor qilish
                      </button>
                    </div>
                  </div>
                )}
              </div>{/* End Chat Main Area */}
              </PanelWrapper>
            </Panel>
          )}

          {/* RIGHT COLUMN: Terminal (multi-tab) */}
          {!terminalMinimized && (
            <Panel style={{ flex: chatMinimized ? 2 : 1 }}>
              <PanelWrapper $closing={terminalClosing} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <TerminalBox>
                <TerminalToolbar>
                  <Buttons>
                    <Dot $color="#ee411a" onClick={handleMinimizeTerminal} />
                    <Dot />
                    <Dot />
                  </Buttons>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1, overflow: 'hidden', margin: '0 8px' }}>
                    {terminals.map(t => (
                      <div key={t.id} onClick={() => setActiveTerminal(t.id)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 4,
                          padding: '3px 10px', cursor: 'pointer', borderRadius: '4px 4px 0 0',
                          fontSize: 12, color: t.id === activeTerminal ? '#fff' : '#888',
                          background: t.id === activeTerminal ? 'rgba(255,255,255,0.08)' : 'transparent',
                          borderBottom: t.id === activeTerminal ? '1px solid #27c39f' : '1px solid transparent',
                          transition: 'all 0.15s', whiteSpace: 'nowrap',
                        }}>
                        <span>#{terminals.indexOf(t) + 1}</span>
                        {terminals.length > 1 && (
                          <span onClick={(e) => { e.stopPropagation(); closeTerminal(t.id) }}
                            style={{ fontSize: 10, opacity: 0.5, cursor: 'pointer', marginLeft: 2 }}>
                            ✕
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                  <AddTab onClick={addTerminal}>+</AddTab>
                </TerminalToolbar>
                <TerminalBody>
                  {terminals.map(t => {
                    const inputId = 'term-input-' + t.id
                    return (
                    <div key={t.id} style={{ display: t.id === activeTerminal ? 'flex' : 'none', flex: 1, flexDirection: 'column', minHeight: 0 }}>
                      <OutputArea onScroll={(e) => handleTerminalScroll(t.id, e)} onClick={() => {
                        const inp = document.getElementById(inputId)
                        if (inp) inp.focus()
                      }}>
                        {t.logs.length === 0 && !t.loading && (
                          <OutputLine $log="">Welcome to NEXURA Security Terminal #{terminals.indexOf(t) + 1}</OutputLine>
                        )}
                        {t.logs.map((log, idx) => (
                          <OutputLine key={idx} $log={log}>{log}</OutputLine>
                        ))}
                        {t.loading && (
                          <OutputLine $log="">Buyruq bajarilmoqda, kuting...</OutputLine>
                        )}
                        <div style={{ display: 'flex', alignItems: 'center', padding: '4px 0', whiteSpace: 'nowrap' }}>
                          <span style={{marginLeft:4,color:'#1eff8e'}}>00Kubi@admin:</span>
                          <span style={{marginLeft:4,color:'#4878c0'}}>~</span>
                          <span style={{marginLeft:4,color:'#ddd'}}>$</span>
                          <form ref={el => termSubmitRefs.current[t.id] = el} onSubmit={(e) => handleTerminalSubmit(e, t.id)} style={{ display: 'flex', flex: 1, minWidth: 0 }}>
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
                        <div ref={el => termRefs.current[t.id] = el} />
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

      {/* macOS-style Dock */}
      <Dock
        ref={dockRef}
        onMouseMove={handleDockMouseMove}
        onMouseLeave={handleDockMouseLeave}
        $empty={!chatMinimized && !terminalMinimized}
      >
        {chatMinimized && (
          <DockItem
            $scale={getItemScale(0, (chatMinimized && terminalMinimized) ? 2 : 1)}
            $justAdded={chatJustMinimized}
            onClick={handleRestoreChat}
          >
            <DockIcon>💬</DockIcon>
            <span>AI Chat</span>
          </DockItem>
        )}
        {terminalMinimized && (
          <DockItem
            $scale={getItemScale((chatMinimized && terminalMinimized) ? 1 : 0, (chatMinimized && terminalMinimized) ? 2 : 1)}
            $justAdded={terminalJustMinimized}
            onClick={handleRestoreTerminal}
          >
            <DockIcon>⌨</DockIcon>
            <span>Terminal</span>
          </DockItem>
        )}
      </Dock>
    </div>
  )
}
