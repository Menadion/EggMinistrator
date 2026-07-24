<!--
  README SKELETON — the graded landing page.
  Fill each <!-- fill --> block in your team's own words. GitHub renders this
  automatically on the repo's front page, so keep it Markdown, not a PDF.
  Delete these comment blocks as you go.
-->

# EggMinistrator

<!-- fill: one line — what it does, for whom.
     e.g. "A stationary, camera-based AI system that inspects, grades, and counts eggs
     for LH Deli, replacing manual visual inspection and handwritten inventory logs." -->

> ⚠️ Capstone / PROJMAN prototype by 5 NU Fairview students. One inspection station, not a
> commercial product.

<!-- fill: a screenshot or photo — the dashboard, or the physical station.
     The first thing a reader sees. Drop the image in docs/ and reference it:
     ![Dashboard](docs/dashboard-screenshot.png) -->

## The problem

<!-- fill: 2–3 sentences on LH Deli's manual inspection/counting/inventory process and why
     it breaks down as volume grows. -->

## Features

<!-- fill: map these to your FR list (FR-01…FR-14).
  - External quality classification (cracks, discoloration, damaged shells)
  - Candling-based internal quality assessment
  - Weight-based size grading
  - Automatic counting
  - Web monitoring dashboard (results, stats, history, reports)
  - Authorized human override of a classification (FR-03)
-->

## Tech stack

| Layer | Tech |
|---|---|
| Capture | ESP32-CAM, candling illumination, load cell + HX711 |
| AI / processing | Python, OpenCV, TensorFlow (runs on a laptop, not the ESP32) |
| Dashboard | PHP, HTML, CSS, JavaScript, MySQL on XAMPP |
| Comms | Wi-Fi (ESP32-CAM → computer) |

## Architecture

<!-- fill: link the architecture diagram in docs/. Even a hand-drawn photo beats nothing.
     One line: camera captures → laptop runs the model → results stored in MySQL → dashboard. -->

## Setup

<!-- fill: numbered steps so someone else could actually run it. Point at the per-subsystem
     READMEs (ai/, dashboard/, database/, firmware/) for detail. -->

## Live demo

<!-- fill: link once the hosted dashboard is up. Note: GitHub Pages CANNOT host this (it's PHP +
     MySQL); the repo stores the code, a web host runs it. -->

## Team

| Name | Role |
|---|---|
| Sean Kyle Ambrocio | Project Manager |
| Ricardo Antonio Jr. | Development, data, implementation |
| Jasfer Ramos | Research, UI/UX, validation |
| Daniel Ivan Renegado | Design, documentation, testing |
| Miguel Andrei Castaneda | <!-- fill: role --> |

## Dataset

<!-- fill: the dataset is NOT in this repo (too large, see CONTRIBUTING.md). State where it
     lives (Google Drive / Colab link), the class list, and image counts per class.
     Details also in ai/README.md. -->

<!-- The capstone paper is intentionally NOT in this repo — it's covered by the defense, and the
     repo is kept code-only. Any lightweight diagrams/screenshots may live in docs/. -->

