# EggMinistrator — System Contract

**Paste this file into your AI assistant before asking it to write anything for this project.**

It exists so that five people working with five different AI tools build one system instead of five.
It contains what has been decided and how the parts connect. It does not contain opinions about
anyone's work.

**Owner: M.** One editor, so it cannot drift. If something here is wrong or out of date, message M
rather than editing it, and it gets fixed in one place.

*Last updated: 2026-08-09*

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
| `dashboard/` | R | React + Vite frontend, Node/Express backend |
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

---

## 4. The interfaces

This is the part that matters most. These are the handoffs between people.

### 4.1 Firmware → server

The ESP32 captures one candling image and one weight reading per egg, and sends both over Wi-Fi to
the local server.

> 🔧 **TO FILL (J + R):** the exact transport. HTTP POST with a multipart image? A raw TCP stream?
> What is the endpoint URL, and does the weight travel in the same request as the image or a
> separate one? Nothing downstream can be finished until this is written down.

### 4.2 Image → classifier

`ai/inference/classify.py` opens the image and resizes it to **224 x 224**.

**Colour order matters and is a silent bug if wrong.** OpenCV's `imread` returns channels in **BGR**
order. Keras models trained with the standard image loaders expect **RGB**. The requirement is that
the channel order at inference matches the channel order used at training. Do not assume either one
is "correct" on its own.

### 4.3 Classifier → database

`classify.py` emits exactly three fields:

```json
{ "image": "<filename>", "class": "good | defective | not_an_egg", "confidence": 0.0 }
```

`class` uses the Decision G values verbatim, with underscores, lowercase.

These land in the `ai_assessments` table:

| Column | Type | Note |
|---|---|---|
| `result_label` | `ENUM('good','defective','not_an_egg')` | must match Decision G exactly |
| `confidence_score` | `DECIMAL(5,4)` | 0.0000 to 1.0000 |
| `assessment_type` | `ENUM('candling')` | one value only, by decision 1 above |
| `model_name` | `VARCHAR(100)` | nullable |
| `model_version` | `VARCHAR(50)` | **`NOT NULL`** |
| `inference_time_ms` | `INT UNSIGNED` | nullable |
| `raw_result` | `LONGTEXT` | nullable |

> 🔧 **TO FILL (M + R):** `model_version` is `NOT NULL`, and no trained model exists yet, so there is
> no version string to write and **no assessment row can currently be inserted**. Agree either a
> placeholder value (for example `v0-stub`) or make the column nullable until a model exists.

> 🔧 **TO FILL (M + R):** is `raw_result` meant to hold the full JSON above? If so, say so here, so
> the dashboard knows what it can read out of it.

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
3. 🟡 **The ESP32-S3 firmware does not exist.** The paper states the node *"executes its own
   firmware"* and posts weight over Wi-Fi. Small job, not yet started. See `firmware/README.md`.
4. 🔴 **Section 4.3 above describes a schema that is not on `main`.** The `ai_assessments` columns
   listed there — `result_label` as an ENUM, `assessment_type ENUM('candling')`, `model_version
   NOT NULL` — exist only on the unmerged **`origin/Ricardo`** branch. What `database/schema.sql`
   on `main` actually has: `result_label VARCHAR(100)`, `assessment_type ENUM('external',
   'candling')`, `image_type ENUM('external','candling')`, `model_version NULL`, and an
   `ai_disposition` with no `'no_egg'` value. **So on `main` there is nowhere to store a
   `not_an_egg` verdict**, and the two `'external'` values contradict settled decision 1 (one
   candling photo per egg). Per section 6, `main` is what exists — so until that branch merges,
   section 4.3 is a plan, not a description. **Do not generate code against 4.3 without checking
   which branch you are on.** Merge is R's call; raise it in the group chat.

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
