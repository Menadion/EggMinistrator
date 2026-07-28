# ai/

The AI image-processing subsystem — Python, OpenCV, TensorFlow. Inference runs on the
**laptop/desktop**, not the ESP32-CAM.

## What the model reads

**One image per egg: the candling (transillumination) frame.** There is no reflected-light capture.
Anything that requires reflected light — surface dirt, shell discoloration — is out of scope and must
not appear as a class.

The frame yields two kinds of finding:

| Kind | Examples | Decision |
|---|---|---|
| Internal quality | blood/meat spots, air cell size | grade / downgrade |
| Shell condition | large cracks (light leakage), gross damage | reject |

> **Balut routing was descoped in Ver4.** Earlier revisions of this file required a third,
> *routing* output that separated eggs showing embryo development. Both scope sections of Ver4
> drop it, so the model has **no embryo class** and emits a quality verdict only. Ver4 still
> carries two leftover promises of balut routing (§3.4 Key Deliverables, and the Expected Benefits
> table, which values it at ₱48,000/yr) — those are paper bugs, not requirements. Do not build to
> them.

## Structure

- `training/` — the Colab notebook and/or training script.
- `inference/` — the script that runs at the station (loads the model, classifies a captured egg).
- `models/` — the trained model file (`.h5` / `.keras`). **If it's over ~100 MB, don't commit it —
  link it here instead.**

## Dataset (NOT in the repo)

⚠️ **There is no dataset to inherit.** LH Deli is a reference scenario, not a client — no operational
data is supplied. The team photographs and labels its own eggs, or sources a public set.

<!-- fill -->
- **Location:** <!-- Google Drive / Colab link -->
- **Classes:** <!-- Ver4 §3.2.6 is the authoritative list — "large cracks revealed by light
     leakage, blood and meat spots, and gross shell damage", plus a normal/good class. So:
     good, blood-meat-spot, large-crack, gross-shell-damage. NO embryo class (descoped Ver4).
     NOT dirty / discolored — the capture cannot show them, and §3.2.4 puts surface dirt out
     of scope outright. -->
- **Image counts per class:** <!-- state them — imbalance matters -->

Defective eggs are rarer than good ones, so the set will be imbalanced on exactly the classes that
matter. Blood and meat spots cannot be ordered on demand — plan collection early. (Fertile eggs
are no longer needed as a *class*, but they are still the cheapest way to source a known-abnormal
candling image while you validate the camera.)

The dataset is kept out of git (thousands of photos blow past GitHub's limits and can't be cleanly
removed once committed). See the repo `CONTRIBUTING.md`.

## Model

<!-- fill -->
- **Accuracy (held-out test set):** <!-- one number — single candling model -->
- **How to retrain:** <!-- open training/notebook in Colab, point it at the dataset link, run all -->

> **Validate the camera before building anything around it.** The ESP32-CAM has exactly one optical
> job: produce a usable candling image **through a brown shell** at low sensor sensitivity, good
> enough to read internal features and light-leakage cracks. That is still unproven on a ~2MP module.
> Photograph real cracked and fertile eggs early — if it fails, switch to a USB camera *before* the
> enclosure is designed around the wrong optics.
>
> Micro-cracks are out of reach for any optical method — don't treat them as a target.
