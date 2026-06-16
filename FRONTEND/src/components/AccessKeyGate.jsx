import React, { useState, useEffect, useRef, useCallback } from 'react'
import styled, { keyframes } from 'styled-components'
import { AnimatePresence, motion } from 'framer-motion'

const SECRET_KEY = 'nexura-shadow-9685'
const MAX_ATTEMPTS = 3
const BLOCK_DURATION = 5 * 60 * 1000

const shake = keyframes`
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-8px) rotate(-0.5deg); }
  40% { transform: translateX(8px) rotate(0.5deg); }
  60% { transform: translateX(-5px) rotate(-0.3deg); }
  80% { transform: translateX(5px) rotate(0.3deg); }
`

const pulse = keyframes`
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
`

const blink = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
`

const ambientFlow = keyframes`
  to { stroke-dashoffset: 0; }
`

const Wrapper = styled.div`
  position: fixed;
  inset: 0;
  background: #0a0e1a;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
  overflow: hidden;
`

const ChipContainer = styled(motion.div)`
  width: 90%;
  max-width: 700px;
`

const StyledSvg = styled.svg`
  display: block;
  width: 100%;
  height: auto;

  .trace-bg {
    stroke: #1a1a2e;
    stroke-width: 1.8;
    fill: none;
  }

  .trace-flow {
    stroke-width: 1.8;
    fill: none;
    stroke-dasharray: 40 400;
    stroke-dashoffset: 438;
  }

  .trace-flow.idle {
    animation: ${ambientFlow} 6s cubic-bezier(0.5, 0, 0.9, 1) infinite;
  }

  .trace-flow.validating {
    animation: ${ambientFlow} 0.6s cubic-bezier(0.5, 0, 0.9, 1) infinite;
  }

  .trace-flow.success {
    animation: ${ambientFlow} 0.3s cubic-bezier(0.5, 0, 0.9, 1) forwards;
  }
`

const ChipBody = styled.rect`
  fill: ${({ $state }) =>
    $state === 'error' ? '#1a0a0a' :
    $state === 'success' ? '#0a1a0a' :
    '#0f0f1a'};
  stroke: ${({ $state }) =>
    $state === 'error' ? '#ff3344' :
    $state === 'success' ? '#00ff88' :
    $state === 'validating' ? '#00aaff' :
    '#222'};
  transition: fill 0.3s, stroke 0.3s;
  filter: drop-shadow(0 0 ${({ $state }) =>
    $state === 'success' ? '20px rgba(0,255,136,0.4)' :
    $state === 'validating' ? '12px rgba(0,170,255,0.3)' :
    $state === 'error' ? '16px rgba(255,51,68,0.4)' :
    '6px rgba(0,0,0,0.8)'});
`

const ChipText = styled.text`
  font-family: 'Share Tech Mono', 'Courier New', monospace;
  font-weight: bold;
  letter-spacing: 2px;
  fill: ${({ $state }) =>
    $state === 'error' ? '#ff3344' :
    $state === 'success' ? '#00ff88' :
    $state === 'validating' ? '#00aaff' :
    '#888'};
  transition: fill 0.3s;
  text-anchor: middle;
  dominant-baseline: central;
`

const InputGroup = styled.foreignObject`
  width: 120px;
  height: 32px;
  overflow: visible;
`

const StyledInput = styled.input`
  width: 100%;
  height: 100%;
  background: rgba(0, 170, 255, 0.06);
  border: 1px solid ${({ $state }) =>
    $state === 'error' ? '#ff3344' :
    $state === 'success' ? '#00ff88' :
    '#00aaff'};
  color: ${({ $state }) =>
    $state === 'error' ? '#ff3344' :
    $state === 'success' ? '#00ff88' :
    '#ddebf0'};
  font-family: 'Share Tech Mono', 'Courier New', monospace;
  font-size: 11px;
  text-align: center;
  outline: none;
  padding: 0 4px;
  box-sizing: border-box;
  transition: border-color 0.3s, color 0.3s;

  &::placeholder {
    color: rgba(255, 255, 255, 0.15);
    font-size: 9px;
  }
`

const CursorSpan = styled.tspan`
  animation: ${blink} 1s infinite;
  fill: ${({ $state }) =>
    $state === 'success' ? '#00ff88' :
    $state === 'error' ? '#ff3344' :
    '#00aaff'};
`

const StatusBar = styled.div`
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'Share Tech Mono', monospace;
  font-size: 11px;
  letter-spacing: 3px;
  color: ${({ $state }) =>
    $state === 'error' ? '#ff3344' :
    $state === 'success' ? '#00ff88' :
    $state === 'validating' ? '#00aaff' :
    'rgba(255,255,255,0.2)'};
  text-align: center;
  transition: color 0.3s;
`

const Overlay = styled(motion.div)`
  position: fixed;
  inset: 0;
  background: #0a0e1a;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
`

function getTraceColor(color) {
  const map = {
    purple: '#9900ff',
    blue: '#00ccff',
    yellow: '#ffea00',
    green: '#00ff15',
    red: '#ff3300',
  }
  return map[color] || '#00ccff'
}

function getTraceStyle(state, color) {
  const base = { stroke: getTraceColor(color), filter: `drop-shadow(0 0 6px ${getTraceColor(color)})` }
  if (state === 'idle') {
    return { ...base, opacity: 0.15 }
  }
  if (state === 'error') {
    return { ...base, stroke: '#ff3344', filter: 'drop-shadow(0 0 8px #ff3344)' }
  }
  return base
}

export default function AccessKeyGate({ children, onAccessGranted, secretKey = SECRET_KEY }) {
  const [state, setState] = useState('idle')
  const [value, setValue] = useState('')
  const [attempts, setAttempts] = useState(0)
  const [blockedUntil, setBlockedUntil] = useState(0)
  const [countdown, setCountdown] = useState(0)
  const [showApp, setShowApp] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    const stored = localStorage.getItem('nx_blocked')
    if (stored) {
      const remaining = parseInt(stored) + BLOCK_DURATION - Date.now()
      if (remaining > 0) {
        setBlockedUntil(parseInt(stored))
        setCountdown(Math.ceil(remaining / 1000))
      } else {
        localStorage.removeItem('nx_blocked')
        localStorage.removeItem('nx_attempts')
      }
    }
  }, [])

  useEffect(() => {
    if (!countdown) return
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          setBlockedUntil(0)
          localStorage.removeItem('nx_blocked')
          localStorage.removeItem('nx_attempts')
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [countdown])

  const handleSubmit = useCallback(() => {
    if (blockedUntil && Date.now() < blockedUntil) return
    if (!value.trim()) return

    setState('validating')

    setTimeout(() => {
      if (value === secretKey) {
        setState('success')
        localStorage.setItem('nexura_auth', 'true')
        setTimeout(() => {
          setShowApp(true)
          if (onAccessGranted) onAccessGranted()
        }, 1200)
      } else {
        setState('error')
        const newAttempts = attempts + 1
        setAttempts(newAttempts)

        if (newAttempts >= MAX_ATTEMPTS) {
          const until = Date.now() + BLOCK_DURATION
          localStorage.setItem('nx_blocked', String(until))
          setBlockedUntil(until)
          setCountdown(300)
        }

        setTimeout(() => {
          setState('idle')
          setValue('')
        }, 1800)
      }
    }, 1500)
  }, [value, secretKey, blockedUntil, attempts, onAccessGranted])

  const traces = [
    { d: 'M100 100 H200 V210 H326', color: 'purple' },
    { d: 'M80 180 H180 V230 H326', color: 'blue' },
    { d: 'M60 260 H150 V250 H326', color: 'yellow' },
    { d: 'M100 350 H200 V270 H326', color: 'green' },
    { d: 'M700 90 H560 V210 H474', color: 'blue' },
    { d: 'M740 160 H580 V230 H474', color: 'green' },
    { d: 'M720 250 H590 V250 H474', color: 'red' },
    { d: 'M680 340 H570 V270 H474', color: 'yellow' },
  ]

  const statusText = () => {
    if (blockedUntil && Date.now() < blockedUntil) {
      const mins = String(Math.floor(countdown / 60)).padStart(2, '0')
      const secs = String(countdown % 60).padStart(2, '0')
      return `⛔ BLOKLANGAN  ${mins}:${secs}`
    }
    switch (state) {
      case 'validating':
        return '⬡ TEKSHIRILMOQDA...'
      case 'success':
        return '✓ KIRISH TASDIQLANDI'
      case 'error':
        return '✗ KIRISH RAD ETILDI'
      default:
        return attempts > 0 ? `URINISH ${attempts}/${MAX_ATTEMPTS}` : '▶ KALIT KIRITING'
    }
  }

  const chipText = () => {
    switch (state) {
      case 'validating':
        return 'VALIDATING'
      case 'success':
        return 'ACCESS GRANTED'
      case 'error':
        return 'ACCESS DENIED'
      default:
        return ''
    }
  }

  if (showApp) {
    return <>{children}</>
  }

  return (
    <Overlay
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.8, ease: 'easeInOut' }}
    >
      <AnimatePresence mode="wait">
        {state === 'success' ? (
          <ChipContainer
            key="success-chip"
            initial={{ scale: 1, opacity: 1 }}
            animate={{ scale: 3, opacity: 0 }}
            exit={{ scale: 4, opacity: 0 }}
            transition={{ duration: 1.2, ease: 'easeInOut' }}
            onAnimationComplete={() => setShowApp(true)}
          >
            <ChipSvg state={state} chipText={chipText()} traces={traces} inputValue={value} setInputValue={setValue} onSubmit={handleSubmit} blocked={blockedUntil > Date.now()} inputRef={inputRef} attempts={attempts} />
          </ChipContainer>
        ) : (
          <ChipContainer
            key="chip"
            animate={state === 'error' ? { x: [0, -8, 8, -5, 5, 0] } : { x: 0 }}
            transition={state === 'error' ? { duration: 0.4 } : { duration: 0.2 }}
          >
            <ChipSvg state={state} chipText={chipText()} traces={traces} inputValue={value} setInputValue={setValue} onSubmit={handleSubmit} blocked={blockedUntil > Date.now()} inputRef={inputRef} attempts={attempts} />
          </ChipContainer>
        )}
      </AnimatePresence>
      <StatusBar $state={state}>{statusText()}</StatusBar>
    </Overlay>
  )
}

function ChipSvg({ state, chipText, traces, inputValue, setInputValue, onSubmit, blocked, inputRef, attempts }) {
  const showInput = state === 'idle'

  return (
    <StyledSvg viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="chipGradient" x1={0} y1={0} x2={0} y2={1}>
          <stop offset="0%" stopColor="#2a2a3a" />
          <stop offset="100%" stopColor="#0f0f1a" />
        </linearGradient>
        <linearGradient id="textGradient" x1={0} y1={0} x2={0} y2={1}>
          <stop offset="0%" stopColor="#eeeeee" />
          <stop offset="100%" stopColor="#888888" />
        </linearGradient>
        <linearGradient id="pinGradient" x1={1} y1={0} x2={0} y2={0}>
          <stop offset="0%" stopColor="#bbbbbb" />
          <stop offset="50%" stopColor="#888888" />
          <stop offset="100%" stopColor="#555555" />
        </linearGradient>
      </defs>

      <g id="traces">
        {traces.map((t, i) => (
          <React.Fragment key={i}>
            <path d={t.d} className="trace-bg" />
            <path
              d={t.d}
              className={`trace-flow ${state}`}
              style={getTraceStyle(state, t.color)}
            />
          </React.Fragment>
        ))}
      </g>

      <ChipBody
        x={330} y={190} width={140} height={100} rx={20} ry={20}
        fill="url(#chipGradient)"
        strokeWidth={3}
        $state={state}
      />

      {/* pins left */}
      <g>
        {[205, 225, 245, 265].map((y) => (
          <rect key={y} x={322} y={y} width={8} height={10} fill="url(#pinGradient)" rx={2} />
        ))}
      </g>

      {/* pins right */}
      <g>
        {[205, 225, 245, 265].map((y) => (
          <rect key={y} x={470} y={y} width={8} height={10} fill="url(#pinGradient)" rx={2} />
        ))}
      </g>

      {/* center content */}
      {showInput ? (
        <InputGroup x={340} y={234} width={120} height={32}>
          <StyledInput
            ref={inputRef}
            type="password"
            placeholder="KEY"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !blocked && onSubmit()}
            disabled={blocked}
            autoFocus
            $state={state}
          />
        </InputGroup>
      ) : (
        <ChipText
          x={400} y={250}
          fontSize={chipText === 'ACCESS GRANTED' || chipText === 'ACCESS DENIED' ? 12 : 13}
          $state={state}
        >
          {chipText}
          {state === 'validating' && <CursorSpan $state={state}>|</CursorSpan>}
        </ChipText>
      )}

      {/* nodes */}
      {[
        [100, 100], [80, 180], [60, 260], [100, 350],
        [700, 90], [740, 160], [720, 250], [680, 340]
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r={5} fill={state === 'error' ? '#ff3344' : '#111'} />
      ))}
    </StyledSvg>
  )
}
