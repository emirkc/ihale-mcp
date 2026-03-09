import React, { useState, useEffect } from 'react';
import { marked } from 'marked';
import * as api from '../api.js';
import { TR } from '../locale.js';

export default function ReportsView() {
  const [reportList, setReportList] = useState({ daily: [], weekly: [] });
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);

  useEffect(() => {
    api.getReports().then(data => {
      setReportList(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleSelect = async (type, filename) => {
    const key = `${type}/${filename}`;
    if (selected === key) return;
    setSelected(key);
    setLoadingContent(true);
    try {
      const data = await api.getReport(type, filename);
      setContent(data.content || '');
    } catch {
      setContent(TR.reports.failedLoad);
    }
    setLoadingContent(false);
  };

  const allReports = [
    ...reportList.daily.map(f => ({ type: 'daily', filename: f })),
    ...reportList.weekly.map(f => ({ type: 'weekly', filename: f })),
  ];

  return (
    <div>
      <div className="page-header">
        <h2>{TR.reports.title}</h2>
        <p>{TR.reports.count(allReports.length)}</p>
      </div>

      {loading ? (
        <div className="loading">{TR.loadingReports}</div>
      ) : allReports.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">▧</div>
          <p>{TR.reports.noReports}</p>
        </div>
      ) : (
        <>
          <div className="report-list">
            {allReports.map(r => (
              <div
                key={`${r.type}/${r.filename}`}
                className={`report-item ${selected === `${r.type}/${r.filename}` ? 'active' : ''}`}
                onClick={() => handleSelect(r.type, r.filename)}
              >
                <span className={`report-type-badge report-type-${r.type}`}>
                  {r.type === 'daily' ? 'günlük' : 'haftalık'}
                </span>
                <span>{r.filename}</span>
              </div>
            ))}
          </div>

          {selected && (
            loadingContent ? (
              <div className="loading">{TR.loadingContent}</div>
            ) : (
              <div className="report-content" dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
            )
          )}
        </>
      )}
    </div>
  );
}

function renderMarkdown(md) {
  return marked.parse(md, { breaks: true, gfm: true });
}
