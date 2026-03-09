import React, { useState, useMemo } from 'react';
import { TR, STATUS_LABELS, CLASS_CHIP_MAP } from '../locale.js';

export default function SuppressedView({ tenders, seenTenders, onSelectTender }) {
  const [tab, setTab] = useState('suppressed');
  const [search, setSearch] = useState('');

  const suppressedItems = useMemo(() => {
    return seenTenders
      .filter(t => t.suppression_count > 0 || t.latest_status === 'REJECTED' || t.latest_status === 'OUT_OF_WINDOW')
      .sort((a, b) => (b.latest_internal_score || 0) - (a.latest_internal_score || 0));
  }, [seenTenders]);

  const hardRejected = useMemo(() => {
    return tenders
      .filter(t => t.classification === 'HARD_REJECT')
      .sort((a, b) => (b.internal_score || 0) - (a.internal_score || 0));
  }, [tenders]);

  const silentRejected = useMemo(() => {
    return tenders
      .filter(t => t.classification === 'SILENT_REJECT')
      .sort((a, b) => (b.internal_score || 0) - (a.internal_score || 0));
  }, [tenders]);

  const tabConfig = {
    suppressed: { items: suppressedItems, isDecision: false, desc: TR.suppressed.archiveDesc, icon: '▫' },
    hard_rejected: { items: hardRejected, isDecision: true, desc: TR.suppressed.hardRejectDesc, icon: '✕' },
    silent_rejected: { items: silentRejected, isDecision: true, desc: TR.suppressed.silentRejectDesc, icon: '–' },
  };

  const { items: rawItems, isDecision, desc: tabDesc, icon: tabIcon } = tabConfig[tab];

  let displayItems = rawItems;
  if (search) {
    const q = search.toLowerCase();
    displayItems = displayItems.filter(t =>
      (t.title || '').toLowerCase().includes(q) ||
      (t.authority || '').toLowerCase().includes(q) ||
      (t.ikn || '').toLowerCase().includes(q)
    );
  }

  return (
    <div>
      <div className="page-header">
        <h2>{TR.suppressed.title}</h2>
        <p>{TR.suppressed.subtitle}</p>
      </div>

      <div className="tab-bar suppressed-tab-bar">
        <button
          className={`tab-btn tab-btn-archive ${tab === 'suppressed' ? 'active' : ''}`}
          onClick={() => setTab('suppressed')}
        >
          <span className="tab-icon">▫</span>
          {TR.suppressed.tabSuppressed(suppressedItems.length)}
        </button>
        <button
          className={`tab-btn tab-btn-hard ${tab === 'hard_rejected' ? 'active' : ''}`}
          onClick={() => setTab('hard_rejected')}
        >
          <span className="tab-icon">✕</span>
          {TR.suppressed.tabHardRejected(hardRejected.length)}
        </button>
        <button
          className={`tab-btn tab-btn-silent ${tab === 'silent_rejected' ? 'active' : ''}`}
          onClick={() => setTab('silent_rejected')}
        >
          <span className="tab-icon">–</span>
          {TR.suppressed.tabSilentRejected(silentRejected.length)}
        </button>
      </div>

      {/* Tab description banner */}
      <div className={`tab-desc tab-desc-${tab}`}>
        <span className="tab-desc-icon">{tabIcon}</span>
        <span>{tabDesc}</span>
      </div>

      <div className="table-container">
        <div className="table-toolbar">
          <input
            className="search-input"
            placeholder={TR.suppressed.searchPlaceholder}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>{TR.th.score}</th>
                <th>{TR.th.ikn}</th>
                <th>{TR.th.title}</th>
                <th>{TR.th.authority}</th>
                <th>{TR.th.province}</th>
                <th>{TR.th.status}</th>
                <th>{TR.th.reason}</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                    {TR.suppressed.noItems}
                  </td>
                </tr>
              ) : (
                displayItems.map(t => (
                  <tr
                    key={t.ikn}
                    className={`clickable ${!isDecision ? 'suppressed-row' : 'rejected-row'}`}
                    onClick={() => { if (isDecision) onSelectTender(t); }}
                  >
                    <td>
                      <span className={`score-cell ${isDecision ? 'score-low' : 'score-archived'}`} style={{ fontSize: 13 }}>
                        {isDecision
                          ? (t.external_score?.toFixed(1) ?? '—')
                          : (t.latest_external_score?.toFixed(1) ?? '—')
                        }
                      </span>
                    </td>
                    <td className="ikn-cell">{t.ikn}</td>
                    <td className="tender-title">{t.title}</td>
                    <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, color: 'var(--text-secondary)' }}>
                      {t.authority || '—'}
                    </td>
                    <td className="province-cell">{t.province || '—'}</td>
                    <td>
                      <StatusChip status={isDecision ? t.classification : t.latest_status} isArchive={!isDecision} />
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {getReason(t, isDecision)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="table-footer">
          <span>{TR.suppressed.itemCount(displayItems.length)}</span>
        </div>
      </div>
    </div>
  );
}

function StatusChip({ status, isArchive }) {
  if (isArchive) {
    const archiveMap = {
      REJECTED: 'chip-archive-rejected',
      OUT_OF_WINDOW: 'chip-archive-expired',
      SEEN: 'chip-archive-seen',
    };
    return (
      <span className={`chip ${archiveMap[status] || 'chip-silent'}`}>
        {STATUS_LABELS[status] || status || '—'}
      </span>
    );
  }
  const chipMap = {
    HARD_REJECT: 'chip-hard-reject',
    SILENT_REJECT: 'chip-silent',
  };
  return (
    <span className={`chip ${chipMap[status] || 'chip-silent'}`}>
      {STATUS_LABELS[status] || status || '—'}
    </span>
  );
}

function getReason(t, isDecision) {
  if (isDecision) {
    if (t.reasons && t.reasons.length > 0) {
      return t.reasons.map(r => `${r.code}: ${r.detail}`).join('; ');
    }
    return STATUS_LABELS[t.classification] || t.classification;
  }
  if (t.latest_status === 'REJECTED') return TR.suppressed.reasonRejected;
  if (t.latest_status === 'OUT_OF_WINDOW') return TR.suppressed.reasonOutOfWindow;
  if (t.suppression_count > 0) return TR.suppressed.reasonSuppressed(t.suppression_count);
  return t.latest_classification || '—';
}
