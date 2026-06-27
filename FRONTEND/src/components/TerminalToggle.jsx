import React, { useState, useEffect, useRef, useCallback } from 'react'
import styled, { keyframes, css } from 'styled-components'
import { apiFetch } from '../api'

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
`

const slideUp = keyframes`
  from { opacity: 0; transform: translateX(-50%) translateY(30px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
`

const ToggleButton = styled.div`
  position: fixed;
  bottom: 25px;
  left: 50%;
  transform: translateX(-50%);
  width: 64px;
  height: 64px;
  background: linear-gradient(145deg, #1e293b, #0f172a);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 10px 40px rgba(0, 255, 136, 0.3), inset 0 2px 10px rgba(255,255,255,0.1);
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  z-index: 1000;
  border: 2px solid rgba(0, 255, 136, 0.3);
  &:hover {
    transform: translateX(-50%) scale(1.1) translateY(-5px);
    box-shadow: 0 20px 50px rgba(0, 255, 136, 0.5), inset 0 2px 10px rgba(255,255,255,0.2);
    border-color: rgba(0, 255, 136, 0.6);
  }
  &:active {
    transform: translateX(-50%) scale(0.95);
  }
  img {
    width: 40px;
    height: 40px;
    object-fit: contain;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    transition: transform 0.3s ease;
  }
  &:hover img {
    transform: scale(1.1);
  }
  @media (max-width: 768px) {
    width: 56px;
    height: 56px;
    bottom: 20px;
    img { width: 32px; height: 32px; }
  }
`

const Badge = styled.span`
  position: absolute;
  top: -5px;
  right: -5px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border-radius: 50%;
  min-width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  padding: 0 6px;
  box-shadow: 0 2px 8px rgba(239,68,68,0.5);
  animation: ${pulse} 2s infinite;
`

const Container = styled.div`
  position: fixed;
  bottom: 110px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  width: 900px;
  max-width: 95vw;
  height: 550px;
  max-height: 70vh;
  background: linear-gradient(145deg, #0f172a, #1e293b);
  border-radius: 16px;
  box-shadow: 0 25px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1);
  display: flex;
  flex-direction: column;
  opacity: 0;
  transition: all 0.4s cubic-bezier(0.4,0,0.2,1);
  z-index: 999;
  border: 1px solid rgba(0, 255, 136, 0.2);
  overflow: hidden;
  pointer-events: none;
  ${props => props.$active && css`
    opacity: 1;
    pointer-events: auto;
    transform: translateX(-50%) translateY(0);
    animation: ${slideUp} 0.4s ease;
  `}
  @media (max-width: 768px) {
    width: 95vw;
    height: 60vh;
    bottom: 90px;
    border-radius: 12px;
  }
`

const Header = styled.div`
  background: linear-gradient(135deg, #1e293b, #334155);
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
`

const HeaderButtons = styled.div`
  display: flex;
  gap: 8px;
`

const HeaderBtn = styled.button`
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0,0,0,0.6);
  font-weight: bold;
  background: ${props => props.$color === 'yellow' ? 'linear-gradient(135deg, #fbbf24, #f59e0b)' : 'linear-gradient(135deg, #ef4444, #dc2626)'};
  &:hover { transform: scale(1.2); }
`

const Title = styled.span`
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 600;
  margin-left: 8px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
`

const Body = styled.div`
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #0a0e1a;
  color: #00ff88;
  &::-webkit-scrollbar { width: 8px; }
  &::-webkit-scrollbar-track { background: #0f172a; border-radius: 4px; }
  &::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #00ff88, #00cc6a); border-radius: 4px; }
  &::-webkit-scrollbar-thumb:hover { background: linear-gradient(135deg, #00cc6a, #00994d); }
`

const Output = styled.div`
  white-space: pre-wrap;
  word-break: break-all;
  margin-bottom: 12px;
  color: #94a3b8;
`

const InputWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 255, 136, 0.2);
`

const Prompt = styled.span`
  color: #00ff88;
  font-weight: bold;
  white-space: nowrap;
  text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
`

const InputField = styled.input`
  flex: 1;
  background: transparent;
  border: none;
  color: #00ff88;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  outline: none;
  caret-color: #00ff88;
`

const WELCOME_MSG = `\x1b[36m
╔═══════════════════════════════════════════════════════╗
║         NEXURA Security Terminal v2.0                ║
║         AI-powered cybersecurity scanner             ║
╚═══════════════════════════════════════════════════════╝
\x1b[0m

\x1b[32m\u2713\x1b[0m Tizim tayyor. Yordam uchun \x1b[33m'help'\x1b[0m deb yozing.

Tayyor bo'lgan buyruqlar:
  \u2022 \x1b[33mscan example.com with nmap\x1b[0m
  \u2022 \x1b[33mcheck github:username/repo dependencies\x1b[0m
  \u2022 \x1b[33mfind vulnerabilities on example.com\x1b[0m
  \u2022 \x1b[33mhelp\x1b[0m - Barcha buyruqlar ro'yxati
`

export default function TerminalToggle() {
  const [active, setActive] = useState(false)
  const [output, setOutput] = useState(WELCOME_MSG)
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([])
  const [historyIdx, setHistoryIdx] = useState(-1)
  const inputRef = useRef(null)
  const bodyRef = useRef(null)

  const toggle = useCallback(() => setActive(a => !a), [])

  const close = useCallback(() => setActive(false), [])

  const execute = useCallback(async (cmd) => {
    const trimmed = cmd.trim()
    if (!trimmed) return

    setOutput(prev => prev + `\n\x1b[32mnexura@scanner:~$\x1b[0m ${trimmed}\n`)
    setHistory(h => [...h, trimmed])
    setHistoryIdx(-1)

    try {
      const res = await apiFetch('/api/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: trimmed }),
      })
      const data = await res.json()
      const out = data.output || data.response || data.error || 'No output'
      setOutput(prev => prev + `${out}\n`)
    } catch (err) {
      setOutput(prev => prev + `\x1b[31mError: ${err.message}\x1b[0m\n`)
    }
  }, [])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      execute(input)
      setInput('')
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (historyIdx < 0) {
        setHistoryIdx(history.length - 1)
        setInput(history[history.length - 1] || '')
      } else if (historyIdx > 0) {
        const idx = historyIdx - 1
        setHistoryIdx(idx)
        setInput(history[idx])
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIdx >= 0 && historyIdx < history.length - 1) {
        const idx = historyIdx + 1
        setHistoryIdx(idx)
        setInput(history[idx])
      } else {
        setHistoryIdx(-1)
        setInput('')
      }
    }
  }, [input, execute, history, historyIdx])

  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === '`') {
        e.preventDefault()
        toggle()
      }
      if (e.key === 'Escape' && active) {
        close()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [active, toggle, close])

  useEffect(() => {
    if (active && inputRef.current) {
      inputRef.current.focus()
    }
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [active, output])

  return (
    <>
      <ToggleButton onClick={toggle} title="Terminalni ochish (Ctrl+`)">
        <img src="/terminal.png" alt="Terminal" />
        {!active && <Badge>1</Badge>}
      </ToggleButton>
      <Container $active={active}>
        <Header>
          <HeaderButtons>
            <HeaderBtn $color="yellow" onClick={close}>−</HeaderBtn>
            <HeaderBtn $color="red" onClick={close}>×</HeaderBtn>
          </HeaderButtons>
          <Title>NEXURA Terminal</Title>
        </Header>
        <Body ref={bodyRef} onClick={() => inputRef.current?.focus()}>
          <Output>{output}</Output>
          <InputWrapper>
            <Prompt>nexura@scanner:~$</Prompt>
            <InputField
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              autoComplete="off"
            />
          </InputWrapper>
        </Body>
      </Container>
    </>
  )
}
