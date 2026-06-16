import { useState, useEffect, useRef } from "react";
import styled, { keyframes } from "styled-components";

const glitch = keyframes`
  0%, 90%, 100% { text-shadow: 2px 0 #27c39f, -2px 0 #2761c3; }
  92% { text-shadow: -3px 0 #27c39f, 3px 0 #2761c3; }
  94% { text-shadow: 3px 0 #27c39f, -3px 0 #2761c3; }
  96% { text-shadow: -2px 0 #27c39f, 2px 0 #2761c3; }
`;

const scan = keyframes`
  0% { top: 0; }
  100% { top: 100%; }
`;

const shake = keyframes`
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-6px); }
  75% { transform: translateX(6px); }
`;

const blink = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
`;

const Wrap = styled.div`
  position: fixed;
  inset: 0;
  background: #0a0e1a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Share Tech Mono', monospace;
  overflow: hidden;
  z-index: 9999;
`;

const ScanLine = styled.div`
  position: absolute;
  left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(39,195,159,0.3), transparent);
  animation: ${scan} 4s linear infinite;
  pointer-events: none;
`;

const Card = styled.div`
  position: relative;
  z-index: 10;
  width: 340px;
  padding: 40px 32px;
  background: rgba(10, 14, 26, 0.95);
  border: 1px solid #2761c3;
  clip-path: polygon(
    12px 0%, calc(100% - 12px) 0%,
    100% 12px, 100% calc(100% - 12px),
    calc(100% - 12px) 100%, 12px 100%,
    0% calc(100% - 12px), 0% 12px
  );
  box-shadow: 0 0 40px rgba(39, 97, 195, 0.15);
`;

const Corner = styled.div`
  position: absolute;
  width: 8px; height: 8px;
  background: #27c39f;
  transform: rotate(45deg);
  ${p => p.tl && 'top: -4px; left: -4px;'}
  ${p => p.tr && 'top: -4px; right: -4px;'}
  ${p => p.bl && 'bottom: -4px; left: -4px;'}
  ${p => p.br && 'bottom: -4px; right: -4px;'}
`;

const LogoText = styled.div`
  font-size: 32px;
  font-weight: 700;
  color: #27c39f;
  letter-spacing: 8px;
  animation: ${glitch} 3s infinite;
  text-align: center;
`;

const LogoSub = styled.div`
  font-size: 10px;
  color: #2761c3;
  letter-spacing: 2px;
  margin-top: 4px;
  text-align: center;
`;

const Cursor = styled.span`
  display: inline-block;
  width: 8px; height: 14px;
  background: #27c39f;
  animation: ${blink} 1s infinite;
  vertical-align: middle;
  margin-left: 2px;
`;

const Divider = styled.hr`
  border: none;
  border-top: 1px solid #2761c3;
  margin: 20px 0;
  opacity: 0.4;
`;

const Label = styled.span`
  font-size: 11px;
  color: #27c39f;
  letter-spacing: 2px;
  display: block;
  margin-bottom: 8px;
`;

const InputWrap = styled.div`
  position: relative;
  margin-bottom: 20px;
`;

const InputIcon = styled.span`
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #2761c3;
  font-size: 16px;
`;

const Input = styled.input`
  width: 100%;
  background: rgba(39, 97, 195, 0.08);
  border: 1px solid #2761c3;
  color: #ddebf0;
  font-family: 'Share Tech Mono', monospace;
  font-size: 14px;
  padding: 12px 16px 12px 36px;
  outline: none;
  box-sizing: border-box;
  clip-path: polygon(
    6px 0%, calc(100% - 6px) 0%,
    100% 6px, 100% calc(100% - 6px),
    calc(100% - 6px) 100%, 6px 100%,
    0% calc(100% - 6px), 0% 6px
  );
  transition: border-color 0.2s, box-shadow 0.2s;
  &:focus {
    border-color: #27c39f;
    box-shadow: 0 0 12px rgba(39,195,159,0.2);
  }
  &::placeholder { color: rgba(221,235,240,0.3); }
`;

const Btn = styled.button`
  width: 100%;
  background: transparent;
  border: 1px solid #27c39f;
  color: #27c39f;
  font-family: 'Share Tech Mono', monospace;
  font-size: 13px;
  letter-spacing: 3px;
  padding: 14px;
  cursor: pointer;
  clip-path: polygon(
    8px 0%, calc(100% - 8px) 0%,
    100% 8px, 100% calc(100% - 8px),
    calc(100% - 8px) 100%, 8px 100%,
    0% calc(100% - 8px), 0% 8px
  );
  transition: all 0.2s;
  &:hover {
    background: rgba(39,195,159,0.1);
    box-shadow: 0 0 20px rgba(39,195,159,0.3);
  }
  &:active { transform: scale(0.98); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const Status = styled.div`
  height: 20px;
  text-align: center;
  font-size: 11px;
  letter-spacing: 1px;
  margin-bottom: 12px;
  color: ${p => p.error ? '#e74c3c' : '#27c39f'};
  animation: ${p => p.error ? shake : 'none'} 0.3s;
`;

const Warning = styled.div`
  margin-top: 16px;
  font-size: 10px;
  color: rgba(39,97,195,0.7);
  text-align: center;
  letter-spacing: 1px;
  span { color: #e74c3c; }
`;

const Footer = styled.div`
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  font-size: 9px;
  color: rgba(39,97,195,0.5);
  letter-spacing: 1px;
`;

const Canvas = styled.canvas`
  position: absolute;
  inset: 0;
  pointer-events: none;
`;

const SECRET = 'nexura-shadow-9685';
const MAX_ATTEMPTS = 3;
const BLOCK_DURATION = 5 * 60 * 1000;

export default function Login({ onLogin }) {
  const [value, setValue] = useState('');
  const [status, setStatus] = useState({ text: '', error: false });
  const [attempts, setAttempts] = useState(0);
  const [blocked, setBlocked] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const canvasRef = useRef(null);

  useEffect(() => {
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
  }, []);

  useEffect(() => {
    const blockedAt = localStorage.getItem('nx_blocked');
    if (blockedAt) {
      const remaining = parseInt(blockedAt) + BLOCK_DURATION - Date.now();
      if (remaining > 0) {
        setBlocked(true);
        setCountdown(Math.ceil(remaining / 1000));
      } else {
        localStorage.removeItem('nx_blocked');
      }
    }
  }, []);

  useEffect(() => {
    if (!countdown) return;
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          setBlocked(false);
          localStorage.removeItem('nx_blocked');
          setStatus({ text: '', error: false });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const wrap = canvas.parentElement;
    canvas.width = wrap.offsetWidth;
    canvas.height = wrap.offsetHeight;
    const particles = Array.from({ length: 50 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedY: -(Math.random() * 0.5 + 0.2),
      opacity: Math.random() * 0.5 + 0.1,
      color: Math.random() > 0.5 ? '#27c39f' : '#2761c3',
    }));
    let raf;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.opacity;
        ctx.fill();
        p.y += p.speedY;
        if (p.y < 0) { p.y = canvas.height; p.x = Math.random() * canvas.width; }
      });
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(raf);
  }, []);

  const handleLogin = () => {
    if (blocked) return;
    if (value === SECRET) {
      setStatus({ text: '✓ KIRISH TASDIQLANDI', error: false });
      localStorage.setItem('nexura_auth', 'true');
      setTimeout(() => onLogin(), 800);
    } else {
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);
      if (newAttempts >= MAX_ATTEMPTS) {
        localStorage.setItem('nx_blocked', Date.now().toString());
        setBlocked(true);
        setCountdown(300);
        setStatus({ text: '⛔ 5 DAQIQA BLOKLANDINGIZ', error: true });
      } else {
        setStatus({ text: `✗ KALIT NOTO'G'RI (${MAX_ATTEMPTS - newAttempts} URINISH QOLDI)`, error: true });
      }
      setValue('');
    }
  };

  const mins = String(Math.floor(countdown / 60)).padStart(2, '0');
  const secs = String(countdown % 60).padStart(2, '0');

  return (
    <Wrap>
      <Canvas ref={canvasRef} />
      <ScanLine />
      <Card>
        <Corner tl /><Corner tr /><Corner bl /><Corner br />
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <LogoText>NEXURA<Cursor /></LogoText>
          <LogoSub>AI KIBERXAVFSIZLIK SKANERI</LogoSub>
        </div>
        <Divider />
        <Status error={status.error}>
          {blocked ? `BLOK: ${mins}:${secs} QOLDI` : status.text}
        </Status>
        <div className="relative w-full mx-auto font-mono">
          <div className="relative p-4 bg-black border-2 border-green-400 rounded-lg shadow-lg overflow-hidden">
            <div className="absolute top-0 left-0 w-6 h-1 bg-green-400" />
            <div className="absolute top-0 left-0 w-1 h-6 bg-green-400" />
            <div className="absolute top-0 right-0 w-6 h-1 bg-green-400" />
            <div className="absolute top-0 right-0 w-1 h-6 bg-green-400" />
            <div className="absolute bottom-0 left-0 w-6 h-1 bg-green-400" />
            <div className="absolute bottom-0 left-0 w-1 h-6 bg-green-400" />
            <div className="absolute bottom-0 right-0 w-6 h-1 bg-green-400" />
            <div className="absolute bottom-0 right-0 w-1 h-6 bg-green-400" />
            <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-transparent via-green-900/20 to-transparent" />
            <label className="mb-3 text-green-400 text-sm tracking-wider flex items-center">
              <span className="mr-2 text-green-600">➜</span>
              <span className="text-green-300 font-bold">KIRISH KALITI</span>
              <span className="ml-2 opacity-75 animate-pulse">▋</span>
            </label>
            <div className="relative">
              <input
                className="w-full bg-transparent text-green-300 text-base border-2 border-green-500 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-green-600 placeholder-green-600/60 pr-10"
                placeholder="➤ KIRISH KALITINI KIRITING"
                type="password"
                value={value}
                onChange={e => setValue(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                maxLength={32}
                disabled={blocked}
              />
              <svg stroke="currentColor" viewBox="0 0 24 24" fill="none"
                className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-green-500">
                <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              </svg>
            </div>
            <div className="absolute top-0 right-12 w-px h-4 bg-green-500/50" />
            <div className="absolute top-0 right-16 w-px h-6 bg-green-500/30" />
            <div className="absolute top-0 right-20 w-px h-2 bg-green-500/70" />
            <div className="absolute bottom-0 left-12 w-px h-4 bg-green-500/50" />
            <div className="absolute bottom-0 left-16 w-px h-6 bg-green-500/30" />
            <div className="absolute bottom-0 left-20 w-px h-2 bg-green-500/70" />
          </div>
        </div>
        <Btn onClick={handleLogin} disabled={blocked}>
          ⚡ TIZIMGA KIRISH
        </Btn>
        <Footer>
          <span>URINISH: {attempts}/{MAX_ATTEMPTS}</span>
          <span>v2.0.0</span>
        </Footer>
      </Card>
    </Wrap>
  );
}
