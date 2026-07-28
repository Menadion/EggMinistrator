# EggMinistrator

A stationary, camera-based egg inspection system that uses AI image processing to inspect,
grade, and count eggs — replacing manual visual inspection and handwritten inventory logs for
a local egg production and distribution business (LH Deli).

A capstone prototype: one inspection station, built to prove the approach, not a commercial
product.

Built with **Python + OpenCV + TensorFlow** (AI), a **React + Vite** dashboard over **MySQL**, and
an **ESP32-CAM** capture rig. Inference runs on the computer, not the ESP32.

> ⚠️ **Unresolved: the dashboard stack.** Ver4 of the capstone paper (p. — "Technology") commits to
> a dashboard "developed using **PHP**, HTML, CSS, JavaScript, and MySQL running on a local XAMPP
> server." The code in `dashboard/` is **React + Vite + Tailwind**, with no PHP. One of the two has
> to move — either the paper is updated to name the real stack, or the dashboard is rebuilt in PHP.
> **Do not let this reach the defense unreconciled.**

## How it works — one capture, two kinds of finding

Each egg is imaged **once**, under **candling illumination (transillumination)** — light passing
through the shell. There is no second, reflected-light photo. That single frame produces two
different kinds of result:

| Kind | Examples | What happens to the egg |
|---|---|---|
| **Internal quality** | blood and meat spots, air cell size | graded / downgraded |
| **Shell condition** | large cracks via light leakage, gross shell damage | rejected |

**What the system does not detect:** surface dirt and shell discoloration (reflected-light features
the candling frame cannot show — and eggs are cleaned upstream anyway), micro-cracks
(unresolvable by any optical method), and **embryo development / balut routing** — descoped as of
Ver4, and absent from both scope sections.

## What it does

- Captures one candling image per egg at a fixed, light-sealed station (ESP32-CAM over Wi-Fi).
- Classifies quality from that frame — internal features, large cracks, gross shell damage.
- Grades **size by weight** (load cell + HX711).
- Counts inspected eggs automatically.
- Logs every result to a MySQL database and shows live results, daily stats, history, and
  reports on a web dashboard.
- Lets authorized staff **override** an AI classification.

## Project layout

Four code subsystems that run in parallel, each with its own README:

- **[`firmware/`](firmware/)** — the ESP32-CAM capture sketch.
- **[`ai/`](ai/)** — the model: training (Colab) and inference (Python / OpenCV / TensorFlow).
- **[`dashboard/`](dashboard/)** — the web dashboard (React + Vite + Tailwind; mock data only, no
  database wiring yet).
- **[`database/`](database/)** — the canonical MySQL schema.

Plus two reference folders: **[`hardware/`](hardware/)** (wiring, bill of materials, enclosure
model) and **[`docs/`](docs/)** (diagrams and design images).

## Running it

Each subsystem sets up independently — start with the README in the folder you're working on.
The dashboard runs on Node (`npm install && npm run dev` in `dashboard/`) and currently reads
**mock data** — nothing is wired to MySQL yet. The schema in `database/` still has to be imported
into XAMPP for the backend work. The AI side runs from `ai/`. The dataset is **not** in this repo
(too large for git) — see [`ai/README.md`](ai/README.md) for where it lives.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for subsystem ownership, branch/PR flow, and commit
conventions.
