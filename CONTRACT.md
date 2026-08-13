# EggMinistrator — System Contract

**Paste this file into your AI assistant before asking it to write anything for this project.**

It exists so that five people working with five different AI tools build one system instead of five.
It contains what has been decided and how the parts connect. It does not contain opinions about
anyone's work.

**Owner: M.** One editor, so it cannot drift. If something here is wrong or out of date, message M
rather than editing it, and it gets fixed in one place.

*Last updated: 2026-08-13*

---

## 1. What the system is, in one paragraph

A single, stationary inspection station for eggs. An egg is placed on the station by hand. One
**candling** photo is taken (light shone through the shell, so the camera sees the inside), and a
load cell weighs the same egg. An AI model classifies the photo, the weight determines a size grade,
and the result is written to a local MySQL database and shown on a web dashboard. It replaces manual
inspection and handwritten tally sheets at a commercial egg operation.

The reference operation runs **white and tinted** (partially pigmented) shells. Not brown.

> ⚠️ The paper title is being revised as of 2026-08-04 and is not final. Do not quote the old title.

---

## 2. Who owns what

| Folder | Owner | Contains |
|---|---|---|
| `ai/` | M | OpenCV + TensorFlow/Keras classifier and inference |
| `database/` | R | MySQL schema, migrations, sample data |
| `dashboard/` | R | React + Vite frontend |
| `backend/` | R | Node/Express API: auth, inspection queries, Gemini insight service |
| `firmware/` | J | ESP32 firmware: camera capture, load cell reading, Wi-Fi |
| `hardware/` | J | Enclosure, bill of materials, wiring |
| `docs/` | shared | Local only, gitignored, not in the repo |

**The seams between folders belong to M** as project manager, because no folder owns them. If your
work crosses a boundary, that is a conversation, not a commit.

---

## 3. Decisions that are settled. Do not re-open or invent alternatives.

1. **One photo per egg, and it is a candling photo.** There is no separate external-quality photo.
   Anything describing two images per egg is out of date.
2. **The model emits exactly three classes: `good`, `defective`, `not_an_egg`.** One verdict per
   egg. It does not report which defect it found. (This is "Decision G".)
3. **Weight is not vision.** Size grading comes from the load cell, not the camera. Accuracy target
   is ±2 g.
4. **Size grades follow PNS/BAFS 321:2021 weight bands**, stored in the `size_grades` table.
5. **Embryo development and balut are out of scope, by input.** The reference operation receives
   only unfertilised eggs; fertilised eggs are separated upstream into a different production line
   and never reach the station. An embryo cannot arrive here, so nothing needs to detect one.
6. **Dirt is out of scope**, because eggs are washed upstream before they reach the station.
7. **The stack is fixed:** Python for `ai/`, Node/Express for the backend, React + Vite for the
   dashboard, MySQL for the database, ESP32 for firmware. **The paper says PHP in one place. The
   paper is wrong.** Do not let an AI generate PHP.
8. **A `not_an_egg` scan is recorded, not discarded.** It writes an `egg_inspections` row
   dispositioned `no_egg` plus its linked `ai_assessments` row, and every egg metric filters it back
   out. Misload rate is real diagnostic data about the station and we keep it. The alternative —
   write nothing and only warn on the station screen — was **considered and rejected 2026-08-13**;
   see section 7.

---

## 4. The interfaces

This is the part that matters most. These are the handoffs between people.

### 4.1 Firmware → server

**The board sends weight. It does not send an image.** That changed with the 2026-08-07 descope: the
camera is a USB webcam on the laptop, and the ESP32-S3 reads the load cell through the HX711, which
has no USB and cannot reach a laptop on its own.

**Transport: HTTP over Wi-Fi, never USB serial.** The board's USB cable carries power only. This is
not a style preference — `hardware/bill-of-materials.md` is explicit that a USB *data* path makes the
board a peripheral attached to a computer, which contradicts the paper's title and §2.2. Whoever
touches this: the weight leaves over the network.

#### The three calls, in order

```
1. BOARD  →  POST /api/inspections            { "weight_g": 58.23 }
   SERVER →  creates the egg_inspections row, replies { "id": 41 }

2. LAPTOP →  POST /api/inspections/41/assessment
             the six fields from classify.py (see 4.3) + raw_result
   SERVER →  writes the ai_assessments row and sets the disposition

3. BOARD  →  GET /api/inspections/41/result   (polled, ~500 ms)
   SERVER →  { "status": "pending" } until step 2 lands,
             then { "label": "good", "confidence": 0.83 }
   BOARD  →  drives the LCD, LEDs and buzzer (FR-15). Gives up after 5 s.
```

**Why the board polls instead of being pushed to.** Pushing means the laptop has to know the board's
IP, which means a static address or a DHCP reservation on whatever router is in the room. That is one
more thing to configure and one more thing to break **on defense day, on an unfamiliar network**.
Polling only requires the board to reach the server, so the board makes outbound requests and nothing
has to know where it is.

**Why the server creates the row and hands back an id.** It is the only way `inspection_id` reaches
the assessment write. The classifier cannot know it — see 4.3 — so step 1 mints it and step 2 quotes
it back. Weight and verdict never have to be matched up by timestamp.

**Authentication.** The board cannot log in as a user. It sends a device key in an `X-Device-Key`
header, and the value lives in `backend/.env`, never in the repo and never in the sketch. J's branch
already assumed this exact header, so it is not a new idea, only a written-down one.

> 🔧 **R's to confirm, and rename freely.** The route names above are a proposal so the firmware has
> something concrete to build against — **the shapes are the contract, the spellings are yours.** In
> the sketch each URL is a single constant, so a rename costs one line. Three things are genuinely
> open: what the `GET` returns while pending, whether `inspection_images.file_path` is written in
> step 2 or separately, and the `class` → disposition mapping (proposed: `good` → `accepted`,
> `defective` → `rejected`, `not_an_egg` → `no_egg`, per settled decision 8).

> ⚠️ **None of these endpoints exist yet.** The backend on `main` serves `GET /api/inspections` and
> can receive an inspection through no route at all. Until step 1 exists, nothing downstream of the
> load cell can run end to end — this sits alongside the empty dataset in section 7.

### 4.2 Image → classifier

`ai/inference/classify.py` opens the image and resizes it to **224 x 224**.

**Colour order matters and is a silent bug if wrong.** OpenCV's `imread` returns channels in **BGR**
order. Keras models trained with the standard image loaders expect **RGB**. The requirement is that
the channel order at inference matches the channel order used at training. Do not assume either one
is "correct" on its own.

### 4.3 Classifier → database

`classify.py` emits exactly six fields *(was three until 2026-08-13)*:

```json
{
  "image": "<filename>",
  "class": "good | defective | not_an_egg",
  "confidence": 0.0,
  "model_name": "candling-classifier",
  "model_version": "0.3.0+20260813T144500Z",
  "inference_time_ms": 105
}
```

`class` uses the Decision G values verbatim, with underscores, lowercase.

**The classifier does not fill the whole row.** Of the `ai_assessments` columns below, `classify.py`
supplies six and the server supplies the rest: `inspection_id` (the server owns it — the classifier
has never heard of it), `assessment_type` (constant `'candling'`), `is_defect_detected` (derive it
from `class`), and `assessed_at` (database default). Do not wait on `ai/` for those four.

These land in the `ai_assessments` table:

| Column | Type | Note |
|---|---|---|
| `result_label` | `ENUM('good','defective','not_an_egg')` | must match Decision G exactly |
| `confidence_score` | `DECIMAL(5,4)` | 0.0000 to 1.0000 |
| `assessment_type` | `ENUM('candling')` | one value only, by decision 1 above |
| `model_name` | `VARCHAR(100)` | nullable |
| `model_version` | `VARCHAR(50)` | **`NOT NULL`** |
| `inference_time_ms` | `INT UNSIGNED` | nullable |
| `raw_result` | `LONGTEXT` | nullable; the verbatim JSON line above |

> ✅ **Settled 2026-08-13 — `model_version` is supplied by the classifier, not typed by hand.**
> `train.py` writes `ai/models/version.json` in the same run that saves the weights, and
> `classify.py` reads it and reports it. The string is `MODEL_VERSION` plus the UTC timestamp of the
> training run, e.g. `0.3.0+20260813T144500Z`. Fits `VARCHAR(50)`.
>
> **Why not a hardcoded constant.** A version typed into `classify.py` is a sticker applied by hand:
> retrain, forget to bump it, and the database records a version that does not describe the weights
> that produced the row. Same failure as a committed `classes.json`. ⚠️ `version.json` now travels
> with `egg.keras` and `classes.json` — **all three or none.**

> ✅ **Settled 2026-08-13 — `raw_result` holds the full JSON line, stored verbatim.**
> The server stores the exact string `classify.py` printed, character for character — **not** a
> re-serialised copy. Parsing the JSON and dumping it again reorders keys and changes spacing, and
> the point of the column is that it is the classifier's own output rather than a version of it.
> Photocopy the letter; do not retype it.
>
> **Why it is kept.** Every other column here is written by the insert code. `raw_result` is the only
> value in the row that arrived untouched, so when a stored result looks wrong it answers *"did the
> model say this, or did our code change it?"* without re-running the pipeline. The six emitted
> fields also land in **two** tables — five columns here, and `image` in `inspection_images` — so this
> is the one place the whole payload stays together.
>
> ⚠️ **Diagnostic record, not a data source.** Nothing should query, filter or chart it. The columns
> are what the dashboard reads; this is what you open when one of them looks wrong.

### 4.4 Database → dashboard

Per-egg rows live in `egg_inspections`:

- `weight_g` `DECIMAL(6,2)`
- `size_grade_id` references `size_grades`
- `ai_disposition` and `final_disposition`, both
  `ENUM('accepted','rejected','review','no_egg')`
- `is_overridden`, `notes` for the human override path

One image row per inspection in `inspection_images` (`image_type` is `ENUM('candling')`,
`file_path`, one image per inspection enforced by a unique key).

---

## 5. AI components in this system

There are currently **three**, and everyone should know all three exist:

| # | Component | Where | Runs |
|---|---|---|---|
| 1 | Candling classifier (Keras) | `ai/` | locally, on the station's machine |
| 2 | Roboflow pretrained detection model | J's prototype | **cloud**, hosted by Roboflow |
| 3 | Gemini analytics insights | `backend/services/geminiInsightService.js` | **cloud**, Google API |

Two of these require an internet connection. If you add a fourth, or swap a cloud service, say so in
the group chat first. The paper has to describe what the system actually contains.

---

## 6. Git rules

- **`main` is the branch that gets demoed.** Whatever is on `main` is what exists.
- **Merge to `main` at the end of each working session.** Long-lived personal branches mean the
  demo runs from somewhere nobody else has seen.
- Never commit `.env`, API keys, or `*.key` / `*.pem`. `.env.example` with empty values is the
  correct pattern and is already in place.
- `docs/` is deliberately gitignored. Do not add it back.

---

## 7. Known open items that affect your work

These are unresolved. If your task touches one, ask before assuming.

1. 🔴 **There is no dataset yet.** No labelled defective eggs exist, so the **85% accuracy target in
   the paper (Table 9) cannot be measured.** The model has trained on 2 eggs and 10 noise images and
   returns ~0.50 confidence. **This is the highest-value open item in the project** and no document
   edit touches it. Collection is team work, not one person's.
2. 🟡 **The load cell spec is chosen but not bought.** The paper previously specified 5 kg against a
   ±2 g target, which wastes resolution on a 60 g object. The BOM now specifies **1 kg**. Confirm on
   purchase.
3. 🔴 **The server cannot receive an inspection.** None of the three calls in section 4.1 exist. The
   backend on `main` serves `GET /api/inspections` and has no route that writes one, so every column
   spec in 4.3 — `model_version`, `raw_result`, the four server-owned columns — describes an insert
   that no code performs. **Owner: R.** This and item 1 are the two things standing between the
   project and a pipeline that runs end to end.
4. 🟡 **The ESP32-S3 firmware exists as an untested draft.** `firmware/EggMinistrator_ESP32S3.ino`,
   written by J, cherry-picked from `origin/Jasfer` on 2026-08-13. Reads the HX711, drives the
   display, LEDs and buzzer. **Never compiled and never run on hardware** — the banner at the top of
   the file says so and should stay until someone flashes it. Three known gaps: it posts over USB
   serial rather than Wi-Fi (contradicts 4.1), its display code targets an SSD1306 OLED rather than
   the **16x2 I²C LCD** the station actually has, and `handleLine()` waits for the egg to be removed
   with no timeout. The rest of J's branch was **not** taken; see section 7 resolved notes below.

**Resolved 2026-08-13** *(kept for context, do not re-open)*:

- ~~`not_an_egg`: store the row, or discard it and only warn?~~ **Store it — Option A stands**, now
  settled decision 8. R's proposal `docs/option-b-warning-only-not-an-egg.md` (discard, warn on
  screen, retry) is **declined**, and R's shipped code already implements what we kept, so nothing
  is torn out.

  The complaint behind the proposal was real — misloads flooded the History page during R's
  testing — but the cause was **not** the data model, and it is **already fixed at the source**.
  `backend/services/inspectionService.js:33` filters `WHERE inspections.final_disposition <>
  'no_egg'`, that endpoint is the only path any page has to inspection rows, and the `schema.sql:202`
  view filters the same way. A misload row is therefore **write-only** — stored by the station, never
  read back — and cannot reach History from the database at all. Whatever R saw predates that filter
  or came from an earlier mock-data build. ❓ **Ask him which**, so we know it is actually gone.

  ⚠️ **Nothing was changed in the dashboard for this.** A UI guard was written on 2026-08-13 — a
  fourth *"Not an Egg"* dropdown choice, with History defaulting to eggs only — and **reverted the
  same day**, because it guarded a path the SQL already closes. The one dashboard edit that stands is
  unrelated to misloads: `HistoryPage.jsx`'s `useMemo` was missing `historyScans` from its dependency
  array, so the table stayed empty until you touched a filter.

  ⚠️ **Open consequence: the data this decision keeps is not readable anywhere.** Misload rate is
  stored and never surfaced — `AnalyticsPage.jsx:134` counts `not_an_egg`, but from rows the API has
  already filtered out, so the tile can only ever read zero. Decision 8 is satisfied in the database
  and invisible in the UI until someone builds the readout.

  ⚠️ **The row-expiry timer discussed in the group chat was not adopted.** It would not have fixed
  this: the flood is same-session, and a one-day timer deletes yesterday's rows. It would also have
  silently reset the Analytics "Not an Egg" count every day, and it depends on MySQL's
  `event_scheduler`, which is **off by default** — a cleanup job that quietly never runs.

- ~~Section 4.3 describes a schema that is not on `main`.~~ **Merged 2026-08-13** (`0927658`).
  `origin/Ricardo` landed on `main`, so `result_label` is now
  `ENUM('good','defective','not_an_egg')`, `assessment_type` is `ENUM('candling')` only,
  `model_version` is `NOT NULL`, and both `ai_disposition` and `final_disposition` carry `'no_egg'`.
  Section 4.3 is a description again, not a plan, and the two `'external'` values that contradicted
  decision 1 are gone. ⚠️ An existing local MySQL database predates this and will not match —
  reapply `database/schema.sql`.

**Resolved 2026-08-07** *(kept for context, do not re-open)*:

- ~~Which ESP32 board the team owns.~~ **The ESP32-S3.** The classic ESP32-CAM is out of the build
  entirely. The camera is deliberately **not** on the ESP32 — capture is a USB webcam on the laptop.
  The ESP32-S3 reads the HX711 and posts weight **over Wi-Fi**, which is what keeps the IoT claim in
  the title true. ⚠️ **Wiring it over USB serial instead would break the cover page** — see
  `firmware/README.md`.
- ~~The final paper title.~~ Confirmed by the professor and landed in Ver6.1.4:
  *"EggMinistrator: An AI-Powered IoT System for Real-Time Egg Grading and Counting Using Candling
  Computer Vision and Load Cell Weight Measurement **for Leong Hup Philippines Inc.**"*

---

## 8. How to use this with your AI

1. Paste this whole file into a new chat before your first request.
2. Say which folder you own and what you are trying to build.
3. If the AI proposes something that contradicts section 3 or 4, it is wrong. Correct it.
4. If you and your AI decide something that changes section 3 or 4, tell M so this file is updated.
   A decision that only lives in your chat log does not exist.
