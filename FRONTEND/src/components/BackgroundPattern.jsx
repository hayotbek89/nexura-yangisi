import React from 'react'
import styled from 'styled-components'
import { useTheme } from '../contexts/ThemeContext'

const PatternContainer = styled.div`
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
`

const PatternInner = styled.div`
  width: 100%;
  height: 100%;
  background: linear-gradient(
      30deg,
      ${p => p.$color1} 12%,
      transparent 12.5%,
      transparent 87%,
      ${p => p.$color1} 87.5%,
      ${p => p.$color1}
    ),
    linear-gradient(
      150deg,
      ${p => p.$color1} 12%,
      transparent 12.5%,
      transparent 87%,
      ${p => p.$color1} 87.5%,
      ${p => p.$color1}
    ),
    linear-gradient(
      30deg,
      ${p => p.$color1} 12%,
      transparent 12.5%,
      transparent 87%,
      ${p => p.$color1} 87.5%,
      ${p => p.$color1}
    ),
    linear-gradient(
      150deg,
      ${p => p.$color1} 12%,
      transparent 12.5%,
      transparent 87%,
      ${p => p.$color1} 87.5%,
      ${p => p.$color1}
    ),
    linear-gradient(
      60deg,
      ${p => p.$color2} 25%,
      transparent 25.5%,
      transparent 75%,
      ${p => p.$color2} 75%,
      ${p => p.$color2}
    ),
    linear-gradient(
      60deg,
      ${p => p.$color2} 25%,
      transparent 25.5%,
      transparent 75%,
      ${p => p.$color2} 75%,
      ${p => p.$color2}
    );
  background-position:
    0 0, 0 0, 40px 70px, 40px 70px, 0 0, 40px 70px;
  background-color: ${p => p.$bg};
  background-size: 80px 140px;
`

export default function BackgroundPattern() {
  const { isDark } = useTheme()

  return (
    <PatternContainer>
      <PatternInner
        $bg={isDark ? '#0a0e1a' : '#f8fafc'}
        $color1={isDark ? '#111111' : '#e2e8f0'}
        $color2={isDark ? 'rgba(119,119,119,0.15)' : 'rgba(100,116,139,0.1)'}
      />
    </PatternContainer>
  )
}
