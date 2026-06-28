import React, { useEffect } from 'react'
import styled, { keyframes } from 'styled-components'
import Loader from './Loader'
import { useScanner } from '../ScannerContext'

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
`

const Dock = styled.div`
  position: fixed;
  bottom: 25px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  z-index: 1000;
`

const CircleBtn = styled.div`
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(145deg, #1e293b, #0f172a);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 10px 40px rgba(0, 255, 136, 0.3), inset 0 2px 10px rgba(255,255,255,0.1);
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  border: 2px solid rgba(0, 255, 136, 0.3);
  &:hover {
    transform: scale(1.1) translateY(-5px);
    box-shadow: 0 20px 50px rgba(0, 255, 136, 0.5), inset 0 2px 10px rgba(255,255,255,0.2);
    border-color: rgba(0, 255, 136, 0.6);
  }
  &:active {
    transform: scale(0.95);
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
    img { width: 32px; height: 32px; }
  }
`

const Badge = styled.span`
  position: absolute;
  top: -6px;
  right: -6px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border-radius: 50%;
  min-width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(239,68,68,0.5);
  animation: ${pulse} 2s infinite;
`

export default function TerminalToggle() {
  const {
    chatMinimized, setChatMinimized, setChatClosing,
    terminalVisible, setTerminalVisible, setTerminalClosing
  } = useScanner()

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

  const toggleTerminal = () => {
    if (terminalVisible) {
      setTerminalClosing(true)
      setTimeout(() => {
        setTerminalVisible(false)
        setTerminalClosing(false)
      }, 600)
    } else {
      setTerminalVisible(true)
    }
  }

  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === '`') {
        e.preventDefault()
        toggleTerminal()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [terminalVisible])

  return (
    <Dock>
      <CircleBtn onClick={toggleChat} title="Chatni ochish/yopish">
        <Loader />
      </CircleBtn>
      <div style={{ position: 'relative' }}>
        <CircleBtn onClick={toggleTerminal} title="Terminalni ochish (Ctrl+`)">
          <img src="/terminal.png" alt="Terminal" />
        </CircleBtn>
        <Badge>1</Badge>
      </div>
    </Dock>
  )
}
