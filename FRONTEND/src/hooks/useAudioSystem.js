import { useCallback, useRef } from 'react'

const KEY = 'nexura_sound_enabled'

export function useAudioSystem() {
  const ctxRef = useRef(null)

  const getCtx = useCallback(() => {
    if (!ctxRef.current) {
      ctxRef.current = new (window.AudioContext || window.webkitAudioContext)()
    }
    if (ctxRef.current.state === 'suspended') {
      ctxRef.current.resume()
    }
    return ctxRef.current
  }, [])

  const playTone = useCallback((freq, duration, type = 'sine', gain = 0.15) => {
    if (localStorage.getItem(KEY) === 'false') return
    try {
      const ctx = getCtx()
      const osc = ctx.createOscillator()
      const g = ctx.createGain()
      osc.type = type
      osc.frequency.setValueAtTime(freq, ctx.currentTime)
      g.gain.setValueAtTime(gain, ctx.currentTime)
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)
      osc.connect(g).connect(ctx.destination)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + duration)
    } catch {}
  }, [getCtx])

  const playNoise = useCallback((duration, gain = 0.08) => {
    if (localStorage.getItem(KEY) === 'false') return
    try {
      const ctx = getCtx()
      const bufferSize = ctx.sampleRate * duration
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate)
      const data = buffer.getChannelData(0)
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1
      }
      const source = ctx.createBufferSource()
      source.buffer = buffer
      const g = ctx.createGain()
      g.gain.setValueAtTime(gain, ctx.currentTime)
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)
      source.connect(g).connect(ctx.destination)
      source.start()
    } catch {}
  }, [getCtx])

  const sounds = {
    keyPress: () => {
      playTone(800, 0.05, 'square', 0.08)
    },
    validatsiya: () => {
      playNoise(0.15, 0.06)
      const ctx = getCtx()
      if (!ctx) return
      const now = ctx.currentTime
      for (let i = 0; i < 4; i++) {
        const osc = ctx.createOscillator()
        const g = ctx.createGain()
        osc.type = 'sawtooth'
        osc.frequency.setValueAtTime(300 + i * 200, now + i * 0.08)
        g.gain.setValueAtTime(0.04, now + i * 0.08)
        g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.06)
        osc.connect(g).connect(ctx.destination)
        osc.start(now + i * 0.08)
        osc.stop(now + i * 0.08 + 0.06)
      }
    },
    ruxsat: () => {
      const ctx = getCtx()
      if (!ctx) return
      const now = ctx.currentTime
      const notes = [523, 659, 784, 1047]
      notes.forEach((freq, i) => {
        const osc = ctx.createOscillator()
        const g = ctx.createGain()
        osc.type = 'sine'
        osc.frequency.setValueAtTime(freq, now + i * 0.12)
        g.gain.setValueAtTime(0.12, now + i * 0.12)
        g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.12 + 0.3)
        osc.connect(g).connect(ctx.destination)
        osc.start(now + i * 0.12)
        osc.stop(now + i * 0.12 + 0.3)
      })
    },
    radEtildi: () => {
      const ctx = getCtx()
      if (!ctx) return
      const now = ctx.currentTime
      const osc = ctx.createOscillator()
      const g = ctx.createGain()
      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(150, now)
      osc.frequency.linearRampToValueAtTime(80, now + 0.4)
      g.gain.setValueAtTime(0.15, now)
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.4)
      osc.connect(g).connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.5)
      playNoise(0.3, 0.1)
    },
    xato: () => {
      playTone(200, 0.15, 'square', 0.12)
      setTimeout(() => playTone(180, 0.2, 'square', 0.1), 150)
    },
  }

  return sounds
}

export function isSoundEnabled() {
  return localStorage.getItem(KEY) !== 'false'
}

export function toggleSound(val) {
  localStorage.setItem(KEY, val ? 'true' : 'false')
}
