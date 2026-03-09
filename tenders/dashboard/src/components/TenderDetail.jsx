import React, { useState, useEffect } from 'react';
import {
  TR, CLASS_LABELS, CLASS_CHIP_MAP,
  URGENCY_LABELS, URGENCY_CHIP_MAP, OPERATOR_LABEL_NAMES,
  BID_STATUS_LABELS, BID_STATUS_CHIPS, openEkap,
} from '../locale.js';
import { getBidTracking, updateBidTracking } from '../api.js';

const LABELS = ['none', 'priority', 'watch', 'reject', 'never_show_similar'];

export default function TenderDetail({ tender, onClose, onUpdate }) {
  const [notes, setNotes] = useState(tender.operator_notes || '');
  const [label, setLabel] = useState(tender.operator_label || 'none');
  const [saving, setSaving] = useState(false);
  const [iknCopied, setIknCopied] = useState(false);

  // Bid tracking state
  const [bidEntry, setBidEntry] = useState(null);
  const [bidStatus, setBidStatus] = useState('reviewing');
  const [bidAmount, setBidAmount] = useState('');
  const [bidNotes, setBidNotes] = useState('');
  const [bidLossReason, setBidLossReason] = useState('');
  const [bidSaving, setBidSaving] = useState(false);
  const [bidLoaded, setBidLoaded] = useState(false);

  useEffect(() => {
    getBidTracking()
      .then(items => {
        const entry = items.find(i => i.ikn === tender.ikn);
        if (entry) {
          setBidEntry(entry);
          setBidStatus(entry.status || 'reviewing');
          setBidAmount(entry.bid_amount != null ? String(entry.bid_amount) : '');
          setBidNotes(entry.notes || '');
          setBidLossReason(entry.loss_reason || '');
        }
        setBidLoaded(true);
      })
      .catch(() => setBidLoaded(true));
  }, [tender.ikn]);

  const handleBidSave = async () => {
    setBidSaving(true);
    try {
      const updates = { status: bidStatus };
      if (bidAmount !== '') updates.bid_amount = Number(bidAmount);
      if (bidNotes !== '') updates.notes = bidNotes;
      if (bidStatus === 'lost' && bidLossReason !== '') updates.loss_reason = bidLossReason;
      const updated = await updateBidTracking(tender.ikn, updates);
      setBidEntry(updated);
    } catch {
      // silent — toast could be added later
    }
    setBidSaving(false);
  };

  const handleStartTracking = async () => {
    setBidSaving(true);
    try {
      const updated = await updateBidTracking(tender.ikn, { status: 'reviewing' });
      setBidEntry(updated);
      setBidStatus('reviewing');
    } catch {
      // silent
    }
    setBidSaving(false);
  };

  const bidDirty = bidEntry
    ? (bidStatus !== (bidEntry.status || 'reviewing') ||
       bidAmount !== (bidEntry.bid_amount != null ? String(bidEntry.bid_amount) : '') ||
       bidNotes !== (bidEntry.notes || '') ||
       bidLossReason !== (bidEntry.loss_reason || ''))
    : false;

  const handleSave = async () => {
    setSaving(true);
    await onUpdate(tender.ikn, { operator_notes: notes, operator_label: label });
    setSaving(false);
  };

  const isDirty = notes !== (tender.operator_notes || '') || label !== (tender.operator_label || 'none');

  return (
    <div className="detail-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="detail-panel">
        <div className="detail-header">
          <div className="detail-title">{tender.title}</div>
          <button className="detail-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-meta">
          <span className={`chip ${CLASS_CHIP_MAP[tender.classification] || 'chip-silent'}`}>
            {CLASS_LABELS[tender.classification] || tender.classification}
          </span>
          {tender.urgency && (
            <span className={`chip ${URGENCY_CHIP_MAP[tender.urgency] || 'chip-normal'}`}>
              {URGENCY_LABELS[tender.urgency] || tender.urgency}
            </span>
          )}
          {tender.status_tag && <span className="chip chip-silent">{tender.status_tag}</span>}
          {tender.reported_today && <span className="chip chip-action">{TR.detail.reportedToday}</span>}
          {tender.operator_label && tender.operator_label !== 'none' && (
            <span className={`chip chip-label-${tender.operator_label}`}>
              {OPERATOR_LABEL_NAMES[tender.operator_label] || tender.operator_label}
            </span>
          )}
        </div>

        <div className="detail-section">
          <h3>{TR.detail.sectionInfo}</h3>
          <div className="info-grid">
            <div className="info-item">
              <div className="info-label">{TR.detail.labelIkn}</div>
              <div className="info-value" style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                {tender.ikn ? (
                  <a
                    href="https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/index.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    title={TR.ekap.openSearch}
                    style={{ color: 'var(--accent)', textDecoration: 'underline', cursor: 'pointer' }}
                    onClick={(e) => {
                      e.preventDefault();
                      openEkap(tender.ikn);
                      setIknCopied(true);
                      setTimeout(() => setIknCopied(false), 2000);
                    }}
                  >
                    {tender.ikn}
                  </a>
                ) : '—'}
                {iknCopied && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--green)', fontFamily: 'inherit' }}>
                    {TR.ekap.iknCopied}
                  </span>
                )}
              </div>
            </div>
            <InfoItem label={TR.detail.labelProvince} value={tender.province} />
            <InfoItem label={TR.detail.labelAuthority} value={tender.authority} />
            <InfoItem label={TR.detail.labelDeadline} value={tender.deadline} />
            <InfoItem label={TR.detail.labelScore} value={`${tender.external_score?.toFixed(1)} / 10 (dahili: ${tender.internal_score})`} />
            <InfoItem label={TR.detail.labelConfidence} value={tender.confidence != null ? `${(tender.confidence * 100).toFixed(0)}%` : '—'} />
          </div>
        </div>

        <div className="detail-section">
          <h3>{TR.detail.sectionScore}</h3>
          {(tender.reasons && tender.reasons.length > 0) ? (
            tender.reasons.map((r, i) => (
              <div key={i} className="reason-row">
                <span className="reason-code">{r.code}</span>
                <span className={`reason-points ${r.points < 0 ? 'reason-negative' : ''}`}>{r.points >= 0 ? '+' : ''}{r.points}</span>
                <span className="reason-detail">{r.detail}</span>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{TR.detail.noReasons}</div>
          )}
        </div>

        {tender.risk_flags && tender.risk_flags.length > 0 && (
          <div className="detail-section">
            <h3>{TR.detail.sectionRisk}</h3>
            <div className="keyword-list">
              {tender.risk_flags.map((f, i) => (
                <span key={i} className="risk-chip">{f}</span>
              ))}
            </div>
          </div>
        )}

        {tender.matched_keywords && tender.matched_keywords.length > 0 && (
          <div className="detail-section">
            <h3>{TR.detail.sectionKeywords}</h3>
            <div className="keyword-list">
              {tender.matched_keywords.map((k, i) => (
                <span key={i} className="keyword-chip">{k}</span>
              ))}
            </div>
          </div>
        )}

        {tender.matched_clusters && tender.matched_clusters.length > 0 && (
          <div className="detail-section">
            <h3>{TR.detail.sectionClusters}</h3>
            <div className="keyword-list">
              {tender.matched_clusters.map((c, i) => (
                <span key={i} className="cluster-chip">{c}</span>
              ))}
            </div>
          </div>
        )}

        {tender.notes && (
          <div className="detail-section">
            <h3>{TR.detail.sectionNotes}</h3>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{tender.notes}</div>
          </div>
        )}

        <div className="detail-section">
          <h3>{TR.detail.sectionActions}</h3>
          <div className="action-form">
            <div>
              <label>{TR.detail.manualLabel}</label>
              <select value={label} onChange={e => setLabel(e.target.value)} style={{ display: 'block', marginTop: 6, width: '100%' }}>
                {LABELS.map(l => <option key={l} value={l}>{OPERATOR_LABEL_NAMES[l] || l}</option>)}
              </select>
            </div>
            <div>
              <label>{TR.detail.operatorNotes}</label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder={TR.detail.notesPlaceholder}
              />
            </div>
            <button
              className="btn btn-primary"
              disabled={!isDirty || saving}
              onClick={handleSave}
            >
              {saving ? TR.detail.saving : TR.detail.save}
            </button>
          </div>
        </div>

        {bidLoaded && (
          <div className="detail-section">
            <h3>{TR.bidTracking.title}</h3>
            {!bidEntry ? (
              <div className="action-form">
                <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 12 }}>
                  {TR.bidTracking.noTracking}
                </div>
                <button
                  className="btn btn-primary"
                  disabled={bidSaving}
                  onClick={handleStartTracking}
                >
                  {bidSaving ? TR.detail.saving : TR.bidTracking.startTracking}
                </button>
              </div>
            ) : (
              <div className="action-form">
                {bidEntry.status && (
                  <div style={{ marginBottom: 8 }}>
                    <span className={`chip ${BID_STATUS_CHIPS[bidEntry.status] || 'chip-silent'}`}>
                      {BID_STATUS_LABELS[bidEntry.status] || bidEntry.status}
                    </span>
                  </div>
                )}
                <div>
                  <label>{TR.bidTracking.status}</label>
                  <select
                    value={bidStatus}
                    onChange={e => setBidStatus(e.target.value)}
                    style={{ display: 'block', marginTop: 6, width: '100%' }}
                  >
                    {Object.keys(BID_STATUS_LABELS).map(s => (
                      <option key={s} value={s}>{BID_STATUS_LABELS[s]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>{TR.bidTracking.bidAmount}</label>
                  <input
                    type="number"
                    value={bidAmount}
                    onChange={e => setBidAmount(e.target.value)}
                    placeholder="0"
                    style={{ display: 'block', marginTop: 6, width: '100%' }}
                  />
                </div>
                <div>
                  <label>{TR.bidTracking.notes}</label>
                  <textarea
                    value={bidNotes}
                    onChange={e => setBidNotes(e.target.value)}
                    placeholder={TR.detail.notesPlaceholder}
                  />
                </div>
                {bidStatus === 'lost' && (
                  <div>
                    <label>{TR.bidTracking.lossReason}</label>
                    <textarea
                      value={bidLossReason}
                      onChange={e => setBidLossReason(e.target.value)}
                      placeholder={TR.bidTracking.lossReason}
                    />
                  </div>
                )}
                <button
                  className="btn btn-primary"
                  disabled={!bidDirty || bidSaving}
                  onClick={handleBidSave}
                >
                  {bidSaving ? TR.detail.saving : TR.detail.save}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function InfoItem({ label, value, mono }) {
  return (
    <div className="info-item">
      <div className="info-label">{label}</div>
      <div className="info-value" style={mono ? { fontFamily: 'var(--font-mono)', fontSize: 12 } : undefined}>
        {value || '—'}
      </div>
    </div>
  );
}
