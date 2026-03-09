import React, { useState, useEffect } from 'react';
import * as api from '../api.js';
import { TR, COUNT_KEY_LABELS, formatDateTime, formatTime } from '../locale.js';

export default function RunHealth({ runState }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getHistory().then(events => {
      setHistory(events);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const lastScan = runState?.last_daily_scan_at;
  const isStale = lastScan ? (Date.now() - new Date(lastScan).getTime()) > 26 * 60 * 60 * 1000 : true;
  const counts = runState?.last_counts || {};

  const eventCounts = {};
  history.forEach(e => {
    eventCounts[e.event_type] = (eventCounts[e.event_type] || 0) + 1;
  });

  return (
    <div>
      <div className="page-header">
        <h2>{TR.health.title}</h2>
        <p>{TR.health.subtitle}</p>
      </div>

      <div className="run-state-bar" style={{ marginBottom: 'var(--space-6)' }}>
        <span className={`dot ${isStale ? 'stale' : ''}`} />
        <span className="status-value" style={{ fontSize: 14 }}>
          {isStale ? TR.health.stale : TR.health.healthy}
        </span>
      </div>

      <div className="stats-grid" style={{ marginBottom: 'var(--space-6)' }}>
        <StatCard label={TR.health.lastRunType} value={runState?.last_run_type?.toUpperCase() || '—'} />
        <StatCard label={TR.health.lastDailyScan} value={formatDateTime(runState?.last_daily_scan_at)} small />
        <StatCard label={TR.health.lastDeltaScan} value={formatDateTime(runState?.last_delta_scan_at) || '—'} small />
        <StatCard label={TR.health.lastWeeklySummary} value={formatDateTime(runState?.last_weekly_summary_at) || '—'} small />
        <StatCard label={TR.health.lastSuccess} value={formatDateTime(runState?.last_successful_run_at)} small />
        <StatCard label={TR.health.updatedAt} value={formatDateTime(runState?.updated_at)} small />
      </div>

      <div className="detail-section">
        <h3 className="section-title">{TR.health.lastScanCounts}</h3>
        <div className="stats-grid">
          {Object.entries(counts).map(([key, val]) => (
            <div key={key} className="stat-card">
              <div className="label">{COUNT_KEY_LABELS[key] || key.replace(/_/g, ' ')}</div>
              <div className="value" style={{ fontSize: 22 }}>{val}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="detail-section" style={{ marginTop: 'var(--space-6)' }}>
        <h3 className="section-title">{TR.health.reportPaths}</h3>
        <div style={{ fontSize: 13, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', marginRight: 'var(--space-2)' }}>{TR.health.lastReport}</span>
            <span className="code-path">{runState?.last_report_path || '—'}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', marginRight: 'var(--space-2)' }}>{TR.health.lastWeekly}</span>
            <span className="code-path">{runState?.last_weekly_report_path || '—'}</span>
          </div>
        </div>
      </div>

      <div className="detail-section" style={{ marginTop: 'var(--space-6)' }}>
        <h3 className="section-title">
          {TR.health.eventLog}
          <span className="section-count">{TR.health.events(history.length)}</span>
        </h3>

        {loading ? (
          <div className="loading">{TR.loadingHistory}</div>
        ) : history.length === 0 ? (
          <div className="empty-state">
            <p>{TR.health.noHistory}</p>
          </div>
        ) : (
          <>
            <div className="stats-grid" style={{ marginBottom: 'var(--space-4)' }}>
              {Object.entries(eventCounts).map(([type, count]) => (
                <div key={type} className="stat-card">
                  <div className="label">{type}</div>
                  <div className="value" style={{ fontSize: 20 }}>{count}</div>
                </div>
              ))}
            </div>

            <div className="table-container">
              <div style={{ overflowX: 'auto', maxHeight: 400 }}>
                <table>
                  <thead>
                    <tr>
                      <th>{TR.th.time}</th>
                      <th>{TR.th.ikn}</th>
                      <th>{TR.th.event}</th>
                      <th>{TR.th.summary}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 50).map((e, i) => (
                      <tr key={i}>
                        <td style={{ whiteSpace: 'nowrap', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                          {formatTime(e.timestamp)}
                        </td>
                        <td className="ikn-cell">{e.ikn}</td>
                        <td><span className="chip chip-silent">{e.event_type}</span></td>
                        <td style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {e.summary}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {history.length > 50 && (
                <div className="table-footer">
                  <span>{TR.health.showingEvents(50, history.length)}</span>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, small }) {
  return (
    <div className={`stat-card ${small ? 'stat-card-sm' : ''}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}
