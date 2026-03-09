import React, { useState, useMemo } from 'react';
import {
  TR, CLASS_LABELS, CLASS_CHIP_MAP,
  URGENCY_LABELS, URGENCY_CHIP_MAP, OPERATOR_LABEL_NAMES,
  scoreClass, parseDeadline, openEkap,
} from '../locale.js';

export default function TenderTable({ tenders, onSelectTender }) {
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [provinceFilter, setProvinceFilter] = useState('');
  const [sortKey, setSortKey] = useState('internal_score');
  const [sortDir, setSortDir] = useState('desc');

  const classifications = useMemo(() =>
    [...new Set(tenders.map(t => t.classification).filter(Boolean))].sort(),
    [tenders]
  );
  const statusTags = useMemo(() =>
    [...new Set(tenders.map(t => t.status_tag).filter(Boolean))].sort(),
    [tenders]
  );
  const provinces = useMemo(() =>
    [...new Set(tenders.map(t => t.province).filter(Boolean))].sort(),
    [tenders]
  );

  const filtered = useMemo(() => {
    let list = [...tenders];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(t =>
        (t.title || '').toLowerCase().includes(q) ||
        (t.authority || '').toLowerCase().includes(q) ||
        (t.ikn || '').toLowerCase().includes(q) ||
        (t.province || '').toLowerCase().includes(q)
      );
    }
    if (classFilter) list = list.filter(t => t.classification === classFilter);
    if (statusFilter) list = list.filter(t => t.status_tag === statusFilter);
    if (provinceFilter) list = list.filter(t => t.province === provinceFilter);

    list.sort((a, b) => {
      let av = a[sortKey], bv = b[sortKey];
      if (sortKey === 'deadline') {
        av = parseDeadline(av);
        bv = parseDeadline(bv);
      }
      if (typeof av === 'string') av = av.toLowerCase();
      if (typeof bv === 'string') bv = bv.toLowerCase();
      if (av == null) return 1;
      if (bv == null) return -1;
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return list;
  }, [tenders, search, classFilter, statusFilter, provinceFilter, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const arrow = (key) =>
    sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : '';

  function exportToCsv(items) {
    const BOM = '\uFEFF';
    const headers = ['Puan', 'Sınıf', 'Durum', 'İl', 'Kurum', 'Başlık', 'IKN', 'Son Tarih', 'Güven', 'Aciliyet', 'Etiket', 'Eşleşen Kelimeler'];
    const rows = items.map(t => [
      t.external_score?.toFixed(1) ?? '',
      CLASS_LABELS[t.classification] || t.classification || '',
      t.status_tag || '',
      t.province || '',
      t.authority || '',
      (t.title || '').replace(/;/g, ','),
      t.ikn || '',
      t.deadline || '',
      t.confidence != null ? (t.confidence * 100).toFixed(0) + '%' : '',
      URGENCY_LABELS[t.urgency] || t.urgency || '',
      OPERATOR_LABEL_NAMES[t.operator_label] || '',
      (t.matched_keywords || []).join('; '),
    ]);
    const csv = BOM + [headers, ...rows].map(r => r.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ihaleler-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="page-header">
        <h2>{TR.tenderTable.title}</h2>
        <p>{TR.tenderTable.showing(filtered.length, tenders.length)}</p>
      </div>

      <div className="table-container">
        <div className="table-toolbar">
          <input
            className="search-input"
            placeholder={TR.tenderTable.searchPlaceholder}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select className="filter-select" value={classFilter} onChange={e => setClassFilter(e.target.value)}>
            <option value="">{TR.tenderTable.allClassifications}</option>
            {classifications.map(c => <option key={c} value={c}>{CLASS_LABELS[c] || c}</option>)}
          </select>
          <select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="">{TR.tenderTable.allStatuses}</option>
            {statusTags.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="filter-select" value={provinceFilter} onChange={e => setProvinceFilter(e.target.value)}>
            <option value="">{TR.tenderTable.allProvinces}</option>
            {provinces.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <button
            className="btn btn-primary"
            style={{ marginLeft: 'auto', whiteSpace: 'nowrap', padding: '6px 16px', fontSize: 13 }}
            onClick={() => exportToCsv(filtered)}
          >
            {TR.tenderTable.exportCsv}
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('external_score')}>{TR.th.score}{arrow('external_score')}</th>
                <th onClick={() => handleSort('classification')}>{TR.th.classification}{arrow('classification')}</th>
                <th onClick={() => handleSort('status_tag')}>{TR.th.status}{arrow('status_tag')}</th>
                <th onClick={() => handleSort('province')}>{TR.th.province}{arrow('province')}</th>
                <th>{TR.th.authority}</th>
                <th onClick={() => handleSort('title')}>{TR.th.title}{arrow('title')}</th>
                <th>{TR.th.ikn}</th>
                <th onClick={() => handleSort('deadline')}>{TR.th.deadline}{arrow('deadline')}</th>
                <th onClick={() => handleSort('confidence')}>{TR.th.confidence}{arrow('confidence')}</th>
                <th onClick={() => handleSort('urgency')}>{TR.th.urgency}{arrow('urgency')}</th>
                <th>{TR.th.label}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    {TR.tenderTable.noMatch}
                  </td>
                </tr>
              ) : (
                filtered.map(t => (
                  <tr key={t.ikn} className="clickable" onClick={() => onSelectTender(t)}>
                    <td>
                      <span className={`score-cell ${scoreClass(t.external_score)}`}>
                        {t.external_score?.toFixed(1) ?? '—'}
                      </span>
                    </td>
                    <td>
                      <span className={`chip ${CLASS_CHIP_MAP[t.classification] || 'chip-silent'}`}>
                        {CLASS_LABELS[t.classification] || t.classification}
                      </span>
                    </td>
                    <td><span className="chip chip-silent">{t.status_tag || '—'}</span></td>
                    <td className="province-cell">{t.province || '—'}</td>
                    <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, color: 'var(--text-secondary)' }}>
                      {t.authority || '—'}
                    </td>
                    <td className="tender-title">{t.title}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11, whiteSpace: 'nowrap' }}>
                      {t.ikn ? (
                        <a
                          href="https://ekap.kik.gov.tr/EKAP/Ortak/IhaleArama/index.html"
                          target="_blank"
                          rel="noopener noreferrer"
                          title={TR.ekap.openSearch}
                          style={{ color: 'var(--accent)', textDecoration: 'underline' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            openEkap(t.ikn);
                          }}
                        >
                          {t.ikn}
                        </a>
                      ) : '—'}
                    </td>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>{t.deadline || '—'}</td>
                    <td>
                      {t.confidence != null ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span className="confidence-bar-bg">
                            <span className="confidence-bar-fill" style={{ width: `${(t.confidence * 100)}%` }} />
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{(t.confidence * 100).toFixed(0)}%</span>
                        </span>
                      ) : '—'}
                    </td>
                    <td>
                      {t.urgency ? (
                        <span className={`chip ${URGENCY_CHIP_MAP[t.urgency] || 'chip-normal'}`}>
                          {URGENCY_LABELS[t.urgency] || t.urgency}
                        </span>
                      ) : '—'}
                    </td>
                    <td>
                      {t.operator_label && t.operator_label !== 'none' ? (
                        <span className={`chip chip-label-${t.operator_label}`}>
                          {OPERATOR_LABEL_NAMES[t.operator_label] || t.operator_label}
                        </span>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="table-footer">
          <span>{TR.tenderTable.footerShowing(filtered.length)}</span>
          <span>{TR.tenderTable.footerSort(sortKey, sortDir)}</span>
        </div>
      </div>
    </div>
  );
}
