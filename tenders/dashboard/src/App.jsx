import React, { useState, useEffect, useCallback } from 'react';
import * as api from './api.js';
import { TR, formatDateTime } from './locale.js';
import Overview from './components/Overview.jsx';
import TenderTable from './components/TenderTable.jsx';
import TenderDetail from './components/TenderDetail.jsx';
import SuppressedView from './components/SuppressedView.jsx';
import ReportsView from './components/ReportsView.jsx';
import RunHealth from './components/RunHealth.jsx';

const VIEWS = [
  { id: 'overview', label: TR.nav.overview, icon: '⊞' },
  { id: 'tenders', label: TR.nav.tenders, icon: '▤' },
  { id: 'suppressed', label: TR.nav.suppressed, icon: '⊘' },
  { id: 'reports', label: TR.nav.reports, icon: '▧' },
  { id: 'health', label: TR.nav.health, icon: '⚡' },
];

export default function App() {
  const [view, setView] = useState('overview');
  const [runState, setRunState] = useState(null);
  const [tenders, setTenders] = useState([]);
  const [seenTenders, setSeenTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTender, setSelectedTender] = useState(null);
  const [toast, setToast] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [rs, td, st] = await Promise.all([
        api.getRunState(),
        api.getTenders(),
        api.getSeenTenders(),
      ]);
      setRunState(rs);
      setTenders(td);
      setSeenTenders(st);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadData();
    }, 60000);
    return () => clearInterval(interval);
  }, [loadData]);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleTenderUpdate = async (ikn, updates) => {
    try {
      const updated = await api.updateTender(ikn, updates);
      setTenders(prev => prev.map(t => t.ikn === ikn ? { ...t, ...updated } : t));
      showToast(TR.toast.updated);
    } catch (err) {
      showToast(TR.toast.updateFailed(err.message));
    }
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>{TR.sidebar.brand}</h1>
          <p>{TR.sidebar.subtitle}</p>
        </div>
        <nav className="sidebar-nav">
          {VIEWS.map(v => (
            <button
              key={v.id}
              className={`nav-item ${view === v.id ? 'active' : ''}`}
              onClick={() => setView(v.id)}
            >
              <span className="nav-icon">{v.icon}</span>
              {v.label}
            </button>
          ))}
        </nav>
        {runState && (
          <div className="sidebar-footer">
            <span className="pulse-dot" />
            <span>{TR.sidebar.lastScan} {formatDateTime(runState.last_daily_scan_at)}</span>
            <span style={{ display: 'block', fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
              {TR.sidebar.autoRefresh}
            </span>
          </div>
        )}
      </aside>

      <main className="main-content">
        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="loading">{TR.loading}</div>
        ) : (
          <>
            {view === 'overview' && (
              <Overview runState={runState} tenders={tenders} onSelectTender={setSelectedTender} />
            )}
            {view === 'tenders' && (
              <TenderTable tenders={tenders} onSelectTender={setSelectedTender} />
            )}
            {view === 'suppressed' && (
              <SuppressedView tenders={tenders} seenTenders={seenTenders} onSelectTender={setSelectedTender} />
            )}
            {view === 'reports' && <ReportsView />}
            {view === 'health' && <RunHealth runState={runState} />}
          </>
        )}

        {selectedTender && (
          <TenderDetail
            tender={selectedTender}
            onClose={() => setSelectedTender(null)}
            onUpdate={handleTenderUpdate}
          />
        )}
      </main>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
