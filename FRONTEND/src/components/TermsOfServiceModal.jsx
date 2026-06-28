import React, { useState } from 'react'
import styled from 'styled-components'
import { motion, AnimatePresence } from 'framer-motion'
import { apiFetch } from '../api'

const Overlay = styled(motion.div)`
  position: fixed;
  inset: 0;
  z-index: 8000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
`

const Modal = styled(motion.div)`
  background: var(--bg-card);
  border: 1px solid var(--primary);
  border-radius: var(--radius);
  max-width: 560px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  padding: 32px;
  box-shadow: 0 0 40px rgba(24, 95, 165, 0.2);
`

const Title = styled.h2`
  font-size: 20px;
  font-family: monospace;
  letter-spacing: 2px;
  color: var(--primary);
  margin-bottom: 20px;
  text-transform: uppercase;
`

const Body = styled.div`
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  margin-bottom: 24px;
`

const Rule = styled.p`
  padding: 8px 12px;
  margin-bottom: 8px;
  border-left: 2px solid var(--primary);
  background: rgba(24, 95, 165, 0.05);
  border-radius: 0 var(--radius) var(--radius) 0;
`

const Label = styled.label`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 24px;
  cursor: pointer;
  line-height: 1.5;
`

const Checkbox = styled.input`
  margin-top: 2px;
  accent-color: var(--primary);
  width: 16px;
  height: 16px;
`

const ButtonRow = styled.div`
  display: flex;
  gap: 12px;
  justify-content: flex-end;
`

const Button = styled(motion.button)`
  padding: 10px 20px;
  border-radius: var(--radius);
  font-family: monospace;
  font-size: 13px;
  letter-spacing: 1px;
  cursor: ${p => p.disabled ? 'not-allowed' : 'pointer'};
  opacity: ${p => p.disabled ? 0.4 : 1};
  border: 1px solid ${p => p.$primary ? 'var(--primary)' : 'var(--border)'};
  background: ${p => p.$primary ? 'var(--primary)' : 'transparent'};
  color: ${p => p.$primary ? '#fff' : 'var(--text)'};
`

export default function TermsOfServiceModal({ onAccept }) {
  const [checked, setChecked] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleAccept = async () => {
    if (!checked || loading) return
    setLoading(true)
    try {
      const res = await apiFetch('/api/tos/accept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_identifier: 'default', tos_version: '1.0' }),
      })
      onAccept()
    } catch {
      onAccept()
    }
    setLoading(false)
  }

  return (
    <AnimatePresence>
      <Overlay
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <Modal
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        >
          <Title>Foydalanish Shartlari</Title>
          <Body>
            <p style={{ marginBottom: 16, fontWeight: 600 }}>
              NEXURA — kiberxavfsizlik skaneri. Davom etishdan oldin:
            </p>
            <Rule>
              1. Men faqat O'ZIMGA TEGISHLI domenlarni yoki men uchun
              YOZMA RUXSAT berilgan tizimlarni tekshiraman.
            </Rule>
            <Rule>
              2. Men ruxsatsiz tizimlarga zarar yetkazish yoki noqonuniy
              kirish uchun bu vositadan FOYDALANMAYMAN.
            </Rule>
            <Rule>
              3. Men barcha topilgan zaifliklardan faqat QONUNIY va ETIK
              maqsadlarda foydalanaman.
            </Rule>
            <Rule>
              4. Men bu shartlarni buzsam, to'liq HUQUQIY JAVOBGARLIKNI
              o'z zimmamga olaman.
            </Rule>
          </Body>
          <Label>
            <Checkbox
              type="checkbox"
              checked={checked}
              onChange={e => setChecked(e.target.checked)}
            />
            <span>Yuqoridagi shartlarni o'qib chiqdim va qabul qilaman</span>
          </Label>
          <ButtonRow>
            <Button
              $primary
              disabled={!checked || loading}
              onClick={handleAccept}
              whileHover={checked && !loading ? { scale: 1.02 } : {}}
              whileTap={checked && !loading ? { scale: 0.98 } : {}}
            >
              {loading ? 'Yuklanmoqda...' : 'ROZIMAN, DAVOM ETAMAN'}
            </Button>
          </ButtonRow>
        </Modal>
      </Overlay>
    </AnimatePresence>
  )
}
