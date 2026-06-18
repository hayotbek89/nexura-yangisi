import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import styled from 'styled-components'
import { useAudioSystem } from '../hooks/useAudioSystem'
import BackgroundPattern from './BackgroundPattern'

const CORRECT_KEY = 'nexura-shadow-9685'

const Wrapper = styled(motion.div)`
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  overflow: hidden;
`

const Container = styled.div`
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  width: 100%;
  max-width: 420px;
  padding: 0 24px;
`

const Chip = styled(motion.div)`
  width: 100px;
  height: 100px;
  position: relative;
`

const ChipBase = styled(motion.div)`
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border: 2px solid #27c39f;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 0 30px rgba(39, 195, 159, 0.3), inset 0 0 30px rgba(39, 195, 159, 0.1);
`

const ChipPins = styled.div`
  position: absolute;
  inset: -8px;
`

const Pin = styled(motion.div)`
  position: absolute;
  width: 6px;
  height: 14px;
  background: ${p => p.$active ? '#27c39f' : '#334155'};
  border-radius: 2px;
  box-shadow: ${p => p.$active ? '0 0 8px #27c39f' : 'none'};
`

const ChipIcon = styled.div`
  font-size: 36px;
  font-weight: 900;
  color: #27c39f;
  font-family: monospace;
  letter-spacing: -2px;
`

const GlitchTitle = styled(motion.h1)`
  font-size: 28px;
  font-weight: 800;
  color: var(--primary);
  text-align: center;
  font-family: monospace;
  letter-spacing: 4px;
  text-transform: uppercase;
`

const Subtitle = styled(motion.p)`
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  font-family: monospace;
`

const Input = styled(motion.input)`
  width: 100%;
  padding: 14px 18px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 16px;
  font-family: monospace;
  text-align: center;
  letter-spacing: 3px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus {
    border-color: var(--primary);
    box-shadow: 0 0 20px rgba(24, 95, 165, 0.2);
  }

  &::placeholder {
    letter-spacing: 1px;
    color: var(--text-muted);
  }
`

const StatusText = styled(motion.div)`
  font-size: 12px;
  font-family: monospace;
  letter-spacing: 1px;
  color: ${p => p.$color || 'var(--text-muted)'};
  min-height: 20px;
`

const ScanLine = styled(motion.div)`
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--primary), transparent);
  opacity: 0.5;
  pointer-events: none;
`

const pins = [
  { top: -6, left: '20%' }, { top: -6, left: '40%' }, { top: -6, left: '60%' }, { top: -6, left: '80%' },
  { bottom: -6, left: '20%' }, { bottom: -6, left: '40%' }, { bottom: -6, left: '60%' }, { bottom: -6, left: '80%' },
]

function scramble(text) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
  return text.split('').map(c => {
    if (c === ' ') return ' '
    return Math.random() > 0.7 ? chars[Math.floor(Math.random() * chars.length)] : c
  }).join('')
}

export default function AccessKeyGate({ onAccess }) {
  const [key, setKey] = useState('')
  const [state, setState] = useState('idle')
  const [statusText, setStatusText] = useState('')
  const [errorCount, setErrorCount] = useState(0)
  const [blockedUntil, setBlockedUntil] = useState(null)
  const [displayTitle, setDisplayTitle] = useState('NEXURA')
  const sounds = useAudioSystem()

  useEffect(() => {
    const stored = localStorage.getItem('nx_blocked_until')
    if (stored && Date.now() < parseInt(stored)) {
      setBlockedUntil(parseInt(stored))
    }
  }, [])

  useEffect(() => {
    if (state === 'idle') {
      const interval = setInterval(() => {
        setDisplayTitle(scramble('NEXURA'))
      }, 80)
      setTimeout(() => {
        clearInterval(interval)
        setDisplayTitle('NEXURA')
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [state])

  useEffect(() => {
    if (!blockedUntil) return
    if (Date.now() >= blockedUntil) {
      setBlockedUntil(null)
      setErrorCount(0)
      localStorage.removeItem('nx_blocked_until')
      localStorage.removeItem('nx_blocked')
      localStorage.removeItem('nexura_attempts')
      return
    }
    const timer = setInterval(() => {
      if (Date.now() >= blockedUntil) {
        setBlockedUntil(null)
        setErrorCount(0)
        localStorage.removeItem('nx_blocked_until')
        localStorage.removeItem('nx_blocked')
        localStorage.removeItem('nexura_attempts')
      }
    }, 1000)
    return () => clearInterval(timer)
  }, [blockedUntil])

  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault()
    if (blockedUntil) return

    const trimmed = key.trim()
    if (!trimmed) return

    setState('validating')
    setStatusText('')
    sounds.validatsiya()

    await new Promise(r => setTimeout(r, 1200))

    if (trimmed === CORRECT_KEY) {
      sounds.ruxsat()
      setStatusText('ACCESS GRANTED')
      setState('success')
      localStorage.removeItem('nx_blocked_until')
      localStorage.removeItem('nx_blocked')
      localStorage.removeItem('nexura_attempts')
      await new Promise(r => setTimeout(r, 1500))
      onAccess()
    } else {
      sounds.radEtildi()
      setStatusText('ACCESS DENIED')
      setState('error')
      const attempts = parseInt(localStorage.getItem('nexura_attempts') || '0') + 1
      localStorage.setItem('nexura_attempts', attempts.toString())
      setErrorCount(attempts)
      if (attempts >= 3) {
        const until = Date.now() + 5 * 60 * 1000
        localStorage.setItem('nx_blocked_until', until.toString())
        localStorage.setItem('nx_blocked', 'true')
        setBlockedUntil(until)
      }
      await new Promise(r => setTimeout(r, 2000))
      setKey('')
      setState('idle')
      setStatusText('')
    }
  }, [key, blockedUntil, sounds, onAccess])

  const blockedLeft = blockedUntil ? Math.max(0, Math.floor((blockedUntil - Date.now()) / 1000)) : 0

  return (
    <AnimatePresence>
      <Wrapper
        initial={{ opacity: 1 }}
        exit={{ opacity: 0, scale: 1.1 }}
        transition={{ duration: 0.6, ease: 'easeInOut' }}
      >
        <BackgroundPattern />
        <ScanLine
          animate={{ top: ['-10%', '110%'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        />
        <Container>
          <Chip>
            <ChipPins>
              {pins.map((p, i) => (
                <Pin
                  key={i}
                  style={p}
                  $active={state === 'success'}
                  animate={state === 'validating' ? {
                    opacity: [0.3, 1, 0.3],
                    transition: { duration: 0.5, repeat: Infinity, delay: i * 0.05 }
                  } : state === 'success' ? {
                    opacity: 1,
                    boxShadow: ['0 0 0px #27c39f', '0 0 12px #27c39f', '0 0 0px #27c39f'],
                    transition: { duration: 1, repeat: Infinity }
                  } : {}}
                />
              ))}
            </ChipPins>
            <ChipBase
              animate={state === 'validating' ? {
                boxShadow: ['0 0 30px rgba(39,195,159,0.3)', '0 0 60px rgba(39,195,159,0.6)', '0 0 30px rgba(39,195,159,0.3)'],
                transition: { duration: 1, repeat: Infinity }
              } : state === 'success' ? {
                boxShadow: ['0 0 30px rgba(39,195,159,0.3)', '0 0 80px rgba(39,195,159,0.8)', '0 0 30px rgba(39,195,159,0.3)'],
                transition: { duration: 0.8, repeat: Infinity }
              } : state === 'error' ? {
                boxShadow: ['0 0 30px rgba(239,68,68,0.3)', '0 0 60px rgba(239,68,68,0.6)', '0 0 30px rgba(239,68,68,0.3)'],
                borderColor: ['#ef4444', '#ef4444'],
                transition: { duration: 0.3, repeat: 3 }
              } : {}}
            >
              <ChipIcon>
                {state === 'success' ? 'OK' : state === 'error' ? '!!' : 'NX'}
              </ChipIcon>
            </ChipBase>
          </Chip>

          <div style={{ textAlign: 'center' }}>
            <GlitchTitle
              animate={state === 'error' ? {
                x: [0, -4, 4, -2, 2, 0],
                transition: { duration: 0.3 }
              } : {}}
            >
              {displayTitle}
            </GlitchTitle>
            <Subtitle
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              KIBERXAVFSIZLIK SKANERI
            </Subtitle>
          </div>

          {blockedUntil ? (
            <StatusText $color="#ef4444" style={{ fontSize: 14 }}>
              BLOKLANGAN — {Math.floor(blockedLeft / 60)}:{(blockedLeft % 60).toString().padStart(2, '0')}
            </StatusText>
          ) : (
            <form onSubmit={handleSubmit} style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Input
                type="password"
                value={key}
                onChange={e => { setKey(e.target.value); sounds.keyPress() }}
                placeholder="access key"
                disabled={state === 'validating'}
                animate={state === 'error' ? {
                  x: [0, -6, 6, -4, 4, 0],
                  borderColor: ['#ef4444', '#ef4444', 'var(--border)'],
                  transition: { duration: 0.4 }
                } : {}}
                autoFocus
              />
              <motion.button
                type="submit"
                disabled={state === 'validating' || !key.trim()}
                style={{
                  padding: '12px 24px',
                  background: state === 'validating' ? 'var(--bg-input)' : 'var(--primary)',
                  border: '1px solid var(--primary)',
                  borderRadius: 'var(--radius)',
                  color: '#fff',
                  fontFamily: 'monospace',
                  fontSize: 13,
                  letterSpacing: 2,
                  cursor: state === 'validating' ? 'not-allowed' : 'pointer',
                  textTransform: 'uppercase',
                  opacity: !key.trim() ? 0.5 : 1,
                }}
                whileHover={key.trim() && state !== 'validating' ? { scale: 1.02 } : {}}
                whileTap={key.trim() && state !== 'validating' ? { scale: 0.98 } : {}}
              >
                {state === 'validating' ? 'Tekshirilmoqda...' : 'Kirish'}
              </motion.button>
            </form>
          )}

          <StatusText $color={state === 'success' ? '#22c55e' : state === 'error' ? '#ef4444' : 'var(--text-muted)'}>
            {statusText || (errorCount > 0 ? `${3 - errorCount} ta urinish qoldi` : '')}
          </StatusText>
        </Container>
      </Wrapper>
    </AnimatePresence>
  )
}
