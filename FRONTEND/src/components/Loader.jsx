import React from 'react';
import styled from 'styled-components';

const Loader = () => {
  return (
    <StyledWrapper>
      <div className="radar-container">
        <div className="loader">
          <span />
          <div id="dot-1" className="dot" />
          <div id="dot-2" className="dot" />
          <div id="dot-3" className="dot" />
          <div id="dot-4" className="dot" />
          <div id="dot-5" className="dot" />
        </div>
        <div className="scan-text">Tizim zaifliklari qidirilmoqda...</div>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;

  .radar-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .scan-text {
    color: #2e8b57;
    font-family: monospace;
    font-size: 14px;
    letter-spacing: 2px;
    text-transform: uppercase;
    animation: pulse 1.5s infinite;
  }

  .loader {
    position: relative;
    width: 200px;
    height: 200px;
    background: rgba(33, 33, 33, 0.9);
    border-radius: 50%;
    box-shadow: inset 0px 0px 15px seagreen;
    border: 2px solid seagreen;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .loader::before {
    content: "";
    position: absolute;
    inset: 30px;
    background: transparent;
    border: 1px solid rgba(46, 139, 87, 0.5);
    border-radius: 50%;
    box-shadow: inset 0px 0px 10px seagreen;
  }

  .loader::after {
    content: "";
    position: absolute;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    border: 1px solid seagreen;
    box-shadow: inset 0px 0px 5px seagreen;
  }

  .loader span {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 100%;
    height: 100%;
    background: linear-gradient(45deg, rgba(46, 139, 87, 0.3) 0%, transparent 50%);
    transform-origin: top left;
    animation: radar81 2s linear infinite;
    border-top: 2px solid #2e8b57;
  }

  @keyframes radar81 {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  .dot {
    width: 6px;
    height: 6px;
    position: absolute;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 10px #00ff87;
    animation: fly 20s linear infinite;
  }

  #dot-1 { --dot-start-top: 150px; --dot-start-left: 180px; --dot-end-top: 50px; --dot-end-left: 20px; animation-delay: 0s; }
  #dot-2 { --dot-start-top: 50px; --dot-start-left: 10px; --dot-end-top: 180px; --dot-end-left: 150px; animation-delay: 2s; }
  #dot-3 { --dot-start-top: 20px; --dot-start-left: 100px; --dot-end-top: 170px; --dot-end-left: 30px; animation-delay: 4s; }
  #dot-4 { --dot-start-top: 160px; --dot-start-left: 40px; --dot-end-top: 20px; --dot-end-left: 160px; animation-delay: 1s; }
  #dot-5 { --dot-start-top: 100px; --dot-start-left: 100px; --dot-end-top: 10px; --dot-end-left: 10px; animation-delay: 5s; }

  @keyframes fly {
    0% { top: var(--dot-start-top); left: var(--dot-start-left); opacity: 0; }
    10%, 90% { opacity: 1; }
    100% { top: var(--dot-end-top); left: var(--dot-end-left); opacity: 0; }
  }
`;

export default Loader;
