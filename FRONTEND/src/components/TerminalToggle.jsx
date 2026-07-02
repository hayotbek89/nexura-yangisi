import React, { useEffect } from 'react'
import styled, { keyframes } from 'styled-components'
import { useScanner } from '../ScannerContext'

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
`

const Dock = styled.div`
  position: fixed;
  bottom: 24px;
  left: calc(50% + 110px);
  transform: translateX(-50%);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 12px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.3);
  backdrop-filter: blur(25px) saturate(200%);
  -webkit-backdrop-filter: blur(25px) saturate(200%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 24px;
  z-index: 10001;
  box-shadow:
    0 20px 50px rgba(0, 0, 0, 0.5),
    inset 0 0 0 1px rgba(255, 255, 255, 0.05);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);

  &::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.1) 0%,
      rgba(255, 255, 255, 0) 100%
    );
    pointer-events: none;
  }

  &:hover {
    background: rgba(15, 23, 42, 0.5);
    gap: 18px;
    padding: 10px 18px;
  }

  @media (max-width: 768px) {
    left: 50%;
    bottom: 30px;
  }
`

const CircleBtn = styled.div`
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: ${props => props.$active ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.05)'};
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid ${props => props.$active ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)'};

  &::after {
    content: "";
    position: absolute;
    bottom: -8px;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #fff;
    opacity: ${props => props.$isOpen ? 0.9 : 0};
    box-shadow: 0 0 8px #fff;
    transition: all 0.3s ease;
  }

  &:hover {
    transform: scale(1.2) translateY(-12px);
    background: rgba(255, 255, 255, 0.18);
    z-index: 10;
  }

  &:active {
    transform: scale(0.95);
  }

  img {
    width: 32px;
    height: 32px;
    object-fit: contain;
    filter: drop-shadow(0 4px 10px rgba(0,0,0,0.4));
  }

  svg {
    width: 36px;
    height: 36px;
  }
`

const Badge = styled.span`
  position: absolute;
  top: -6px;
  right: -6px;
  background: linear-gradient(135deg, #ff453a, #ff3b30);
  color: white;
  border-radius: 10px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  box-shadow: 0 4px 12px rgba(255, 59, 48, 0.5);
  border: 1.5px solid rgba(255, 255, 255, 0.2);
  pointer-events: none;
  z-index: 11;
`

export default function TerminalToggle() {
  const {
    chatMinimized, setChatMinimized, setChatClosing,
    terminalVisible, setTerminalVisible, setTerminalClosing
  } = useScanner()

  const starPath = "M63,37c-6.7-4-4-27-13-27s-6.3,23-13,27-27,4-27,13,20.3,9,27,13,4,27,13,27,6.3-23,13-27,27-4,27-13-20.3-9-27-13Z";

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
      <div style={{ position: 'relative' }}>
        <CircleBtn onClick={toggleChat} title="Chatni ochish/yopish" $isOpen={!chatMinimized} $active={!chatMinimized}>
          <svg viewBox="0 0 100 100" style={{ color: '#a855f7', filter: 'drop-shadow(0 0 15px rgba(168, 85, 247, 0.6))' }}>
            <path d={starPath} fill="currentColor" />
          </svg>
        </CircleBtn>
      </div>
      <div style={{ position: 'relative' }}>
        <CircleBtn onClick={toggleTerminal} title="Terminalni ochish (Ctrl+`)" $isOpen={terminalVisible} $active={terminalVisible}>
          <img src="/terminal.png" alt="Terminal" />
        </CircleBtn>
        <Badge>1</Badge>
      </div>
    </Dock>
  )
}


