# EggMinistrator

A stationary, camera-based egg inspection system that uses AI image processing to inspect,
grade, and count eggs — replacing manual visual inspection and handwritten inventory logs at
**LH Deli**, the egg production and distribution operation of **Leong Hup Philippines Inc.**

A capstone prototype: one inspection station, built to prove the approach, not a commercial
product.

Built with **Python + OpenCV + TensorFlow** (AI), a **React + Vite** dashboard over **MySQL**, a
**USB webcam** for capture, and an **ESP32-S3** weight node reading a load cell over Wi-Fi.
Inference runs on the computer, not the microcontroller.

> **Hardware descoped 2026-08-07.** The build was previously an **ESP32-CAM** capture rig. For time
> constraints it is now webcam + laptop + HX711 + load cell, with the already-owned ESP32-S3
> repurposed from programmer to networked weight node. See `hardware/bill-of-materials.md`.

> **Settled 2026-07-28:** the paper previously described a **PHP** dashboard on XAMPP. The code is
> React + Vite and it builds, so the paper is being updated to match the code rather than the
> reverse. MySQL and XAMPP stay. The "software cost is effectively zero" argument is unaffected,
> since Node, React and Vite are free too.

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

- Captures one candling image per egg at a fixed, light-sealed station (USB webcam on the laptop),
  with weight read by an ESP32-S3 node over Wi-Fi.
- Classifies quality from that frame — internal features, large cracks, gross shell damage.
- Grades **size by weight** (load cell + HX711).
- Counts inspected eggs automatically.
- Logs every result to a MySQL database and shows live results, daily stats, history, and
  reports on a web dashboard.
- Lets authorized staff **override** an AI classification.

## Project layout

Four code subsystems that run in parallel, each with its own README:

- **[`firmware/`](firmware/)** — the ESP32-S3 weight node (reads the HX711, posts over Wi-Fi).
  **Not written yet.**
- **[`ai/`](ai/)** — the model: training and inference (Python / OpenCV / TensorFlow), both run
  locally.
- **[`dashboard/`](dashboard/)** — the web dashboard (React + Vite + Tailwind; mock data only, no
  database wiring yet).
- **[`database/`](database/)** — the canonical MySQL schema.

Plus **[`hardware/`](hardware/)** — wiring, bill of materials, enclosure model and design images.

The repo is **code only**. The capstone paper, the RRL and the team's working notes are handled at
the defense and are not tracked here.

## Running it

Each subsystem sets up independently — start with the README in the folder you're working on.
The dashboard runs on Node (`npm install && npm run dev` in `dashboard/`) and currently reads
**mock data** — nothing is wired to MySQL yet. The schema in `database/` still has to be imported
into XAMPP for the backend work. The AI side runs from `ai/`. The dataset is **not** in this repo
(too large for git) — see [`ai/README.md`](ai/README.md) for where it lives.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for subsystem ownership, branch/PR flow, and commit
conventions.
