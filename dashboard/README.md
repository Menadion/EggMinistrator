# dashboard/

The responsive EggMinistrator monitoring dashboard, built with React, Vite, Tailwind CSS,
Recharts, and React Router. It currently uses sample data until the ESP32-S3 and MariaDB
connections are added.

## Run locally

1. Open a terminal in `dashboard/`.
2. Run `npm install`.
3. Run `npm run dev` and open the URL shown by Vite (normally `http://localhost:5173`).

## Structure

- `src/pages/` - login, dashboard, history, reports, and analytics page components.
- `src/components/` - reusable sidebar, layout, badges, cards, and export controls.
- `src/data/mockData.js` - all current sample inspection data.
- `src/index.css` - Tailwind entry point and application-wide styles.

The project uses hash-based routes, so routes work when deployed as static files. Later, the
existing `config.example.php` can be used when a PHP API is added for MariaDB and device data.
