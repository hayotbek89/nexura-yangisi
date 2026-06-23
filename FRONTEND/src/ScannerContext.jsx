import React, { createContext, useContext, useState, useCallback } from 'react';
import { apiFetch } from './api';

const ScannerContext = createContext();

export const useScanner = () => useContext(ScannerContext);

export const ScannerProvider = ({ children }) => {
  const [url, setUrl] = useState('');
  const [scanning, setScanning] = useState(false);
  const [messages, setMessages] = useState([]);
  const [results, setResults] = useState([]);
  const [findings, setFindings] = useState({ critical: 0, high: 0, medium: 0, low: 0 });
  const [toolStatus, setToolStatus] = useState({
    nmap: { status: 'idle' },
    nikto: { status: 'idle' },
    sqlmap: { status: 'idle' },
    nuclei: { status: 'idle' },
    gobuster: { status: 'idle' },
    amass: { status: 'idle' },
  });
  const [aiAdvice, setAiAdvice] = useState('');
  const [scanId, setScanId] = useState(null);
  const [reportUrl, setReportUrl] = useState(null);
  const [agentic, setAgentic] = useState(false);

  const [chatLogs, setChatLogs] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  // Terminal multi-tab state (persists across navigation)
  const [terminals, setTerminals] = useState([
    { id: 'term_1', logs: [], loading: false, input: '' },
  ]);
  const [activeTerminal, setActiveTerminal] = useState('term_1');
  const [terminalScrolledUp, setTerminalScrolledUp] = useState({});

  const appendToTerminal = useCallback((termId, lines) => {
    setTerminals(prev => prev.map(t =>
      t.id === termId
        ? { ...t, logs: [...t.logs, ...(Array.isArray(lines) ? lines : [lines])] }
        : t
    ))
  }, [])

  const addTerminal = useCallback(() => {
    const id = 'term_' + Date.now() + '_' + Math.random().toString(36).slice(2, 4)
    setTerminals(prev => [...prev, { id, logs: [], loading: false, input: '' }])
    setActiveTerminal(id)
  }, [])

  const closeTerminal = useCallback((id) => {
    setTerminals(prev => {
      const filtered = prev.filter(t => t.id !== id)
      if (filtered.length === 0) {
        const newId = 'term_' + Date.now()
        return [{ id: newId, logs: [], loading: false, input: '' }]
      }
      return filtered
    })
    setTerminalScrolledUp(prev => { const n = {...prev}; delete n[id]; return n })
  }, [])

  const value = {
    url, setUrl,
    scanning, setScanning,
    messages, setMessages,
    results, setResults,
    findings, setFindings,
    toolStatus, setToolStatus,
    aiAdvice, setAiAdvice,
    scanId, setScanId,
    reportUrl, setReportUrl,
    agentic, setAgentic,
    chatLogs, setChatLogs,
    chatLoading, setChatLoading,
    terminals, setTerminals,
    activeTerminal, setActiveTerminal,
    terminalScrolledUp, setTerminalScrolledUp,
    appendToTerminal,
    addTerminal,
    closeTerminal,
  };

  return (
    <ScannerContext.Provider value={value}>
      {children}
    </ScannerContext.Provider>
  );
};
