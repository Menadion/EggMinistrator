# database/

The canonical MySQL database for EggMinistrator. It stores individual egg inspections,
external and candling AI assessments, weight grades, and an auditable staff-override history.

## Importing locally

1. Start MySQL in XAMPP and open phpMyAdmin.
2. Import `schema.sql`. It creates the `eggministrator` database and its tables.
3. Optionally import `sample-data.sql` for development-only records.

`schema.sql` resets the EggMinistrator tables when imported. Never import it into a database
with records you need to keep without exporting them first.

## Files

- `schema.sql` - canonical database definition, indexes, foreign keys, and daily summary view.
- `sample-data.sql` - optional demo users, grades, one batch, inspections, AI results, and an override.

The sample users use a shared development-only password: `password`. Replace or remove them
before any real deployment. Update the weight thresholds in `size_grades` if LH Deli uses a
different grading standard.

No migration framework is used yet: schema changes land in `schema.sql` and everyone re-imports.
