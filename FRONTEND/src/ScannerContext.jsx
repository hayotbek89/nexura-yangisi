import React, { createContext, useContext, useState } from 'react';

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
    agentic, setAgentic
  };

  return (
    <ScannerContext.Provider value={value}>
      {children}
    </ScannerContext.Provider>
  );
};
