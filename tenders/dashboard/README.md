# Koç Büro Tender Radar — Dashboard

Local operator dashboard for inspecting tender scan results, scores, suppressed items, and run health.

## Quick Start

```bash
cd tenders/dashboard
npm install
npm run dev
```

This starts both the API server (port 3099) and Vite dev server (port 5173).
Open **http://localhost:5173** in your browser.

## Production Mode

```bash
npm run build
npm run preview
```

Open **http://localhost:3099** — serves the built frontend and API from a single server.

## Architecture

- **Server**: Express.js (`server/index.js`) — reads local JSON/markdown files, serves REST API
- **Frontend**: React 18 + Vite — dark control-room UI
- **Data**: Reads from `tenders/data/*.json` and `tenders/reports/{daily,weekly}/*.md`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/run-state` | Last scan metadata |
| GET | `/api/tenders` | All scored tender decisions |
| GET | `/api/seen-tenders` | Deduplication/suppression state |
| GET | `/api/history` | Chronological event log |
| GET | `/api/reports` | List available report files |
| GET | `/api/reports/:type/:file` | Read a specific report |
| PATCH | `/api/tenders/:ikn` | Update operator notes/label |

## Dashboard Views

1. **Overview** — scan stats, top candidates
2. **Tenders** — full table with search, filters, sorting
3. **Suppressed** — inspect suppressed/rejected/silent items
4. **Reports** — rendered markdown reports
5. **Run Health** — system status, event log, counts
