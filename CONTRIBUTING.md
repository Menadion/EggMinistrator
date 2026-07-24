# Contributing to EggMinistrator

Five-person capstone, one working prototype. The repo has three subsystems that move in
parallel — **firmware** (ESP32-CAM), **ai** (Python/OpenCV/TensorFlow), and **dashboard**
(PHP/MySQL on XAMPP) — plus **database** and **hardware** docs. The best changes are focused,
land in the right folder, and are tested before they're committed.

## Subsystems

Work in the folder for your part; don't reach into someone else's without a heads-up. Who did
what is tracked by commit history, not a table here.

| Folder | Stack |
|---|---|
| `firmware/` | ESP32-CAM capture sketch |
| `ai/` | Python, OpenCV, TensorFlow, Colab |
| `dashboard/` | PHP, MySQL, HTML/CSS/JS, XAMPP |
| `database/` | `schema.sql`, seed data |
| `docs/`, `hardware/` | diagrams, manuals, BOM |

## Branches — so five people don't overwrite each other

- **One branch per person or per feature:** `sean/dashboard`, `ai-model`, `esp32-capture`.
- **Never commit straight to `main`.** Open a **pull request** into `main`, even a self-approved
  one — it leaves a visible record a professor can scroll.
- Pull `main` into your branch before opening the PR, so you resolve conflicts on your side.
- **Everyone commits something.** A repo where one person made 94 of 100 commits invites the
  question of who actually did the work.

## Before a change

- One bug fix or feature per commit. Keep it focused and reviewable.
- Avoid broad rewrites or formatting-only churn unless restructuring *is* the change.
- **Don't mix a file *move* with a file *rewrite* in one commit** — relocating and restructuring
  are different operations; keeping them separate keeps a break bisectable.

## Running checks (the smallest relevant one, before you commit)

There is no automated test suite — verification is manual, per subsystem:

- **dashboard:** `php -l path/to/file.php` syntax-checks a PHP file, then **load the page in the
  browser** and confirm the flow actually works. `php -l` only checks syntax.
- **ai:** re-run the training notebook / inference script end-to-end on a couple of sample images
  and confirm it classifies without erroring. Note the model's accuracy in `ai/README.md`.
- **firmware:** compile/verify the sketch in the Arduino IDE before pushing.
- **database:** land schema changes in `database/schema.sql` (the canonical dump) and re-import
  to apply. No migration framework.

## Commits

- **Conventional prefixes:** `feat`, `fix`, `refactor`, `chore`, `docs`. Optional scope, e.g.
  `feat(dashboard): …`, `fix(ai): …`.
- Messages say **what changed**: `Add weight logging to inspection endpoint`, not `update`.
- One commit per task; granular and bisectable.
- Never amend a pushed commit — always make a new one.

## Never commit

- **The dataset.** Thousands of egg photos blow past GitHub's limits and can't be cleanly
  removed once they're in history. Keep them in Google Drive / Colab and link them in
  `ai/README.md` with the class list and image counts. (`.gitignore` already blocks `*.jpg`
  etc. — don't force-add them.)
- **Real credentials.** No hosting passwords, DB passwords, or registrar logins. Commit
  `dashboard/config.example.php` with placeholders; each person copies it to `config.php`
  locally, which `.gitignore` keeps out.
- **Generated junk.** `venv/`, `__pycache__/`, `.vscode/`, `.DS_Store` — all already ignored.

## Don't

- Don't introduce a build tool or bundler without agreeing first — the dashboard is
  deliberately no-build (edit PHP/CSS/JS and refresh).
- Don't add features or abstractions beyond the task's scope.
- Don't commit a trained model over ~100MB — link it instead.
