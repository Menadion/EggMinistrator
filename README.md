# EggMinistrator

A stationary, camera-based egg inspection system that uses AI image processing to inspect,
grade, and count eggs — replacing manual visual inspection and handwritten inventory logs for
a local egg production and distribution business (LH Deli).

A capstone prototype: one inspection station, built to prove the approach, not a commercial
product.

Built with **Python + OpenCV + TensorFlow** (AI), **PHP + MySQL on XAMPP** (dashboard), and an
**ESP32-CAM** capture rig. Inference runs on the computer, not the ESP32.

## How it works — one capture, three kinds of finding

Each egg is imaged **once**, under **candling illumination (transillumination)** — light passing
through the shell. There is no second, reflected-light photo. That single frame produces three
different kinds of result:

| Kind | Examples | What happens to the egg |
|---|---|---|
| **Internal quality** | blood and meat spots, air cell size | graded / downgraded |
| **Shell condition** | large cracks via light leakage, gross shell damage | rejected |
| **Routing** | embryo development | separated for **balut** — *not a defect* |

That third row matters: a balut egg is intentionally fertilized product, not a low-quality egg.
Routing and quality judgment are separate outputs, and the code should keep them separate.

**What the system does not detect:** surface dirt and shell discoloration (reflected-light features
the candling frame cannot show — and eggs are cleaned upstream anyway), and micro-cracks
(unresolvable by any optical method).

## What it does

- Captures one candling image per egg at a fixed, light-sealed station (ESP32-CAM over Wi-Fi).
- Classifies quality from that frame — internal features, large cracks, gross shell damage.
- Separates eggs showing embryo development for balut handling.
- Grades **size by weight** (load cell + HX711).
- Counts inspected eggs automatically.
- Logs every result to a MySQL database and shows live results, daily stats, history, and
  reports on a web dashboard.
- Lets authorized staff **override** an AI classification.

## Project layout

Four code subsystems that run in parallel, each with its own README:

- **[`firmware/`](firmware/)** — the ESP32-CAM capture sketch.
- **[`ai/`](ai/)** — the model: training (Colab) and inference (Python / OpenCV / TensorFlow).
- **[`dashboard/`](dashboard/)** — the PHP / MySQL web dashboard, served on XAMPP.
- **[`database/`](database/)** — the canonical MySQL schema.

Plus two reference folders: **[`hardware/`](hardware/)** (wiring, bill of materials, enclosure
model) and **[`docs/`](docs/)** (diagrams and design images).

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
