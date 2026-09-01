# EggMinistrator

A stationary, camera-based egg inspection system that uses AI image processing to inspect,
grade, and count eggs — replacing manual visual inspection and handwritten inventory logs at
**LH Deli**, the egg production and distribution operation of **Leong Hup Philippines Inc.**

A capstone prototype: one inspection station, built to prove the approach, not a commercial
product.

Built with **Python + OpenCV + TensorFlow** (AI), a **React + Vite** dashboard over **MySQL**, a
**USB webcam** for capture, and an **ESP32** weight node reading a load cell over Wi-Fi.
Inference runs on the computer, not the microcontroller.

Parts list in `hardware/bill-of-materials.md`. Board details, including which ESP32 this actually
is, in `firmware/README.md`.

## How it works — one capture, one verdict

Each egg is imaged **once**, under **candling illumination (transillumination)** — light passing
through the shell. There is no second, reflected-light photo. The model returns **one verdict per
egg** and does not name which defect it saw.

| Verdict | What it means | What happens to the egg |
|---|---|---|
| `good` | No defect visible under transillumination | accepted |
| `defective` | Cracks revealed by light leakage, or gross shell damage | rejected |
| `not_an_egg` | Empty platform, a hand, a misload | recorded, not counted as an egg |

"Internal quality" here means cracks revealed by transillumination and nothing else — **not** blood
or meat spots, and not air cell size. The scope and the reasons are in `ai/README.md`; the paper
agrees, FR-14 reads *"Detect large cracks and gross shell damage."*

**What the system does not detect:**

- **blood and meat spots, air cell size** — out of scope since 2026-08-20, above;
- **surface dirt and shell discoloration** — reflected-light features a candling frame cannot show.
  *(Do not restore "eggs are cleaned upstream anyway" — that clause was cut 2026-08-19: the station
  sits upstream of the wash, and the wash was never removing all the dirt.)*
- **micro-cracks** — unresolvable by any optical method;
- **embryo development / balut routing** — out of scope **by input**: fertilised eggs are separated
  upstream into a different production line, so an embryo cannot reach the station at all. The model
  has no embryo class.

## What it does

- Captures one candling image per egg at a fixed, light-sealed station (USB webcam on the laptop),
  with weight read by an ESP32 node over Wi-Fi.
- Classifies quality from that frame — cracks revealed by light leakage, gross shell damage.
- Grades **size by weight** (load cell + HX711).
- Counts inspected eggs automatically.
- Logs every result to a MySQL database and shows live results, daily stats, history, and
  reports on a web dashboard.
- Lets authorized staff **override** an AI classification.

## Project layout

Five code subsystems that run in parallel, each with its own README:

- **[`firmware/`](firmware/)** — the ESP32 weight node (reads the HX711, posts over Wi-Fi).
  **Written (535 lines), never compiled and never flashed.**
- **[`ai/`](ai/)** — the model: training and inference (Python / OpenCV / TensorFlow), both run
  locally. Plus `listen_station.py`, the loop that shoots the webcam and posts the verdict back.
- **[`backend/`](backend/)** — the Node API the dashboard and the board both talk to: auth,
  inspections, assessments, the FR-03 override. No README yet.
- **[`dashboard/`](dashboard/)** — the web dashboard (React + Vite + Tailwind), reading live records
  from the database through `backend/`.
- **[`database/`](database/)** — the canonical MySQL schema.

Plus **[`hardware/`](hardware/)** — wiring, bill of materials, enclosure model and design images.

The repo is **code only**. The capstone paper, the RRL and the team's working notes live in a
local-only `docs/` folder, gitignored since 2026-08-01 on the consultant's ruling that the GitHub
repo stays code and documentation is handled at the defense. See the `docs/` block in `.gitignore`.

## Running it

**On a machine that has never run this, start with [`SETUP.md`](SETUP.md).** It covers the
whole chain from an empty laptop to a running station, in the order that works, and flags the
two steps that destroy data or take an evening if you get them wrong.

Once set up, `run-eggministrator.bat` brings the whole stack up in one command and
`stop-eggministrator.bat` takes it down.

Each subsystem also sets up independently — start with the README in the folder you're working on.

The dashboard runs on Node (`npm install && npm run dev` in `dashboard/`) and reads **live records
from the database**, through the API in `backend/` — so it needs `backend/` running and the schema in
`database/` imported into XAMPP first. *(It no longer runs on mock data; `src/data/mockData.js`
survives only as default date bounds and the size names and chart colours.)*

The AI side runs from `ai/`, from the repo root. The dataset is **not** in this repo (too large for
git) — see [`ai/README.md`](ai/README.md) for where it lives.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for subsystem ownership, branch/PR flow, and commit
conventions.
