import styled, { keyframes } from 'styled-components';

const eyeLid = keyframes`
  0%, 40%, 45%, 100% { transform: translateY(0); }
  42.5% { transform: translateY(17.5px); }
`;

const eyes = keyframes`
  from { transform: translateY(112.5px); }
  to { transform: translateY(15px); }
`;

const pupil = keyframes`
  0%, 37.5%, 40%, 45%, 87.5%, 100% { 
    stroke-dashoffset: 0; transform: translate(0, 0); 
  }
  12.5%, 25%, 62.5%, 75% { transform: translate(-35px, 0); }
  42.5% { stroke-dashoffset: 35; transform: translate(0, 17.5px); }
`;

const mouthLeft = keyframes`
  from, 50% { stroke-dashoffset: -102; }
  to { stroke-dashoffset: 0; }
`;

const mouthRight = keyframes`
  from, 50% { stroke-dashoffset: 102; }
  to { stroke-dashoffset: 0; }
`;

const nose = keyframes`
  from { transform: translate(0, 0); }
  to { transform: translate(0, 22.5px); }
`;

const glitch = keyframes`
  0%, 90%, 100% { text-shadow: 2px 0 #e74c3c, -2px 0 #2761c3; }
  92% { text-shadow: -3px 0 #e74c3c, 3px 0 #2761c3; }
  94% { text-shadow: 3px 0 #e74c3c, -3px 0 #2761c3; }
`;

const scan = keyframes`
  0% { top: 0; }
  100% { top: 100%; }
`;

const Wrap = styled.div`
  position: fixed;
  inset: 0;
  background: #0a0e1a;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-family: 'Share Tech Mono', monospace;
  z-index: 9999;
  overflow: hidden;
`;

const ScanLine = styled.div`
  position: absolute;
  left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(231,76,60,0.3), transparent);
  animation: ${scan} 3s linear infinite;
  pointer-events: none;
`;

const FaceWrap = styled.div`
  color: #e74c3c;
  margin-bottom: 32px;

  svg {
    width: 160px;
  }

  .face__eyes,
  .face__eye-lid,
  .face__mouth-left,
  .face__mouth-right,
  .face__nose,
  .face__pupil {
    animation: ${eyes} 1s 0.3s forwards;
  }

  .face__eye-lid {
    animation: ${eyeLid} 4s 1.3s infinite;
  }

  .face__mouth-left {
    animation: ${mouthLeft} 1s 0.3s forwards;
  }

  .face__mouth-right {
    animation: ${mouthRight} 1s 0.3s forwards;
  }

  .face__nose {
    animation: ${nose} 1s 0.3s forwards;
  }

  .face__pupil {
    animation: ${pupil} 4s 1.3s infinite;
  }
`;

const Title = styled.div`
  font-size: 28px;
  font-weight: 700;
  color: #e74c3c;
  letter-spacing: 6px;
  animation: ${glitch} 3s infinite;
  margin-bottom: 8px;
  text-align: center;
`;

const Sub = styled.div`
  font-size: 11px;
  color: #2761c3;
  letter-spacing: 3px;
  text-align: center;
  margin-bottom: 24px;
`;

const Card = styled.div`
  position: relative;
  padding: 24px 32px;
  border: 1px solid #e74c3c;
  clip-path: polygon(
    12px 0%, calc(100% - 12px) 0%,
    100% 12px, 100% calc(100% - 12px),
    calc(100% - 12px) 100%, 12px 100%,
    0% calc(100% - 12px), 0% 12px
  );
  text-align: center;
  max-width: 400px;
`;

const Corner = styled.div`
  position: absolute;
  width: 8px; height: 8px;
  background: #e74c3c;
  transform: rotate(45deg);
  ${p => p.tl && 'top: -4px; left: -4px;'}
  ${p => p.tr && 'top: -4px; right: -4px;'}
  ${p => p.bl && 'bottom: -4px; left: -4px;'}
  ${p => p.br && 'bottom: -4px; right: -4px;'}
`;

const Message = styled.p`
  font-size: 12px;
  color: #ddebf0;
  letter-spacing: 2px;
  line-height: 1.8;
  margin: 0 0 16px;
`;

const Code = styled.div`
  font-size: 10px;
  color: rgba(231, 76, 60, 0.6);
  letter-spacing: 1px;
  margin-top: 16px;
`;

const RetryBtn = styled.button`
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
  font-family: 'Share Tech Mono', monospace;
  font-size: 12px;
  letter-spacing: 3px;
  padding: 12px 24px;
  cursor: pointer;
  clip-path: polygon(
    6px 0%, calc(100% - 6px) 0%,
    100% 6px, 100% calc(100% - 6px),
    calc(100% - 6px) 100%, 6px 100%,
    0% calc(100% - 6px), 0% 6px
  );
  transition: all 0.2s;
  margin-top: 16px;
  &:hover {
    background: rgba(231, 76, 60, 0.1);
    box-shadow: 0 0 20px rgba(231, 76, 60, 0.3);
  }
`;

export default function ErrorPage({ error, onRetry }) {
  return (
    <Wrap>
      <ScanLine />
      <FaceWrap>
        <svg viewBox="0 0 320 380">
          <g fill="none" stroke="currentColor" strokeLinecap="round"
             strokeLinejoin="round" strokeWidth={25}>
            <g className="face__eyes" transform="translate(0,112.5)">
              <g transform="translate(15,0)">
                <polyline className="face__eye-lid" points="37,0 0,120 75,120" />
                <polyline className="face__pupil" points="55,120 55,155"
                  strokeDasharray="35 35" />
              </g>
              <g transform="translate(230,0)">
                <polyline className="face__eye-lid" points="37,0 0,120 75,120" />
                <polyline className="face__pupil" points="55,120 55,155"
                  strokeDasharray="35 35" />
              </g>
            </g>
            <rect className="face__nose" x="132.5" y="112.5"
              width={55} height={155} rx={4} ry={4} />
            <g transform="translate(65,334)" strokeDasharray="102 102">
              <path className="face__mouth-left" d="M 0 30 C 0 30 40 0 95 0" />
              <path className="face__mouth-right" d="M 95 0 C 150 0 190 30 190 30" />
            </g>
          </g>
        </svg>
      </FaceWrap>

      <Title>TIZIM XATOSI</Title>
      <Sub>NEXURA SCANNER v2.0.0</Sub>

      <Card>
        <Corner tl /><Corner tr /><Corner bl /><Corner br />
        <Message>
          NEXURA AI SKANERI VAQTINCHA MAVJUD EMAS.<br />
          TEXNIK ISHLAR OLIB BORILMOQDA.
        </Message>
        <Message style={{ color: 'rgba(221,235,240,0.5)', fontSize: '11px' }}>
          {error || 'SERVER BILAN ALOQA UZILDI'}
        </Message>
        <RetryBtn onClick={onRetry || (() => window.location.reload())}>
          ↺ QAYTA URINISH
        </RetryBtn>
        <Code>ERROR_CODE: NX-503 | SUPPORT: nexuraai.uz</Code>
      </Card>
    </Wrap>
  );
}
