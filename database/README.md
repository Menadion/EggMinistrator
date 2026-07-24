# database/

How the MySQL database is versioned.

- `schema.sql` — the **canonical** table definitions. Export from phpMyAdmin and commit here;
  this is how schema changes get tracked. Re-import to apply.
- `sample-data.sql` — optional seed rows for testing (no real production data).

No migration framework — schema changes land in `schema.sql` and everyone re-imports.
