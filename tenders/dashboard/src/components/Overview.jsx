import React from 'react';
import {
  TR, CLASS_LABELS, CLASS_CHIP_MAP,
  URGENCY_LABELS, URGENCY_CHIP_MAP, OPERATOR_LABEL_NAMES,
  formatDateTime, getAgeString, getDeadlineLabel, parseDeadline, scoreClass,
} from '../locale.js';

export default function Overview({ runState, tenders, onSelectTender }) {
  const counts = runState?.last_counts || {};

  const lastScan = runState?.last_daily_scan_at;
  const scanAge = lastScan ? getAgeString(lastScan) : null;
  const isStale = lastScan ? (Date.now() - new Date(lastScan).getTime()) > 26 * 60 * 60 * 1000 : true;

  // Decision queue: tenders that need operator attention
  // Priority: operator-labeled "priority" first, then ACTION, STRONG_CANDIDATE, WATCH
  // Exclude items already labeled as reject/never_show_similar
  const decisionQueue = tenders
    .filter(t => {
      if (t.operator_label === 'reject' || t.operator_label === 'never_show_similar') return false;
      return ['ACTION', 'STRONG_CANDIDATE', 'WATCH'].includes(t.classification);
    })
    .sort((a, b) => {
      // Priority-labeled items first
      const ap = a.operator_label === 'priority' ? 1 : 0;
      const bp = b.operator_label === 'priority' ? 1 : 0;
      if (bp !== ap) return bp - ap;
      // Then by urgency: CRITICAL > NORMAL > LOW
      const urgOrder = { CRITICAL: 3, NORMAL: 2, LOW: 1 };
      const au = urgOrder[a.urgency] || 2;
      const bu = urgOrder[b.urgency] || 2;
      if (bu !== au) return bu - au;
      // Then by deadline (soonest first)
      const ad = parseDeadline(a.deadline) || Infinity;
      const bd = parseDeadline(b.deadline) || Infinity;
      if (ad !== bd) return ad - bd;
      // Then by score
      return (b.internal_score || 0) - (a.internal_score || 0);
    });

  const criticalItems = decisionQueue.filter(t => t.urgency === 'CRITICAL');
  const actionItems = decisionQueue.filter(t => t.urgency !== 'CRITICAL' && ['ACTION', 'STRONG_CANDIDATE'].includes(t.classification));
  const watchItems = decisionQueue.filter(t => t.urgency !== 'CRITICAL' && t.classification === 'WATCH');

  return (
    <div>
      {/* Compact status bar */}
      <div className="desk-header">
        <div className="desk-header-left">
          <h2>{TR.overview.title}</h2>
          <span className="desk-scan-age">{scanAge || TR.overview.unknown}</span>
        </div>
        <div className="run-state-bar run-state-bar-compact">
          <span className={`dot ${isStale ? 'stale' : ''}`} />
          <span>
            <span className="status-label">{TR.overview.status} </span>
            <span className="status-value">{runState?.last_run_type?.toUpperCase() || '—'}</span>
          </span>
          <span>
            <span className="status-label">{TR.overview.scanTime} </span>
            <span className="status-value">{formatDateTime(lastScan)}</span>
          </span>
        </div>
      </div>

      {/* Compact stats strip */}
      <div className="stats-strip">
        <StripStat label={TR.stats.action} value={counts.action ?? 0} cls="accent-green" />
        <StripStat label={TR.stats.strong_candidate} value={counts.strong_candidate ?? 0} cls="accent-green" />
        <StripStat label={TR.stats.watch} value={counts.watch ?? 0} cls="accent-amber" />
        <div className="stats-strip-divider" />
        <StripStat label={TR.stats.scanned} value={counts.scanned ?? '—'} cls="accent-cyan" />
        <StripStat label={TR.stats.unique} value={counts.unique ?? '—'} cls="accent-blue" />
        <StripStat label={TR.stats.hard_rejected} value={counts.hard_rejected ?? 0} cls="accent-red" />
        <StripStat label={TR.stats.suppressed} value={counts.suppressed ?? 0} cls="accent-purple" />
      </div>

      {/* Decision Queue */}
      <div className="queue-header">
        <h3>{TR.overview.queueTitle}</h3>
        <span className="queue-count">{decisionQueue.length}</span>
      </div>

      {decisionQueue.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">✓</div>
          <p>{TR.overview.queueEmpty}</p>
        </div>
      ) : (
        <div className="decision-queue">
          {criticalItems.length > 0 && (
            <QueueSection
              label={TR.overview.sectionCritical}
              items={criticalItems}
              variant="critical"
              onSelectTender={onSelectTender}
            />
          )}
          {actionItems.length > 0 && (
            <QueueSection
              label={TR.overview.sectionAction}
              items={actionItems}
              variant="action"
              onSelectTender={onSelectTender}
            />
          )}
          {watchItems.length > 0 && (
            <QueueSection
              label={TR.overview.sectionWatch}
              items={watchItems}
              variant="watch"
              onSelectTender={onSelectTender}
            />
          )}
        </div>
      )}
    </div>
  );
}

function QueueSection({ label, items, variant, onSelectTender }) {
  return (
    <div className={`queue-section queue-section-${variant}`}>
      <div className="queue-section-header">
        <span className={`queue-section-dot queue-dot-${variant}`} />
        <span className="queue-section-label">{label}</span>
        <span className="queue-section-count">{items.length}</span>
      </div>
      <div className="queue-cards">
        {items.map(t => (
          <QueueCard key={t.ikn} tender={t} onSelect={onSelectTender} />
        ))}
      </div>
    </div>
  );
}

function QueueCard({ tender: t, onSelect }) {
  const deadlineLabel = getDeadlineLabel(t.deadline);
  const isUrgentDeadline = deadlineLabel === TR.overview.deadlineToday || deadlineLabel === TR.overview.deadlinePassed;
  const hasNoLabel = !t.operator_label || t.operator_label === 'none';

  return (
    <div className="queue-card" onClick={() => onSelect(t)}>
      <div className="queue-card-left">
        <div className={`queue-card-score ${scoreClass(t.external_score)}`}>
          {t.external_score?.toFixed(1) ?? '—'}
        </div>
      </div>
      <div className="queue-card-body">
        <div className="queue-card-title">{t.title}</div>
        <div className="queue-card-authority">{t.authority}</div>
        <div className="queue-card-chips">
          <ClassChip classification={t.classification} />
          {t.urgency && <UrgencyChip urgency={t.urgency} />}
          {deadlineLabel && (
            <span className={`chip chip-deadline ${isUrgentDeadline ? 'chip-deadline-urgent' : ''}`}>
              {deadlineLabel}
            </span>
          )}
          {t.province && <span className="chip chip-silent">{t.province}</span>}
          {t.reported_today && <span className="chip chip-action">{TR.detail.reportedToday}</span>}
          {t.operator_label && t.operator_label !== 'none' && (
            <span className={`chip chip-label-${t.operator_label}`}>
              {OPERATOR_LABEL_NAMES[t.operator_label] || t.operator_label}
            </span>
          )}
          {hasNoLabel && (
            <span className="chip chip-pending">{TR.overview.pendingDecision}</span>
          )}
        </div>
      </div>
      <div className="queue-card-arrow">›</div>
    </div>
  );
}

function StripStat({ label, value, cls }) {
  return (
    <div className="strip-stat">
      <span className={`strip-stat-value ${cls}`}>{value}</span>
      <span className="strip-stat-label">{label}</span>
    </div>
  );
}

function ClassChip({ classification }) {
  return (
    <span className={`chip ${CLASS_CHIP_MAP[classification] || 'chip-silent'}`}>
      {CLASS_LABELS[classification] || classification}
    </span>
  );
}

function UrgencyChip({ urgency }) {
  return (
    <span className={`chip ${URGENCY_CHIP_MAP[urgency] || 'chip-normal'}`}>
      {URGENCY_LABELS[urgency] || urgency}
    </span>
  );
}
