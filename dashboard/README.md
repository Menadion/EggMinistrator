# dashboard/

The web monitoring dashboard — PHP, HTML, CSS, JavaScript, MySQL, served on **XAMPP**. Shows
live results, counts, daily stats, history, and reports.

## Local setup

1. Install XAMPP; start Apache + MySQL.
2. Import the schema: `database/schema.sql` (via phpMyAdmin).
3. Copy `config.example.php` → `config.php` and fill in your local DB credentials.
   `config.php` is gitignored — never commit it.
4. Put the dashboard under your XAMPP `htdocs/` and open it in the browser.

## Structure

- `public/` — PHP pages, CSS, JS.
- `config.example.php` — DB-config template (copy to `config.php` locally).

> **GitHub Pages cannot host this** — it serves static files only, and this is PHP + MySQL. The
> repo stores the code; a real web host runs it.
