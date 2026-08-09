# ai/

The AI image-processing subsystem — Python, OpenCV, TensorFlow. Inference runs on the
**laptop/desktop**, not on the microcontroller. Since 2026-08-07 the image is captured by a **USB
webcam attached to that same laptop**; the ESP32-S3 handles weight only.

## What the model reads

**One image per egg: the candling (transillumination) frame.** There is no reflected-light capture.
Anything that requires reflected light — surface dirt, shell discoloration — is out of scope and must
not appear as a class.

The frame yields two kinds of finding:

| Kind | Examples | Decision |
|---|---|---|
| Internal quality | blood/meat spots, air cell size | grade / downgrade |
| Shell condition | large cracks (light leakage), gross damage | reject |

> **Balut routing is out of scope by input, not by decision** (`CONTRACT.md` §3.5, confirmed
> 2026-08-04). Earlier revisions of this file required a third, *routing* output that separated eggs
> showing embryo development, and then explained its removal as a Ver4 descoping choice. The real
> reason is stronger and does not depend on a revision: **the reference operation separates
> fertilised eggs upstream into a different production line, so an embryo cannot arrive at the
> station at all.** Nothing needs to detect one. The model has **no embryo class** and emits a
> quality verdict only.
>
> ⚠️ Ver4 carried two leftover promises of balut routing (§3.4 Key Deliverables, and the Expected
> Benefits table valuing it at ₱48,000/yr). **Not re-checked against Ver6.1.4** — if they survived,
> they are paper bugs, not requirements. Do not build to them.

## Structure

- `training/train.py` — trains the classifier and writes both output files below. **Runs locally,
  not in Colab** — there is no notebook in this project.
- `training/check_order.py` — prints the class list Keras derives from the dataset folders, and
  nothing else. Run it after adding or renaming a folder (see the warning below).
- `inference/classify.py` — the script that runs at the station: loads the model, classifies one
  captured egg, prints one JSON line.
- `models/` — written by `train.py`, **both files gitignored**: `egg.keras` (the weights) and
  `classes.json` (the class list). Neither is in the repo; you get them by training.
- `dataset/` — three class folders, committed empty via `.gitkeep`. The photos themselves stay out
  of git; the folders are tracked so nobody has to type a class name and get it wrong.
- [`how-to-add-images.md`](how-to-add-images.md) — the shooting and training guide. **Hand this to
  whoever is collecting photos.**

## Running the scripts

⚠️ **Run everything from the repo root, not from inside `ai/`.** The scripts use paths like
`"ai/dataset"`, so they only resolve from the top of the repo.

```
pip install -r ai/requirements.txt
python ai/training/train.py
python ai/inference/classify.py some_photo.jpg
```

⚠️ **`train.py` will fail right now.** The 12 debug fixture images were deleted on 2026-08-07 once
the pipeline was proven, so `ai/dataset/` is empty and there is nothing to train on. That is
expected, not a broken script. It starts working again as soon as real photos land in the three
class folders.

## Dataset (NOT in the repo)

⚠️ **There is no dataset to inherit.** **No operational data is supplied** — the team photographs and
labels its own eggs, or sources a public set. That has not changed and is the part that matters here.

> **Corrected 2026-08-07.** This line used to read *"LH Deli is a reference scenario, not a client."*
> That is no longer accurate: the professor confirmed the client relationship and the paper now names
> **Leong Hup Philippines Inc.** on its cover, with **LH Deli** as the business unit and deployment
> site. What survives is the operative half — a named client still does not mean a supplied dataset.
> **Building the dataset is the team's job.**

- **Classes: `good` / `defective` / `not_an_egg`** — three, locked 2026-07-30 (Decision G; the
  decision log is a local working note, ask a teammate for it). These exact strings are what
  `inference/classify.py` prints and what the database stores.

  | Class | What goes in it |
  |---|---|
  | `good` | No internal defect visible under transillumination. |
  | `defective` | **Any** of: blood or meat spot, large crack revealed by light leakage, gross shell damage. The model does **not** report which. |
  | `not_an_egg` | Empty platform, a hand, a misload. |

  **Why three and not four or five.** Softmax scores sum to 1, so a per-defect class list cannot
  represent an egg with two defects at once — blood-spot-and-crack and one-unidentifiable-defect
  produce the same output. More decisive: blood and meat spots cannot be sourced on demand, so
  splitting the scarcest images across several boxes is the worst thing you can do to this dataset.
  Three classes pools them and is materially likelier to clear the 85% target.

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
- **`classes.json` and `egg.keras` travel together.** Sending one without the other produces
  confident nonsense.
- After touching the dataset folders, run `python ai/training/check_order.py` and retrain.

- **Location:** the three folders in `ai/dataset/`, on each person's own machine. The folders are
  tracked (via `.gitkeep`) so the class names cannot be typoed; the photos are not. Transfer is by
  zip — see [`how-to-add-images.md`](how-to-add-images.md) §8.
- **Image counts per class:** <!-- fill: state them — imbalance matters -->

Defective eggs are rarer than good ones, so the set will be imbalanced on exactly the classes that
matter. Blood and meat spots cannot be ordered on demand — plan collection early. (Fertile eggs
are no longer needed as a *class*, but they are still the cheapest way to source a known-abnormal
candling image while you validate the camera.)

The dataset is kept out of git (thousands of photos blow past GitHub's limits and can't be cleanly
removed once committed). See the repo `CONTRIBUTING.md`.

## Model

- **Architecture:** MobileNetV2 pretrained on ImageNet, frozen, plus a global-average-pooling layer
  and one softmax `Dense` sized to the number of class folders. Transfer learning — the base is not
  retrained, only the final layer is. 3 epochs, `adam`, `sparse_categorical_crossentropy`.
- **Input:** 224 × 224 RGB. `classify.py` converts OpenCV's BGR to RGB before predicting — see
  `CONTRACT.md` §4.2 for why that line matters and why removing it fails silently.
- **How to retrain:** `python ai/training/train.py`, **from the repo root**. There is no notebook
  and no Colab step.

> 🔴 **Accuracy (held-out test set): cannot be filled yet, and not just for want of data.**
> `train.py` splits the dataset 80/20 into **training and validation only**. There is no third,
> untouched split, so no number this code currently produces is a held-out test accuracy. The paper
> claims **85%** (Ver6.1.4 Table 9). Filling this in needs both a real dataset *and* a test split
> that the training run never sees.
>
> Current state per `CONTRACT.md` §7.1: trained on 2 eggs and 10 noise images, returning ~0.50
> confidence. **Do not quote the training run's printed score as the system's accuracy** — see
> [`how-to-add-images.md`](how-to-add-images.md) §7.

> **Validate the capture before building anything around it.** The camera has exactly one optical job:
> produce a usable candling image **through a white or tinted shell**, good enough to read internal
> features and light-leakage cracks. Photograph real cracked eggs early.
>
> *(Updated 2026-08-07. This used to warn about the ESP32-CAM resolving a **brown** shell at ~2MP —
> the hardest version of this problem. Both halves are retired: capture moved to a **USB webcam** in
> the descope, and the shells were corrected to white and tinted on 2026-08-03. Brown was never
> sourced. What remains to check is the webcam's minimum focus distance, which sets the chamber depth.)*
>
> Micro-cracks are out of reach for any optical method — don't treat them as a target.
