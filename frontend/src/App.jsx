import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Download, Trash2, Copy, Check, ScanLine, Activity } from 'lucide-react';
import { format as formatDate } from 'date-fns';

function App() {
  const [scans, setScans] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [toastMessage, setToastMessage] = useState('');
  const wsRef = useRef(null);
  const scanInputRef = useRef(null);
  
  // Dynamic Host for Websocket and API based on current URL
  const API_HOST = window.location.hostname;
  // If we are serving via Vite, point to Python's port 8000. 
  // If we are deployed behind an Nginx or single container, point to the same port.
  // We'll default to 8000.
  const API_PORT = process.env.NODE_ENV === 'production' ? window.location.port : 8000;
  
  const HTTP_BASE = `http://${API_HOST}:${API_PORT}/api`;
  const WS_BASE = `ws://${API_HOST}:${API_PORT}/ws`;

  const fetchScans = async () => {
    try {
      const res = await fetch(`${HTTP_BASE}/scans`);
      if (res.ok) {
        const data = await res.json();
        setScans(data);
      }
    } catch (e) {
      console.error("Failed to fetch scans", e);
    }
  };

  useEffect(() => {
    fetchScans();

    const connectWs = () => {
      const ws = new WebSocket(WS_BASE);
      
      ws.onopen = () => setIsConnected(true);
      
      ws.onclose = () => {
        setIsConnected(false);
        // Retry connection
        setTimeout(connectWs, 3000);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'new_scan') {
            setScans(prev => {
              // Check if we already have this scan ID
              const existingIndex = prev.findIndex(s => s.id === data.scan.id);
              
              let newArr;
              if (existingIndex >= 0) {
                // Remove the old one, put the updated one at top
                newArr = prev.filter(s => s.id !== data.scan.id);
                newArr.unshift({...data.scan, isNew: true});
              } else {
                newArr = [{...data.scan, isNew: true}, ...prev];
              }

              // Remove the isNew flag after animation
              setTimeout(() => {
                setScans(current => 
                  current.map(s => s.id === data.scan.id ? {...s, isNew: false} : s)
                );
              }, 1000);
              return newArr;
            });
            showToast(`Scanned: ${data.scan.barcode_data}`);
          } else if (data.type === 'delete_scan') {
            setScans(prev => prev.filter(s => String(s.id) !== String(data.id)));
          } else if (data.type === 'clear_all') {
            setScans([]);
          }
        } catch (e) {
          console.error("WS parse error", e);
        }
      };
      
      wsRef.current = ws;
    };

    connectWs();
    
    // Auto-focus the invisible input on click anywhere so we don't lose the scanner
    const handleGlobalClick = () => {
      if (scanInputRef.current) {
        scanInputRef.current.focus();
      }
    };
    
    window.addEventListener('click', handleGlobalClick);
    
    // Initial focus
    setTimeout(() => {
      if (scanInputRef.current) scanInputRef.current.focus();
    }, 500);

    return () => {
      if (wsRef.current) wsRef.current.close();
      window.removeEventListener('click', handleGlobalClick);
    };
  }, []);

  const handleScanInput = async (e) => {
    // Scanners usually send 'Enter' at the end of the scan
    if (e.key === 'Enter') {
      e.preventDefault();
      const scannedData = e.target.value.trim();
      if (scannedData) {
        try {
          await fetch(`${HTTP_BASE}/scans`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode_data: scannedData })
          });
        } catch (err) {
          console.error("Manual scan submission failed", err);
        }
      }
      // Clear the invisible input
      e.target.value = '';
    }
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 3000);
  };

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this scan?")) return;
    try {
      await fetch(`${HTTP_BASE}/scans/${id}`, { method: 'DELETE' });
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  const handleDeleteAll = async () => {
    if (scans.length === 0) return;
    if (!window.confirm("CAUTION: Are you sure you want to clear ALL scan history? This cannot be undone.")) return;
    try {
      await fetch(`${HTTP_BASE}/scans`, { method: 'DELETE' });
    } catch (e) {
      console.error("Clear all failed", e);
    }
  };

  const handleExport = () => {
    window.open(`${HTTP_BASE}/export`, '_blank');
  };

  return (
    <div className="app-container">
      {/* Invisible input specifically for catching scanner keystrokes */}
      <input 
        type="text" 
        ref={scanInputRef}
        onKeyDown={handleScanInput}
        style={{ position: 'absolute', opacity: 0, top: '-1000px' }}
        autoFocus
      />
      
      <header className="header">
        <div>
          <h1>Enhanced Scanning Console</h1>
          <div className="status-indicator" style={{marginTop: '0.5rem'}}>
            <div className={`status-dot ${isConnected ? 'connected' : ''}`}></div>
            {isConnected ? 'Scanner service connected' : 'Connecting to scanner service...'}
          </div>
        </div>
        <div className="actions-group">
          <button className="btn btn-primary" onClick={handleExport} disabled={scans.length === 0}>
            <Download size={18} />
            Export CSV
          </button>
          <button className="btn btn-danger" onClick={handleDeleteAll} disabled={scans.length === 0}>
            <Trash2 size={18} />
            Delete All
          </button>
        </div>
      </header>

      <main className="glass-panel">
        <div className="table-wrapper">
          {scans.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Barcode Data</th>
                  <th>Count</th>
                  <th style={{textAlign: 'right'}}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => (
                  <tr key={scan.id} className={scan.isNew ? 'row-new' : ''}>
                    <td className="timestamp">
                      {formatDate(new Date(scan.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                    </td>
                    <td className="barcode-data">
                      {scan.barcode_data}
                    </td>
                    <td>
                      <span className="count-badge">
                        {scan.count || 1}
                      </span>
                    </td>
                    <td style={{textAlign: 'right'}}>
                      <div className="row-actions" style={{display: 'inline-flex'}}>
                        <button 
                          onClick={() => copyToClipboard(scan.barcode_data, scan.id)}
                          className="btn btn-icon-only"
                          title="Copy to clipboard"
                        >
                          {copiedId === scan.id ? <Check size={18} className="success" style={{color: 'var(--success)'}}/> : <Copy size={18} />}
                        </button>
                        <button 
                          onClick={() => handleDelete(scan.id)}
                          className="btn btn-icon-only btn-icon-danger"
                          title="Delete scan"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <ScanLine size={64} />
              <h3>Awaiting Scans...</h3>
              <p>Plug in your scanner and scan a barcode to begin logging history.</p>
            </div>
          )}
        </div>
      </main>

      {toastMessage && (
        <div className="toast">
          <Activity size={20} color="var(--accent)" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}

export default App;
