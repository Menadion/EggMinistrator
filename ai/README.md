# ai/

The AI image-processing subsystem — Python, OpenCV, TensorFlow. Inference runs on the
**laptop/desktop**, not on the microcontroller. Since 2026-08-07 the image is captured by a **USB
webcam attached to that same laptop**; the ESP32 handles weight only.

## What the model reads

**One image per egg: the candling (transillumination) frame.** There is no reflected-light capture.
Anything that requires reflected light — surface dirt, shell discoloration — is out of scope and must
not appear as a class.

The frame yields **one verdict per egg**, and the model does not report which defect it saw:

| Verdict | What goes in it | Decision |
|---|---|---|
| `good` | nothing visible under transillumination | accept |
| `defective` | large cracks (light leakage), gross shell damage | reject |
| `not_an_egg` | empty platform, a hand, a misload | record, do not count as an egg |

⚠️ **Do not re-add blood/meat spots or air cell.** The client does not grade for spots at all, so
they are not a requirement being left uncovered — they are out of scope. *"Internal quality"* means
cracks revealed by transillumination and nothing else, and the station must never be described as
reading the *contents* of an egg. `CONTRACT.md` §7 records the ruling; the paper agrees, FR-14 reads
*"Detect large cracks and gross shell damage."*

**Balut routing is out of scope by input, not by decision** (`CONTRACT.md` §3.5). The facility
receives only unfertilised eggs — fertilised ones are separated upstream into a different production
line and never reach the station — so an embryo cannot arrive here at all. Nothing needs to detect
one. The model has **no embryo class** and emits a quality verdict only. **Do not build to a balut
requirement.**

## Structure

- `scripts/train.py` — trains the classifier and writes both output files below. **Runs locally,
  not in Colab** — there is no notebook in this project.
- `scripts/check_order.py` — prints the class list Keras derives from **each of the three
  splits**, then says whether they agree. Since the split went three ways on disk there are three
  folders producing a class list and they must be identical; `classes.json` is written from
  `train/` alone. Run it after adding or renaming a folder (see the warning below).
- `inference/classify.py` — the script that runs at the station: loads the model, classifies one
  captured egg, prints one JSON line.
- `models/` — written by `train.py`, **all three files gitignored**: `egg.keras` (the weights),
  `classes.json` (the class list), and `version.json` (the model name and version string that
  `classify.py` reports to the database). None are in the repo; you get them by training.
- `dataset/` — three class folders, committed empty via `.gitkeep`. The photos themselves stay out
  of git; the folders are tracked so nobody has to type a class name and get it wrong.
- [`how-to-add-images.md`](how-to-add-images.md) — the shooting and training guide. **Hand this to
  whoever is collecting photos.**

## Running the scripts

⚠️ **Run everything from the repo root, not from inside `ai/`.** The scripts use paths like
`"ai/dataset"`, so they only resolve from the top of the repo.

```
pip install -r ai/requirements.txt
python ai/scripts/train.py
python ai/inference/classify.py some_photo.jpg
```

## Two listeners

| | `ai/listen_station.py` | `ai/listen_tray.py` |
|---|---|---|
| Trigger | `GET /api/inspections/pending` (one egg) | `GET /api/cycles/pending` (one tray) |
| Frame | one egg, cropped by `capture_settings.json` zoom/pan | one 4K tray, cropped six ways by `tray_map.json` |
| Verdicts | one | up to six, one `predict()` call |
| Report | `POST /api/inspections/:id/assessment` | `POST /api/cycles/:id/assessment` or `/reject` |
| Who | J's single-candling dataset rig (internal tooling) | the product (per-batch candling, panel ruling 2026-08-26) |

Shared code is in `ai/station_common.py`. Geometry and thresholds for the tray are measured once per
rig by `ai/scripts/calibrate_tray.py`; synthetic tray frames for testing come from
`ai/scripts/make_tray_frame.py`. Run the tray listener headless on a synthetic frame with
`py ai/listen_tray.py --frame <jpg> --once --default-map`.

⚠️ **`train.py` will fail right now.** The 12 debug fixture images were deleted on 2026-08-07 once
the pipeline was proven, so `ai/dataset/` is empty and there is nothing to train on. That is
expected, not a broken script. It starts working again as soon as real photos land in the three
class folders.

## Dataset (NOT in the repo)

⚠️ **There is no dataset to inherit.** **No operational data is supplied** — the team photographs and
labels its own eggs, or sources a public set. That has not changed and is the part that matters here.

- **Classes: `good` / `defective` / `not_an_egg`** — three, locked 2026-07-30 (Decision G; the
  decision log is a local working note, ask a teammate for it). These exact strings are what
  `inference/classify.py` prints and what the database stores.

  | Class | What goes in it |
  |---|---|
  | `good` | No internal defect visible under transillumination. |
  | `defective` | **Either**: a large crack revealed by light leakage, or gross shell damage. The model does **not** report which. |
  | `not_an_egg` | Empty platform, a hand, a misload. |

  **Why three and not four or five.** Softmax scores sum to 1, so a per-defect class list cannot
  represent an egg with two defects at once — crack-and-gross-damage and one-unidentifiable-defect
  produce the same output. More decisive: the defect images are the scarce ones, and splitting the
  scarcest images across several boxes is the worst thing you can do to this dataset. Three classes
  pools them and is materially likelier to clear the 85% target.

  *(This paragraph used to rest on blood and meat spots being unsourceable. That argument is retired
  with the class — see the narrowing note above. The pooling argument stands on its own.)*

  **`not_an_egg` is not padding.** Nothing forces the platform to hold an egg and softmax always
  returns a winner, so without it a thumb in frame gets scored `good` or `defective`.

  **Still excluded:** no embryo class (out of scope by input, see above), no dirty or discoloured
  class (the capture cannot show them), no size class (FR-04 is a threshold on the load cell, not a
  model output).

### ⚠️ The class order is Keras's to give, not ours to declare

Nothing in the code lists the three class strings. `train.py` reads the **subfolder names** of
`ai/dataset/` and Keras sorts them **alphabetically** — `defective`, `good`, `not_an_egg` — then
writes that list to `ai/models/classes.json`. `classify.py` reads the same file and indexes into it
with `probs.argmax()`. That is why nothing is hardcoded on either side.

The consequence is the trap: **a fourth folder, or a rename, silently renumbers the existing
classes.** Add `cracked/` and it sorts first, so every index shifts and a model trained before the
change now reports the wrong label with full confidence — no error, no warning.

- `classes.json` is **gitignored on purpose.** It is written by the same run as the weights and
  describes only that model. A committed copy would drift from weights nobody else has.
- **`classes.json`, `version.json` and `egg.keras` travel together — all three or none.** Sending
  one without the others produces confident nonsense, or a database row stamped with a version that
  describes different weights.
- After touching the dataset folders, run `python ai/scripts/check_order.py` and retrain.

- **Location:** `ai/dataset/`, on each person's own machine. Every folder is tracked (via
  `.gitkeep`) so the class names cannot be typoed; the photos are not. Transfer is by zip — see
  [`how-to-add-images.md`](how-to-add-images.md) §8.
- **Two levels, and they are not interchangeable.** `capture.py` writes only to
  `ai/dataset/_incoming/<class>/`; `train.py` reads only `ai/dataset/{train,val,test}/<class>/`.
  A shooter cannot know which split an egg belongs to — the unit of the split is the **egg**, and
  that is decided across a whole batch. Sorting `_incoming/` into the three splits is a separate,
  deliberate step, and the `e01`/`e02` egg number in each filename is what makes it possible.
- **Image counts per class:** <!-- fill: state them — imbalance matters -->

Defective eggs are rarer than good ones, so the set will be imbalanced on exactly the class that
matters — plan collection early.

✅ **Cracks are the one defect the team can manufacture**, which is why the dataset no longer depends
on client access (`docs/projman/context.md`). That mattered on 2026-08-20 when the client dataset
channel closed. Crack them under controlled conditions, shoot them **in the same rig the model will
run in** — same candler, same chamber, same distance, same background — and they count.

The dataset is kept out of git (thousands of photos blow past GitHub's limits and can't be cleanly
removed once committed). See the repo `CONTRIBUTING.md`.

## Model

- **Architecture:** MobileNetV2 pretrained on ImageNet, frozen, plus a global-average-pooling layer
  and one softmax `Dense` sized to the number of class folders. Transfer learning — the base is not
  retrained, only the final layer is. 3 epochs, `adam`, `sparse_categorical_crossentropy`.
- **Input:** 224 × 224 RGB. `classify.py` converts OpenCV's BGR to RGB before predicting — see
  `CONTRACT.md` §4.2 for why that line matters and why removing it fails silently.
- **How to retrain:** `python ai/scripts/train.py`, **from the repo root**. There is no notebook
  and no Colab step.

### The three splits, and the one you are not allowed to look at

`train.py:20-22` cuts the data three ways, not two:

```python
half    = len(val_ds) // 2
test_ds = val_ds.take(half)
val_ds  = val_ds.skip(half)
```

`image_dataset_from_directory` can only produce two subsets (`"training"` and `"validation"` — there
is no `"test"`), so the 20% validation slice is halved again. `train.py:45` trains against `val_ds`;
`train.py:46` measures `test_ds` once with `model.evaluate()`.

**Do not reorder those three lines.** `.take()` and `.skip()` return new datasets and leave the
original alone, so both must read `val_ds` *before* line 16 rebinds it. Rebind first and line 15
reads the already-halved dataset, producing an **empty test set with no error**. The same applies to
`half`: it is a variable so the count is locked to the original, not to save typing.

**Why the two names are not interchangeable.** `take` and `skip` are symmetric — the operation says
nothing about what a half is *for*. The role lives in the variable name. `val_ds` is what training
validates against; `test_ds` is the held-out set. Read the name, never the operation.

🔴 **Accuracy (held-out test set) still cannot be filled, and the missing piece is data, not code.**
The split exists, so the code can produce a held-out number. Per `CONTRACT.md` §7.1 the model has
trained on 2 eggs and 10 noise images at ~0.50 confidence, and `ai/dataset/` is empty. The paper
claims **85%**.

⚠️ **The split is correct by reading, not by running.** With an empty dataset `train.py` fails before
it reaches either line. Nobody has executed this path.

⚠️ **`test_ds` is a one-shot, and no code can enforce that.** `evaluate()` will run a hundred times
without complaint. But the moment you use the test number to decide something — more epochs, a
different optimizer — you have started steering by it, and it stops being an estimate of unseen
performance for exactly the reason `val_accuracy` did. Look once. A fresh honest number needs fresh
images nobody has seen.

**Do not quote the training run's printed score as the system's accuracy** — see
[`how-to-add-images.md`](how-to-add-images.md) §7.

**Validate the capture before building anything around it.** The camera has exactly one optical job:
produce a usable candling image **through a white or tinted shell**, good enough to read internal
features and light-leakage cracks. Photograph real cracked eggs early. The open item is the webcam's
minimum focus distance, which sets the chamber depth.

Micro-cracks are out of reach for any optical method — don't treat them as a target.
