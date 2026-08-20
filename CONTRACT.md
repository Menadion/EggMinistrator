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

A single, stationary inspection station for eggs. An egg is placed on the station by hand. A load cell under the
platform weighs it; the weight both triggers the capture and determines the size grade. One
**candling** photo is taken (light
shone through the shell, so the camera sees the inside), an AI model classifies it, and the result is
written to a local MySQL database and shown on a web dashboard. It replaces manual inspection and
handwritten tally sheets at a commercial egg operation.

The client runs **white and tinted** (partially pigmented) shells. Not brown.

> ✅ **DESCOPE REVERSED, 2026-08-20.** Weight was descoped on 2026-08-19 and restored the next
> morning. **The load cell and HX711 are in the build**, the station weighs the egg, and weight
> determines a size grade. The paragraph above describes the live design. The descope is a dead end:
> `docs/projman/weight-descope.md` is marked VOID and nothing in it should be acted on.
>
> **Nothing was lost.** Both parts arrived 2026-08-14 and are on the shelf; no size-grading code was
> ever deleted; R was never told, so there is nothing to walk back with him.
>
> **Three adviser rulings on 2026-08-20 drove this, and all three reach further than the descope:**
>
> 1. 🔴 **The title cannot change.** It names *"Load Cell Weight Measurement"*, and a locked title
>    means the component it names has to exist. This is what forced the reversal.
> 2. 🔴 **The defense requires physical hardware. A simulator will not be accepted** — a simulated
>    demo is read as no programming having been done. **This overrules the 2026-08-14 team decision
>    to demo by simulation.** See open item 4; it is the largest change on this page.
> 3. ✅ **Scope changes do not need to be written into the paper.** Different panelists on the day,
>    so quiet changes are fine. Neither the descope nor its reversal is ever explained to anyone.

> 🔴 **A fourth ruling, unrelated to weight, constrains everything the project says out loud.**
> **Never present the client as already operating a system that does what we do.** The panel reads
> "an existing system" as the project being defeated, even when the framing is integration or
> complement. Industry competitors in the comparison matrix are fine and were explicitly requested by
> Ferrer; *this client already owns a grading machine* is not sayable. This kills the warehouse-machine
> contrast as a public argument, though it stays usable as a defensive answer if a panelist raises it
> first. See `docs/projman/gaps.md`.

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
   is ±2 g. *(Briefly voided 2026-08-19, restored 2026-08-20 — see section 1.)*
4. **Size grades follow PNS/BAFS 321:2021 weight bands**, stored in the `size_grades` table.
   *(Briefly voided 2026-08-19, restored 2026-08-20 — see section 1.)*
5. **Embryo development and balut are out of scope, by input.** The reference operation receives
   only unfertilised eggs; fertilised eggs are separated upstream into a different production line
   and never reach the station. An embryo cannot arrive here, so nothing needs to detect one.
6. **Dirt is out of scope, because a backlit frame cannot show it.** Surface dirt and shell
   discoloration are reflected-light features; the station captures one transilluminated image and
   nothing else.
   > ⚠️ **The reason changed on 2026-08-19 and the old one must not be used.** It used to read
   > *"because eggs are washed upstream before they reach the station."* That died twice over: the
   > station now sits at the **laying house, upstream of the wash**, and the client's own process
   > description has the candling stage **after** the wash still finding dirt, so washing was never
   > removing all of it. The capture-design reason is stronger anyway — it is a fact about optics
   > rather than about a workflow, so it cannot be invalidated by the workflow changing again.
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

**The board sends a weight. It does not send an image.** The camera is a USB webcam on the laptop;
the board reads the load cell through the HX711 and reports the number.

> ✅ **Restored 2026-08-20.** This briefly read *"the board sends a placement event"* during the
> 24-hour weight descope. **The weight payload below is correct and R's endpoint already accepts it.**
> No coordination with J or R is needed here after all.

**Transport: HTTP over Wi-Fi, never USB serial.** The board's USB cable carries power only. This is
not a style preference — `hardware/bill-of-materials.md` is explicit that a USB *data* path makes the
board a peripheral attached to a computer, which contradicts the paper's title and §2.2. **This is the
load-bearing half of the IoT claim**: the board runs its own firmware and reports over the network
rather than hanging off a USB port.

#### The three calls, in order

```
1. BOARD  →  POST /api/inspections            { "weight_g": 58.23 }
   SERVER →  creates the egg_inspections row, replies { "id": 41 }
             ⚠️ and must also trigger the capture — see FR-01, still unwritten

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
   edit touches it.

   ⚠️ **Collection is NOT team work, and this line used to say it was.** There is one candler and it
   is J's, so J is the only person who can see inside an egg. Everything follows from that: hunting
   blood and meat spots across the group is impossible, and at ~1% natural occurrence one person's
   consumption yields near zero. **Blood and meat spots are effectively uncollectable on this
   timeline** — see item 5. What one person *can* batch: cracks made on a counter edge (free,
   unlimited, and exactly FR-14) and aged eggs with enlarged air cells (free, needs a week, and
   genuinely *internal* quality, which is what FR-12 claims). Those two carry the defective class.

   ⚠️ **No usable photo can be taken until the egg stands up on its own.** Fingers holding the egg
   appear in the candling frame and will not exist at inference, so the model would learn a grip.
   A bottle cap with the centre cut out is enough, provided it is the same every shot.
   ⚠️ **The final holder (BOM item 4) is a harder part than the photo rig**, because it must also
   transfer the egg's weight to the load cell while the rig does not. Do not assume that a working
   photo rig means the station holder is solved.
2. 🔴 **The load cell and HX711 arrived 2026-08-14 and still need wiring and calibration.**
   *(Briefly voided by the 2026-08-19 descope; restored 2026-08-20 with both parts still on the
   shelf.)*

   ✅ **CALIBRATION IS DONE.** This entry used to say the factor was still the library's placeholder
   `2280.0`. **That is out of date.** `LOADCELL_CALIBRATION_FACTOR = 735.25`, calibrated by J on
   2026-08-16 against the cell this project owns — the sketch shows the working at line 129: a raw
   reading of 44267 against a known 60 g gives 737.8, settled to 735.25 in testing. **The longest job
   on the hardware list was already finished four days ago.**

   ✅ **Wiring is only two signal pins**, DOUT and SCK, plus power. The interface is documented, so
   nothing here is blocked on an unknown part.

   ✅ **The chip is identified and the pin map already suits it.** `board-id/` was run on COM3 and
   returned **ESP32-D0WD-V3 rev v3.1**, MAC `1c:69:20:a3:f8:8c` — a **classic ESP32, not an S3**. The
   sketch was rewritten for it and avoids GPIO6-11 (SPI flash), the strapping pins and the input-only
   range. Nothing is blocked here.

   🔴 **One physical job before flashing: J's LEDs are wired to GPIO12 and GPIO13, and the sketch
   drives 26, 27 and 23.** They have to move, or the indicators simply will not light. GPIO12 is MTDI
   and, held high at boot, selects a 1.8 V flash voltage and the board may not start — J's own code
   drives it low so his bench setup works, but that is one stray pull-up from an unbootable board,
   which is why the sketch moved off it. See the sketch at line 113.
3. ✅ **RESOLVED 2026-08-14 — the server receives inspections.** Built by R, merged in `de64b77`,
   and verified end to end against MariaDB. All three calls in section 4.1 exist and behave as
   specified. `DEVICE_API_KEY` now has a real value in `backend/.env`; **the same string has to go
   into `firmware/secrets.h` or the board gets a 401.** `requireDeviceKey` fails closed when the key
   is unset — 503 rather than allowing anything through — and compares with `timingSafeEqual`.

   🟡 **One cosmetic gap left.** `createInspection` sets no `batch_id` or `sequence_number`, so
   `formatEggId` falls back to a truncated UUID: new rows read `78919cdf…` in the dashboard while
   the seeded ones read `B001-EGG-001`. Harmless, and it will look like a bug on a projector.
4. 🟡 **The ESP32-S3 firmware exists but has never been compiled or flashed.**
   `firmware/EggMinistrator_ESP32S3.ino`, written by J, cherry-picked from `origin/Jasfer` on
   2026-08-13 and reworked the same day: it now posts over Wi-Fi per 4.1, drives the **16x2 I²C
   LCD** the station actually has, and bounds every wait that used to block forever. **Never
   compiled and never run on hardware** — the banner at the top of the file says so and stays until
   someone flashes it. The rest of J's branch was **not** taken; see the resolved notes below.

   Two things to know before flashing. **Credentials live in `firmware/secrets.h`**, which is
   gitignored — copy `secrets.h.example` and fill it in; if `secrets.h` ever appears in
   `git status`, something is wrong with the ignore rule. And **`LCD_I2C_ADDRESS` is a guess**:
   `0x27` is the common PCF8574 address but a large share of these modules are `0x3F`, and
   `LiquidCrystal_I2C::init()` returns nothing, so a wrong address fails silently as a blank screen
   with a lit backlight.

   🔴 ~~**SOFTDEV will be demonstrated by simulation, not by the prototype.** Team decision,
   2026-08-14.~~ **OVERRULED BY THE ADVISER, 2026-08-20. The defense requires physical hardware.**
   A simulated demo is read as no programming having been done. **The board must be flashed, wired
   and working on 2026-08-26.** This is the single largest change on this page and it makes flashing
   the critical path for the whole project.

   ✅ **`firmware/simulate_station.py` keeps a job, just not that one.** It plays the board and the
   laptop against the **real** backend — real endpoints, real device-key check, real database writes,
   real dashboard — which makes it the fastest way to exercise the server while the hardware is being
   built. It still POSTs `weight_g`, which is **correct again** after the descope reversal, so no
   change is needed to it. Use it for development. Do not use it on the day.

   ✅ **The firmware can also be tested without waiting on item 3.** `firmware/stub_server.py` answers
   all three calls in 4.1 using nothing but the Python standard library, inventing a verdict a
   second and a half after each weight arrives and cycling `good` → `defective` → `not_an_egg` so
   every LED and buzzer path gets exercised. It is a test double for the seam, **not** a preview of
   the backend — it stores nothing and proves nothing about R's implementation. What it proves is
   the board against this spec, which is the half that can be finished now.

5. 🟡 **Paper revisions owed. None applied yet. Owner: M.** Parked here so they are not quietly
   buried — the paper is not in this repo, so this list is the only record that they are outstanding.

   - **Parts list.** The station gets a **16x2 I²C LCD and three indicator LEDs**, both pre-owned,
     so they go in the *already owned* table at ₱0. ⚠️ **State explicitly that the total is
     unchanged** — a reader who sees new components will assume the money moved. Tables 2, 6 and 15
     keep **₱3,432.00**.
   - 🔴 **FR-15 is half met and there is no buzzer.** The requirement asks for a visual indicator
     **and an audible signal**; the LCD and LEDs cover the first, nothing covers the second. The
     firmware is already written for it — `BUZZER_PIN` on GPIO10, `beep()` sounding 1/2/3 tones for
     good/defective/not_an_egg — so **the code exists and the part does not.** A passive piezo
     buzzer is ₱20–50 and two wires. If it is bought it joins the parts-to-buy table and the totals
     *do* move; if the audible signal is instead played through the laptop speaker, say so in the
     paper, because the laptop is at the station but it is not the station.
   - **Defect scope.** Blood and meat spots are **under-sampled, not removed.** Write them as a
     stated limitation with the sampling constraint named (one candler, ~1% natural occurrence) and
     list them as future work. ⚠️ **Do not delete the capability.** FR-12 claims *internal* quality;
     if `defective` collapses to cracks alone, the system is transilluminating in order to find a
     shell defect, and the candler and the light-sealed chamber lose their justification. The
     internal claim is carried by **air-cell / ageing** defects, which are free.
   - **Transport wording.** Confirm §2.2 and the Ch4 sensing layer match section 4.1: the ESP32-S3
     posts weight over **HTTP on Wi-Fi**, and its USB cable carries power only. The design did not
     change, but the prose should be checked against it.
   - **FR-14 phrasing.** It says *detect* cracks, and the model outputs `defective` without naming
     the defect type. That satisfies it as written — make sure the paper does not overclaim
     per-defect classification anywhere.

   ⏳ **This list is incomplete.** The TENTREP panel's full revision list is still pending a
   transcription of the 2026-08-11 recording, and that transcription has not been done. Nothing here
   should be treated as the whole set until it has.

6. 🔴 **Nobody has asked LH Deli what they reject an egg for, and that answer defines `defective`.**
   Not a documentation question — it decides what the model is trained to do.

   The defective class currently leans on **aged eggs / enlarged air cells**, because they are the
   only *internal* defect that can be produced for free (item 1). But an aged egg is a lower
   **grade**, not necessarily a **reject** — commercial graders sort by air cell depth into AA/A/B
   rather than throwing the egg away. ⚠️ **If the client does not reject old eggs and we train the
   model to call them `defective`, we have built a machine that rejects sellable stock.** It would
   still score well on our own test set, because that test set agrees with our labels and the client
   does not. That failure is invisible from inside the project.

   **Ask "what makes you reject an egg today?"** rather than "do you check age?" — the first defines
   the class, the second only invites a yes/no. If the answer is that they assess nothing internal,
   that is a genuine innovation claim and worth making; but it has to be their answer, not our
   assumption.

   **Bundle this with the client contact already owed.** The TENTREP panel called the economic value
   unspecific and asked for baseline data from the client's operation. One conversation, three
   questions: what gets rejected today, is anything internal assessed today, and how many eggs per
   day / how many graders / how long. Do not make two calls.

7. 🟡 **The override audit trail is a text column, and `staff_overrides` is dead furniture.**
   `inspectionService.js:286` — `overrideInspection()` — does one `UPDATE` on `egg_inspections`
   (`is_overridden = 1`, `final_disposition`, and a sentence appended to `notes`). **It never inserts
   into `staff_overrides`. No application code path ever has.** The table has existed since the first
   schema and has indexes and two foreign keys.

   ⚠️ **It is not empty, and that is worse than empty.** `sample-data.sql:50` seeds exactly one
   row — `review` → `accepted`, *"Visual check confirmed minor, non-defective shell variation"*, dated
   **2026-07-25**. Verified against the live local database 2026-08-18: one row, and overriding an egg
   through the dashboard does not add a second. An empty table reads as *not built yet*; one plausible
   hand-written row reads as *working* until someone checks the date.

   So the answer to *"where is override history stored?"* is currently **a free-text `notes` field**,
   parsed by nobody, holding lines like `Overridden to "defective" by admin at 2026-08-17T…`. There
   is no `overridden_by` column — `inspectionService.js:296` says so and points here.

   **Why this matters on 2026-08-26 and not before.** FR-03 is met as written: staff can override,
   and the override sticks. Nothing is broken. But the schema advertises a structured, queryable,
   user-attributed override log, and the running system does not produce one. A panelist who overrides
   an egg on the projector and then opens `staff_overrides` sees the count sit at one, timestamped
   three weeks before the demo. **Know the answer before the room asks the question.** Either say the table is provisioned for the audit log and the
   current build writes the trail to `notes`, or spend the hour and make the write real.

   ⚠️ **Do not "clean up" the unused table.** It is provisioned, not abandoned, and
   `schema.sql:145-146` was widened on 2026-08-18 (audit item 1, migration
   `20260818_allow_no_egg_in_staff_overrides.sql`) so it can accept a `no_egg` correction whenever the
   write is wired. Dropping it re-opens a settled question.

   ⚠️ **"Override" means two different things in this repo and it has already caused damage.**
   The FR-03 dropdown on the History page and the `staff_overrides` table are separate; the audit item
   about the table's ENUM was read as an instruction to delete the dropdown, and `f6fa589` removed a
   delivered FR. Restored in `5b104fd`. **Before touching anything with "override" in the name, check
   which of the two it is.**

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

- ~~Which ESP32 board the team owns.~~ **An ESP32-D0WD-V3, a classic ESP32** — confirmed 2026-08-20
  by running `firmware/board-id/`, not read off the can, which says only "ESP32-32X". *(Earlier notes
  here and elsewhere in the repo call it an ESP32-S3. They are wrong; the paper says only "ESP32" and
  is correct.)* The ESP32-CAM is out of the build
  entirely. The camera is deliberately **not** on the ESP32 — capture is a USB webcam on the laptop.
  The ESP32-S3 posts **over Wi-Fi**, which is what keeps the IoT claim in the title true. ⚠️ **Wiring
  it over USB serial instead would break the cover page** — see `firmware/README.md`.
  > ✅ **Unchanged.** A 2026-08-19 note here said the board reads a presence sensor rather than the
  > HX711. That descope was reversed on 2026-08-20; it reads the HX711 and posts a weight.
- ~~The final paper title.~~ ✅ **CLOSED AND LOCKED 2026-08-20.** It stands as
  *"EggMinistrator: An AI-Powered IoT System for Real-Time Egg Grading and Counting Using Candling
  Computer Vision and Load Cell Weight Measurement **for Leong Hup Philippines Inc.**"* Briefly
  re-opened on 2026-08-19 when weight was descoped; **the adviser declined the change on 2026-08-20**,
  which is what forced the descope to be reversed rather than the title. **Do not re-open this.** The
  title is now a constraint on the build, not the other way round.

---

## 8. Functional requirements — the live checklist

Transcribed from the paper, **Table 10 / §3.2.3**. It lived only in the PDF, which meant nobody could
check their own work against the thing being graded. **The bar is 50% for SOFTDEV and 100% for
finals.** Update the status column when something lands; it is the project plan now, not just a
defense aid.

**Status as of 2026-08-15: 8 met, 3 partial, 4 not met — 53%. ✅ The SOFTDEV bar of 50% is cleared**
**on software alone**, with no hardware flashed and no model trained. The remaining four are all
`ai/` and all wait on one thing: photographs.

> ✅ **All eight met requirements now carry a dated verification, checked 2026-08-15.**
> Four of them — FR-05, FR-07, FR-09 and FR-10 — previously held only a one-line assertion
> (*"dashboard"*, *"builds clean"*, *"Analytics: per-day averages"*, *"HistoryPage + admin
> accounts"*) and had never been re-checked since they were written. They were run against a live
> stack: MariaDB, the real backend, the real dashboard, with fresh inspections driven through
> `simulate_station.py`. All four held. **The 53% is now evidence rather than a claim**, which
> matters because the margin over the bar is a single requirement.

> ⚠️ **`final_grade` holds the SIZE, not the verdict.** The sample data puts `Medium` and `Large` in
> it. An early cut of the FR-03 override wrote `"defective"` there and corrupted the size shown on
> every page — caught only because the change was tested against a real database rather than
> reasoned about. The verdict lives in `final_disposition`. **R: worth renaming it `final_size_grade`
> before someone repeats this.**

| FR | Requirement | | Where it stands |
|---|---|---|---|
| 01 | Capture egg images using a stationary camera | 🔴 | no capture code exists. `classify.py` reads a file off disk (`cv2.imread(sys.argv[1])`); nothing opens a webcam. ⚠️ **The load cell does NOT close this.** It supplies the *trigger*; something on the laptop must still receive that event, open the webcam, classify, and POST back against the inspection ID. **That listener is still unwritten**, and with the simulator ruled out of the defense it is now required to exist by 2026-08-26 |
| 02 | Automatically detect eggs on the platform | 🟡 | firmware triggers at a 20 g threshold on the load cell. *(A 2026-08-19 note replaced this with a presence sensor; the descope was reversed 2026-08-20 and the weight threshold stands.)* Still amber: board never flashed. A pre-owned presence sensor sits in the drawer as a fallback if the threshold proves jumpy in testing |
| 03 | Allow authorized personnel to override an AI result | ✅ | **built and verified 2026-08-13** against MariaDB — `PATCH /api/inspections/:code/override`, any signed-in account, per-row control on History. Writes `final_disposition` + `is_overridden`, appends who and when to `notes`, and never touches `ai_disposition`. `400` on an invalid label, `401` without a token. ⚠️ The History control was deleted in `f6fa589` and restored in `5b104fd` — do not remove it again, see section 7 item 7. The override is logged to `egg_inspections.notes`, **not** to `staff_overrides` |
| 04 | Assign a size class from weight (PNS, Table 11) | ✅ | R's `findSizeGrade()` verified 2026-08-14, tested 58.20 g → `Medium`. *(Descoped 2026-08-19, restored 2026-08-20. R was never told, and no code was deleted, so this row never actually moved.)* |
| 05 | Automatically count inspected eggs | ✅ | **verified 2026-08-15** against a live stack. `DashboardPage.jsx:31` renders `inspections.length` straight off `GET /api/inspections`; the endpoint returned 5,234 rows over a database holding 5,337, the difference being the 103 `no_egg` rows decision 8 filters out. A real count over real rows, not a stored total |
| 06 | Store inspection records in the database | ✅ | **verified end to end 2026-08-14.** Built by R, merged in `de64b77`. Weight POSTed → row minted with an id → assessment POSTed against it → verdict polled back. Every 4.3 column lands, including the four the server owns, `raw_result` byte-identical to what was sent, and the `inspection_images` row created |
| 07 | Display results on the monitoring dashboard | ✅ | **verified 2026-08-15** against a live stack, replacing "builds clean", which was never a check that anything displayed. Dashboard and History both render live rows carrying egg ID, weight, size grade, quality verdict, station and timestamp. Confirmed by driving fresh inspections through `simulate_station.py` and watching them arrive |
| 08 | Generate inspection reports | ✅ | verified 2026-08-13: report builder + filters + paginated preview over real DB rows, and `downloadCsv()` genuinely produces a file. ⚠️ the **"Export PDF" button just calls `window.print()`** — same handler as Print, nothing generates a PDF. Relabel or remove before a demo |
| 09 | Display daily production statistics | ✅ | **verified 2026-08-15** against a live stack. Analytics computes volume, defect rate, size mix, weight bands and hour-of-day from live rows, and widens its own date range to span the data on load (`AnalyticsPage.jsx:74-82`), so the 7-day default never hides anything. ⚠️ It was demonstrating over 2 days and 13 eggs until the `database/` demo seeds were applied on 2026-08-15; it now covers 2026-03-01 onward and aggregates monthly. **The requirement was met either way, the demo was not** |
| 10 | Allow administrators to access inspection history | ✅ | **verified 2026-08-15** against a live stack. `HistoryPage.jsx:50` fetches `/api/inspections` through `authenticatedFetch`; unauthenticated calls get `AUTH_REQUIRED`. ⚠️ **There is no role check on that route** — `server.js:55-59` calls only `getSessionUser`, and signing in as `inspector` returned all 5,234 rows. Role gating exists only on `/api/admin/*`. The requirement says administrators *can* reach the history, not that only they can, so it is met as written — same reading R applied to FR-03. **Say this deliberately if asked** |
| 11 | Capture a candling image under transillumination | 🔴 | **same missing capture code as FR-01** |
| 12 | Classify internal egg quality from the candling image | 🔴 | `classify.py` is written but no trained model exists — `ai/models/` is absent |
| 13 | Measure the weight of each inspected egg | 🟡 | firmware written (535 lines) and **calibrated 2026-08-16, factor 735.25**. Amber only because the board has never been compiled or flashed. *(Descoped 2026-08-19, restored 2026-08-20.)* |
| 14 | Detect large cracks and gross shell damage | 🔴 | **same missing model as FR-12** |
| 15 | Indicate the result at the station, visual + audible | 🟡 | **visual half only.** LCD + 3 LEDs exist and the firmware drives them; **there is no buzzer**, so nothing satisfies "audible signal". The `beep()` code is already written and waiting on a ₱20–50 part — see section 7 item 5 |

### They move in clusters, not one at a time

- **Software cluster (R, mostly) — clears 50% with no hardware and no model.** `FR-08` needs only
  verifying. `FR-06` is the ingest already in progress. ~~`FR-04` comes with it.~~ `FR-03` needs a
  button and an endpoint against columns that have been sitting ready. ~~**That is 8/15 = 53%.**~~
  > ✅ **8 of 15 = 53% stands.** A 2026-08-19 recount here read 7 of 13 after FR-04 and FR-13 were
  > descoped. **The descope was reversed on 2026-08-20**, both requirements are back, and the count
  > returns to the printed figure. Nothing about the denominator needs explaining to anyone.
- **Hardware cluster (J) — `FR-02`, `FR-13`, `FR-15` all flip on the first successful flash.** → 11/15.
- **AI cluster (M) — `FR-01`+`FR-11` are one capture script, `FR-12`+`FR-14` are one training run.**
  Two jobs, four requirements, blocked on nobody.

⚠️ **FR-14 asks you to *detect* cracks, not to name them.** The model outputs `defective`, and it does
not distinguish a crack from a blood spot. That satisfies the requirement as written — but say so
deliberately rather than discovering it in front of a panel. This is also where J's `data.yaml`
class list came from: FR-12 names internal quality and FR-14 names cracks, and he read two
*detection* requirements as a *labelling* scheme. §3.2.2 has the correct three classes.

---

## 9. How to use this with your AI

1. Paste this whole file into a new chat before your first request.
2. Say which folder you own and what you are trying to build.
3. If the AI proposes something that contradicts section 3 or 4, it is wrong. Correct it.
4. If you and your AI decide something that changes section 3 or 4, tell M so this file is updated.
   A decision that only lives in your chat log does not exist.
