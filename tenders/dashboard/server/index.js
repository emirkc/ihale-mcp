import express from 'express';
import cors from 'cors';
import { readFile, writeFile, readdir } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, '../../data');
const REPORTS_DIR = join(__dirname, '../../reports');

const app = express();
app.use(cors());
app.use(express.json());

// Serve built frontend in production
const distDir = join(__dirname, '../dist');
if (existsSync(distDir)) {
  app.use(express.static(distDir));
}

// --- Helpers ---

async function readJSON(filename) {
  const raw = await readFile(join(DATA_DIR, filename), 'utf-8');
  return JSON.parse(raw);
}

// --- API Routes ---

app.get('/api/run-state', async (_req, res) => {
  try {
    const data = await readJSON('run_state.json');
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: 'Failed to read run_state.json', detail: err.message });
  }
});

app.get('/api/tenders', async (_req, res) => {
  try {
    const data = await readJSON('tender_decisions.json');
    res.json(data.items || []);
  } catch (err) {
    res.status(500).json({ error: 'Failed to read tender_decisions.json', detail: err.message });
  }
});

app.get('/api/seen-tenders', async (_req, res) => {
  try {
    const data = await readJSON('seen_tenders.json');
    res.json(data.items || []);
  } catch (err) {
    res.status(500).json({ error: 'Failed to read seen_tenders.json', detail: err.message });
  }
});

app.get('/api/history', async (_req, res) => {
  try {
    const data = await readJSON('tender_history.json');
    res.json(data.events || []);
  } catch (err) {
    res.status(500).json({ error: 'Failed to read tender_history.json', detail: err.message });
  }
});

app.get('/api/reports', async (_req, res) => {
  try {
    const result = { daily: [], weekly: [] };

    for (const type of ['daily', 'weekly']) {
      const dir = join(REPORTS_DIR, type);
      if (existsSync(dir)) {
        const files = await readdir(dir);
        result[type] = files
          .filter(f => f.endsWith('.md'))
          .sort()
          .reverse();
      }
    }

    res.json(result);
  } catch (err) {
    res.status(500).json({ error: 'Failed to list reports', detail: err.message });
  }
});

app.get('/api/reports/:type/:filename', async (req, res) => {
  try {
    const { type, filename } = req.params;
    if (!['daily', 'weekly'].includes(type)) {
      return res.status(400).json({ error: 'Invalid report type' });
    }
    // Sanitize filename
    const safeName = filename.replace(/[^a-zA-Z0-9._\-\[\]]/g, '');
    const filePath = join(REPORTS_DIR, type, safeName);

    if (!existsSync(filePath)) {
      return res.status(404).json({ error: 'Report not found' });
    }

    const content = await readFile(filePath, 'utf-8');
    res.json({ filename: safeName, type, content });
  } catch (err) {
    res.status(500).json({ error: 'Failed to read report', detail: err.message });
  }
});

// --- Bid Tracking ---

const VALID_BID_STATUSES = ['reviewing', 'preparing_bid', 'bid_submitted', 'won', 'lost', 'cancelled', 'no_bid'];

app.get('/api/bid-tracking', async (_req, res) => {
  try {
    const data = await readJSON('bid_tracking.json');
    res.json(data.items || []);
  } catch (err) {
    res.status(500).json({ error: 'Failed to read bid_tracking.json', detail: err.message });
  }
});

app.patch('/api/bid-tracking/:ikn', async (req, res) => {
  try {
    const iknParam = decodeURIComponent(req.params.ikn);
    const { status, bid_amount, bid_date, result_date, notes, loss_reason } = req.body;

    if (!status || !VALID_BID_STATUSES.includes(status)) {
      return res.status(400).json({
        error: `Invalid status. Must be one of: ${VALID_BID_STATUSES.join(', ')}`,
      });
    }

    const filePath = join(DATA_DIR, 'bid_tracking.json');
    const data = JSON.parse(await readFile(filePath, 'utf-8'));
    if (!data.items) data.items = [];

    let item = data.items.find(i => i.ikn === iknParam);
    const now = new Date().toISOString();

    if (!item) {
      // Create new entry — copy basic info from tender_decisions if available
      item = { ikn: iknParam, title: null, authority: null, province: null, created_at: now };
      try {
        const decisions = await readJSON('tender_decisions.json');
        const tender = (decisions.items || []).find(t => t.ikn === iknParam);
        if (tender) {
          item.title = tender.title || null;
          item.authority = tender.authority || null;
          item.province = tender.province || null;
        }
      } catch {
        // tender_decisions not available — continue without extra fields
      }
      data.items.push(item);
    }

    // Update fields
    item.status = status;
    if (bid_amount !== undefined) item.bid_amount = bid_amount;
    if (bid_date !== undefined) item.bid_date = bid_date;
    if (result_date !== undefined) item.result_date = result_date;
    if (notes !== undefined) item.notes = notes;
    if (loss_reason !== undefined) item.loss_reason = loss_reason;
    item.updated_at = now;
    data.updated_at = now;

    await writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
    res.json(item);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update bid tracking', detail: err.message });
  }
});

// PATCH: update operator notes and manual label for a tender
app.patch('/api/tenders/:ikn', async (req, res) => {
  try {
    const iknParam = decodeURIComponent(req.params.ikn);
    const { operator_notes, operator_label } = req.body;

    const validLabels = ['none', 'priority', 'watch', 'reject', 'never_show_similar'];

    if (operator_label && !validLabels.includes(operator_label)) {
      return res.status(400).json({ error: `Invalid label. Must be one of: ${validLabels.join(', ')}` });
    }

    const filePath = join(DATA_DIR, 'tender_decisions.json');
    const data = JSON.parse(await readFile(filePath, 'utf-8'));

    const item = (data.items || []).find(t => t.ikn === iknParam);
    if (!item) {
      return res.status(404).json({ error: 'Tender not found in decisions' });
    }

    if (operator_notes !== undefined) {
      item.operator_notes = operator_notes;
    }
    if (operator_label !== undefined) {
      item.operator_label = operator_label;
    }

    await writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
    res.json(item);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update tender', detail: err.message });
  }
});

// SPA fallback for production
if (existsSync(distDir)) {
  app.get('*', (_req, res) => {
    res.sendFile(join(distDir, 'index.html'));
  });
}

const PORT = process.env.PORT || 3099;
app.listen(PORT, () => {
  console.log(`\n  Koç Büro Tender Dashboard API`);
  console.log(`  → http://localhost:${PORT}\n`);
});
