# EggMinistrator

A stationary, camera-based egg inspection system that uses AI image processing to inspect,
grade, and count eggs — replacing manual visual inspection and handwritten inventory logs for
a local egg production and distribution business (LH Deli).

A capstone prototype: one inspection station, built to prove the approach, not a commercial
product.

Built with **Python + OpenCV + TensorFlow** (AI), **PHP + MySQL on XAMPP** (dashboard), and an
**ESP32-CAM** capture rig. Inference runs on the computer, not the ESP32.

## What it does

- Captures egg images at a fixed, evenly lit station (ESP32-CAM over Wi-Fi).
- Classifies **external quality** from the image — cracks, discoloration, damaged shells.
- Assesses **internal quality** via candling (transillumination).
- Grades **size by weight** (load cell + HX711).
- Counts inspected eggs automatically.
- Logs every result to a MySQL database and shows live results, daily stats, history, and
  reports on a web dashboard.
- Lets authorized staff **override** an AI classification.

## Project layout

Four subsystems that run in parallel, each with its own README:

- **[`firmware/`](firmware/)** — the ESP32-CAM capture sketch.
- **[`ai/`](ai/)** — the model: training (Colab) and inference (Python / OpenCV / TensorFlow).
- **[`dashboard/`](dashboard/)** — the PHP / MySQL web dashboard, served on XAMPP.
- **[`database/`](database/)** — the canonical MySQL schema.

Hardware wiring and the bill of materials are in **[`hardware/`](hardware/)**.

## Running it

Each subsystem sets up independently — start with the README in the folder you're working on.
The dashboard needs XAMPP and the schema imported from `database/`; the AI side runs from
`ai/`. The dataset is **not** in this repo (too large for git) — see
[`ai/README.md`](ai/README.md) for where it lives.

> The dashboard is PHP + MySQL, so **GitHub Pages can't host it** — the repo stores the code, a
> web host runs it.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for subsystem ownership, branch/PR flow, and commit
conventions.
