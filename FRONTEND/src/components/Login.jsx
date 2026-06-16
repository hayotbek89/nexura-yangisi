import React, { useState, useEffect } from 'react'
import styled, { keyframes } from 'styled-components'

const SECRET_KEY = 'nexura-shadow-9685'
const MAX_ATTEMPTS = 3
const BLOCK_DURATION = 5 * 60 * 1000

const glitch = keyframes`
  0% { text-shadow: 2px 0 #27c39f, -2px 0 #2761c3; }
  25% { text-shadow: -2px 0 #27c39f, 2px 0 #2761c3; }
  50% { text-shadow: 2px 2px #27c39f, -2px -2px #2761c3; }
  75% { text-shadow: -2px 2px #27c39f, 2px -2px #2761c3; }
  100% { text-shadow: 2px 0 #27c39f, -2px 0 #2761c3; }
`

const shake = keyframes`
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-6px); }
  20%, 40%, 60%, 80% { transform: translateX(6px); }
`

const flashGreen = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(39, 195, 159, 0.6); }
  50% { box-shadow: 0 0 40px 10px rgba(39, 195, 159, 0.3); }
  100% { box-shadow: 0 0 0 0 rgba(39, 195, 159, 0); }
`

const particleFall = keyframes`
  0% { transform: translateY(-100vh) rotate(0deg); opacity: 1; }
  100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
`

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`

const Wrapper = styled.div`
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  background: #0a0e1a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  font-family: 'Courier New', monospace;
`

const ParticleCanvas = styled.div`
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;

  span {
    position: absolute;
    color: #27c39f;
    font-size: 10px;
    opacity: 0.15;
    animation: ${particleFall} ${props => props.duration || '8s'} linear infinite;
    animation-delay: ${props => props.delay || '0s'};
    top: -10%;
  }
`

const Card = styled.div`
  position: relative;
  z-index: 1;
  background: rgba(10, 14, 26, 0.9);
  border: 1px solid #2761c3;
  box-shadow: 0 0 30px rgba(39, 195, 159, 0.1), inset 0 0 60px rgba(39, 195, 159, 0.03);
  clip-path: polygon(12px 0%, calc(100% - 12px) 0%, 100% 12px, 100% calc(100% - 12px), calc(100% - 12px) 100%, 12px 100%, 0% calc(100% - 12px), 0% 12px);
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  animation: ${fadeIn} 0.6s ease-out;
`

const Logo = styled.div`
  font-size: 36px;
  font-weight: 800;
  color: #27c39f;
  text-align: center;
  letter-spacing: 6px;
  margin-bottom: 8px;
  animation: ${glitch} 2s infinite;
`

const Subtitle = styled.div`
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
  letter-spacing: 2px;
  margin-bottom: 40px;
  text-transform: uppercase;
`

const InputWrapper = styled.div`
  margin-bottom: 20px;
`

const StyledInput = styled.input`
  width: 100%;
  padding: 14px 16px;
  background: transparent;
  border: 1px solid ${props => props.$hasError ? '#ff3355' : '#2761c3'};
  color: #27c39f;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  outline: none;
  clip-path: polygon(6px 0%, calc(100% - 6px) 0%, 100% 6px, 100% calc(100% - 6px), calc(100% - 6px) 100%, 6px 100%, 0% calc(100% - 6px), 0% 6px);
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
  animation: ${props => props.$shake ? shake : props.$flash ? flashGreen : 'none'} 0.5s ease;

  &:focus {
    border-color: #27c39f;
    box-shadow: 0 0 12px rgba(39, 195, 159, 0.2);
  }

  &::placeholder {
    color: rgba(39, 195, 159, 0.3);
  }
`

const LoginButton = styled.button`
  width: 100%;
  padding: 14px;
  background: transparent;
  border: 1px solid #27c39f;
  color: #27c39f;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  font-weight: bold;
  letter-spacing: 3px;
  cursor: pointer;
  clip-path: polygon(8px 0%, calc(100% - 8px) 0%, 100% 8px, 100% calc(100% - 8px), calc(100% - 8px) 100%, 8px 100%, 0% calc(100% - 8px), 0% 8px);
  transition: background 0.2s, box-shadow 0.2s;

  &:hover:not(:disabled) {
    background: rgba(39, 195, 159, 0.1);
    box-shadow: 0 0 20px rgba(39, 195, 159, 0.2);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`

const ErrorText = styled.div`
  color: #ff3355;
  font-size: 11px;
  text-align: center;
  margin-top: 16px;
  letter-spacing: 1px;
`

const BlockText = styled.div`
  color: #ff3355;
  font-size: 12px;
  text-align: center;
  margin-top: 16px;
  letter-spacing: 1px;
`

const Hint = styled.div`
  color: rgba(255, 255, 255, 0.2);
  font-size: 10px;
  text-align: center;
  margin-top: 24px;
  letter-spacing: 1px;
`

export default function Login({ onLogin }) {
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [shakeInput, setShakeInput] = useState(false)
  const [flashInput, setFlashInput] = useState(false)
  const [blockedUntil, setBlockedUntil] = useState(() => {
    const stored = localStorage.getItem('nexura_blocked_until')
    return stored ? parseInt(stored, 10) : 0
  })
  const [countdown, setCountdown] = useState(0)

  useEffect(() => {
    if (!blockedUntil || Date.now() > blockedUntil) {
      setBlockedUntil(0)
      setCountdown(0)
      return
    }
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((blockedUntil - Date.now()) / 1000))
      setCountdown(remaining)
      if (remaining <= 0) {
        setBlockedUntil(0)
        localStorage.removeItem('nexura_blocked_until')
        localStorage.removeItem('nexura_attempts')
      }
    }
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [blockedUntil])

  const handleSubmit = () => {
    if (blockedUntil && Date.now() < blockedUntil) return

    if (input === SECRET_KEY) {
      setError('')
      setFlashInput(true)
      setTimeout(() => {
        onLogin()
      }, 400)
      return
    }

    const attempts = parseInt(localStorage.getItem('nexura_attempts') || '0', 10) + 1
    localStorage.setItem('nexura_attempts', String(attempts))

    setShakeInput(true)
    setError(`Xato kalit! Urinish: ${attempts}/${MAX_ATTEMPTS}`)
    setTimeout(() => setShakeInput(false), 500)

    if (attempts >= MAX_ATTEMPTS) {
      const until = Date.now() + BLOCK_DURATION
      localStorage.setItem('nexura_blocked_until', String(until))
      setBlockedUntil(until)
      setError('')
    }

    setInput('')
  }

  const particles = Array.from({ length: 30 }, (_, i) => (
    <span
      key={i}
      style={{
        left: `${Math.random() * 100}%`,
        animationDuration: `${6 + Math.random() * 8}s`,
        animationDelay: `${Math.random() * 8}s`,
      }}
    >
      {String.fromCharCode(0x30A0 + Math.floor(Math.random() * 96))}
    </span>
  ))

  return (
    <Wrapper>
      <ParticleCanvas>{particles}</ParticleCanvas>
      <Card>
        <Logo>NEXURA</Logo>
        <Subtitle>AI Kiberxavfsizlik Skaneri</Subtitle>
        <form onSubmit={e => { e.preventDefault(); handleSubmit() }}>
          <InputWrapper>
            <StyledInput
              type="password"
              placeholder="🔑 Kirish kalitini kiriting..."
              value={input}
              onChange={e => setInput(e.target.value)}
              $shake={shakeInput}
              $flash={flashInput}
              disabled={!!(blockedUntil && Date.now() < blockedUntil)}
              autoFocus
            />
          </InputWrapper>
          <LoginButton type="submit" disabled={!!(blockedUntil && Date.now() < blockedUntil) || !input.trim()}>
            TIZIMGA KIRISH
          </LoginButton>
        </form>
        {error && <ErrorText>{error}</ErrorText>}
        {countdown > 0 && (
          <BlockText>
            ⚠ Bloklangan! {Math.floor(countdown / 60)}:{(countdown % 60).toString().padStart(2, '0')}
          </BlockText>
        )}
        <Hint>3 marta xato = 5 daqiqa bloklanish</Hint>
      </Card>
    </Wrapper>
  )
}
