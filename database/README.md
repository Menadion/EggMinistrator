# database/

The canonical MySQL database for EggMinistrator. It stores individual egg inspections,
candling AI assessments, weight grades, and an auditable staff-override history.

## Importing locally

1. Start MySQL in XAMPP and open phpMyAdmin.
2. Import `schema.sql`. It creates the `eggministrator` database and its tables.
3. Optionally import `sample-data.sql` for development-only records.

`schema.sql` resets the EggMinistrator tables when imported. Never import it into a database
with records you need to keep without exporting them first.

## Updating an existing database

For an existing `eggministrator` database, run each file in `migrations/` once in filename order.
`20260803_add_temporary_password_security.sql` is additive: it preserves all users and adds safe
defaults (`must_change_password = 0`, no temporary-password expiry, and zero failed attempts).
It also creates the hashed session and password-change-token tables required by the backend.

`20260803_add_account_name_fields_and_restrict_roles.sql` adds nullable `first_name`,
`middle_initial`, and `last_name` fields, keeps existing `full_name` values unchanged, and limits
new roles to `admin` or `inspector`. It stops instead of changing any existing viewer account.
Existing accounts with blank structured-name fields must be updated manually in Accounts.

## Files

- `schema.sql` - canonical database definition, indexes, foreign keys, and daily summary view.
- `sample-data.sql` - optional demo users, grades, one batch, inspections, AI results, and an override.
- `migrations/` - additive updates for existing databases; do not run a migration more than once.
- `fr-04-size-classification.md` - the PNS/BAFS 321:2021 weight bands the `size_grades` table
  implements. It belongs beside the schema because it is the specification the schema follows.

## Candling model contract

Each assessment represents one candling result per inspection. The permitted `result_label` values
are `good`, `defective`, and `not_an_egg`. The last value records a misload without adding it to the
egg totals in `daily_inspection_summary`.

Size grades use the six PNS/BAFS 321:2021 bands: Pewee (under 45 g), Small (45 to under 55 g),
Medium (55 to under 60 g), Large (60 to under 65 g), Extra Large (65 to under 70 g), and Jumbo
(70 g and above).

The sample users use a shared development-only password: `password`. Replace or remove them
before any real deployment. Update the weight thresholds in `size_grades` if Leong Hup PH uses a
different grading standard.

There is no migration runner: apply tracked SQL files in `migrations/` manually for existing
databases, and keep `schema.sql` aligned for fresh installs.
