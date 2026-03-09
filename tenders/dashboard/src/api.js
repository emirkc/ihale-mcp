const BASE = '/api';

async function fetchJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getRunState() {
  return fetchJSON('/run-state');
}

export async function getTenders() {
  return fetchJSON('/tenders');
}

export async function getSeenTenders() {
  return fetchJSON('/seen-tenders');
}

export async function getHistory() {
  return fetchJSON('/history');
}

export async function getReports() {
  return fetchJSON('/reports');
}

export async function getReport(type, filename) {
  return fetchJSON(`/reports/${type}/${encodeURIComponent(filename)}`);
}

export async function updateTender(ikn, updates) {
  const res = await fetch(`${BASE}/tenders/${encodeURIComponent(ikn)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getBidTracking() {
  return fetchJSON('/bid-tracking');
}

export async function updateBidTracking(ikn, updates) {
  const res = await fetch(`${BASE}/bid-tracking/${encodeURIComponent(ikn)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
