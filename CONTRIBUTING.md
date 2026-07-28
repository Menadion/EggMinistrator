# Contributing to EggMinistrator

Five-person capstone, one working prototype. The repo has four code subsystems that move in
parallel — **firmware** (ESP32-CAM), **ai** (Python/OpenCV/TensorFlow), **dashboard**
(PHP/MySQL on XAMPP), and **database** (the schema) — plus **hardware** and **docs** for build
reference. The best changes are focused, land in the right folder, and are tested before they're
committed.

**One thing to know before you touch anything:** each egg is captured **once**, under candling
(backlit) illumination. There is no second reflected-light photo. Surface dirt and shell
discoloration are therefore out of scope. **Balut / embryo routing was descoped in Ver4** — the
system emits a quality verdict only, with no routing output. See the root [README](README.md) and
`docs/context.md`.

## Subsystems

Work in the folder for your part; don't reach into someone else's without a heads-up. Who did
what is tracked by commit history, not a table here.

| Folder | Stack |
|---|---|
| `firmware/` | ESP32-CAM capture sketch |
| `ai/` | Python, OpenCV, TensorFlow, Colab |
| `dashboard/` | React, Vite, Tailwind, Recharts |
| `database/` | `schema.sql`, seed data |
| `docs/`, `hardware/` | diagrams, manuals, BOM |

### The dashboard stack (settled 2026-07-28)

The paper used to say the dashboard was "developed using **PHP**, HTML, CSS, JavaScript, and MySQL
running on a local XAMPP server." It isn't. The merged `dashboard/` is **React + Vite + Tailwind**
with no PHP.

**Resolved in favour of the code:** the paper is being corrected to name React + Vite. MySQL and
XAMPP stay as they were. Build on React; don't add PHP to `dashboard/` expecting it to match the
old description.

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

- **dashboard:** `npm run build` must succeed, then `npm run dev` and **load the page in the
  browser** and confirm the flow actually works. A clean build only proves it compiles.
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
- **Real credentials.** No hosting passwords, DB passwords, or registrar logins. Commit an
  example config with placeholders (`.env.example`, or `config.example.php` if a PHP backend
  lands); each person copies it locally to a file `.gitignore` keeps out.
- **Generated junk.** `venv/`, `__pycache__/`, `.vscode/`, `.DS_Store` — all already ignored.

## Don't

- Don't introduce a **further** build tool, bundler, or framework without agreeing first. The
  React + Vite reversal has been accepted and written into the paper; don't stack another
  unagreed choice on top of it.
- Don't add features or abstractions beyond the task's scope.
- Don't commit a trained model over ~100MB — link it instead.
