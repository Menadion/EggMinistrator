# dashboard/

The responsive EggMinistrator monitoring dashboard, built with React, Vite, Tailwind CSS, Recharts,
and React Router. It reads **live inspection records from the database**, through the Node API in
[`../backend/`](../backend/).

## Run locally

The dashboard does not run usefully on its own — it needs the API and the database behind it.

1. Import `../database/schema.sql` into MySQL/MariaDB via XAMPP (see [`../database/`](../database/)).
2. Start the API: `npm install && npm start` in [`../backend/`](../backend/), with a `.env` in place.
3. Open a terminal in `dashboard/`.
4. Run `npm install`.
5. Run `npm run dev` and open the URL shown by Vite (normally `http://localhost:5173`).

Without step 2 the pages load and every data panel reports that it cannot reach the records.

## Structure

- `src/pages/` — login, dashboard, history, reports, analytics, and accounts page components.
- `src/components/` — reusable sidebar, layout, badges, cards, and export controls.
- `src/auth/AuthContext.jsx` — session token handling and `authenticatedFetch`, which every data
  call goes through.
- `src/hooks/useDatabaseInspections.js` — the shared fetch of `/api/inspections`.
- `src/data/mockData.js` — **no longer the data source.** What survives is used as default date
  bounds for the Reports and Analytics filters, plus the size names and chart colours. Inspection
  figures on every page come from the database.
- `src/index.css` — Tailwind entry point and application-wide styles.

The project uses hash-based routes, so routes work when deployed as static files.

## What the pages read

| Page | Source |
|---|---|
| Login, Accounts | `backend/routes/authRoutes.js` |
| Dashboard, History, Reports, Analytics | `GET /api/inspections` |
| Analytics summaries | `POST /api/analytics/insights` (cloud model, needs internet) |
| History override dropdown | `PATCH /api/inspections/:code/override` — this is FR-03 |

⚠️ **`config.example.php` in this folder is a leftover** from the PHP era and nothing reads it.
It is not referenced by any code. Safe to delete — left in place only because removing files is not
this pass's job.

⚠️ **The override dropdown on the History page is FR-03 and is delivered.** It has been deleted once
by mistake (`f6fa589`, restored in `5b104fd`) by someone acting on an audit item about the separate
`staff_overrides` table. **They are two different things.** Check which one you are looking at before
touching anything with "override" in the name — see `CONTRACT.md` §7.
