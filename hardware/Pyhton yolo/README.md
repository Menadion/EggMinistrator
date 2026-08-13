# Egg Inspector

A desktop app that watches a webcam (or a photo), finds an egg, and tells
you if it looks good, cracked/damaged, or has a blood/meat spot.

---

## 1. Install

You need Python 3.10 or newer. Open a terminal/command prompt **in this
folder** and run:

```
pip install -r requirements.txt
```

## 2. Run

```
python egg_inspector_yolo.py
```

**Important:** run it from a terminal like this, not by double-clicking
the file. If something goes wrong, double-clicking just makes the window
flash and disappear — you won't see why. Running it from a terminal shows
the actual error message, which is the #1 thing to send me if you're
stuck.

A window should open. You don't need a trained model to start — it works
right away using a rule-based check (brightness + crack + stain
detection), good enough to try the app before you train anything. It's
not a trained AI model, just a starting point — see
[section 4](#4-training-your-own-model-optional-but-the-best-way-to-improve-accuracy)
for the real thing.

---

## 3. Using it

- **Start Webcam** — turns on your camera and watches for an egg. Detection
  works regardless of whether the egg is lying horizontally or standing
  vertically, and is designed to keep working even with shadows falling
  across the egg (see [section 9](#9-ai-assisted-detection-experimental) for
  an optional extra layer if it's still missing yours).
- **Open Image** — checks a single photo instead of live video.
- **☁ Analyze (Roboflow)** — checks a photo using an online model instead
  of the local one (optional, see [section 6](#6-optional-cloud-model)).
- **Override last result** — if the app got it wrong, pick the correct
  answer here. This also fixes the training photo it saved, so your data
  stays clean.
- **History tab** — every result from this session.
- **Settings tab** — camera choice, sensitivity sliders, operator name,
  egg weight.

---

## 4. Training your own model (optional, but the best way to improve accuracy)

The app checks for 3 classes: **good**, **cracked-damaged** (large cracks or
gross shell damage), and **blood-meat-spot** (internal spots visible under
candling). This matches the 3 output classes in the project doc's success
criteria (Section 3.2.2) — surface dirt is intentionally not a class here,
since the doc scopes it out (eggs are cleaned upstream of this station).

The app saves a photo of every egg it checks into `dataset/collected/`,
sorted by the label it gave (or the one you corrected it to). That's your
training data — no extra tool needed.

1. Use the app normally for a while. Correct any wrong guesses with
   **Override**.
2. Once you have a decent number of photos (200+ good eggs, 80+ of each
   defect type is a good starting target):
   ```
   python prepare_dataset.py
   ```
3. Then:
   ```
   python train_yolo.py
   ```
4. Click **Reload Model** in the app (or just restart it). It now uses
   your trained model instead of the rule-based heuristic.
5. Repeat this now and then as you collect more photos — accuracy keeps
   improving the more (correctly labeled) data you feed it.

No classifier is ever 100% accurate — even top commercial systems land
around 94–98% in ideal conditions. The goal is getting as close to that
as your data allows, not perfection.

---

## 5. Files you'll see appear

| File / folder | What it is |
|---|---|
| `inspection_log.csv` | A running log of every result. |
| `dataset/collected/` | Training photos, sorted by label. |
| `dataset/train/`, `dataset/val/` | Made by `prepare_dataset.py`. |
| `models/best-cls.pt` | Your trained model, made by `train_yolo.py`. |
| `reports/` | Session reports from "Export Report". |

---

## 6. Optional: cloud model

There's a second way to check a photo: a ready-made model hosted online
(no training required, but needs internet). This is a **separate,
optional install** — it's kept out of the main `requirements.txt` on
purpose so a problem with it (e.g. not yet supporting a brand-new Python
version) can never stop the app itself from installing.

```
pip install -r requirements-roboflow.txt
```

Then set your API key as an environment variable (don't put it directly
in any file):

```
export ROBOFLOW_API_KEY="your-key-here"      # macOS/Linux
setx ROBOFLOW_API_KEY "your-key-here"        # Windows
```

Then use the **☁ Analyze (Roboflow)** button in the app, or run it
by itself:

```
python roboflow_classifier.py path/to/egg.jpg
```

This only works for single photos, not live video, and its labels may
not exactly match `good / cracked-damaged / blood-meat-spot` since it was
trained by someone else. If it's not installed or not configured, the
app just tells you so — everything else works normally without it.

---

## 7. Troubleshooting

**"Nothing happens" / window flashes and closes**
Run it from a terminal (see [section 2](#2-run)) so you can actually read
the error, then send me that exact message. As of this update, a broken
dependency now prints a plain-English message and instructions instead of
just crashing — if you still see a wall of red traceback text, please
send it to me.

**`ERROR: Could not find a version that satisfies the requirement inference-sdk`**
This happened because `inference-sdk` (the optional Roboflow feature)
hadn't yet published support for a very new Python version. It used to
be bundled into the main `requirements.txt`, which meant this one
optional package failing could stop `customtkinter` and everything else
from installing too. Fixed by splitting it out — the Roboflow package now
lives in its own `requirements-roboflow.txt` (see
[section 6](#6-optional-cloud-model)) and is never required. Just run:
```
pip install -r requirements.txt
```
and skip `requirements-roboflow.txt` entirely unless you specifically
want the cloud-model button.

**`ModuleNotFoundError: No module named 'distutils'`**
This was a real bug: older `customtkinter` versions (below 6.0.0) don't
work on Python 3.12+ because they import a module Python removed. Fixed
by:
```
pip install --upgrade customtkinter
```
(`requirements.txt` now requires `customtkinter>=6.0.0` so a fresh
install won't hit this — but `pip install -r requirements.txt` alone
won't *upgrade* an already-installed old copy, hence the `--upgrade`.)

**`ModuleNotFoundError: No module named '...'`**
A dependency isn't installed. Run `pip install -r requirements.txt` again
in the same folder as `egg_inspector_yolo.py`.

**On a brand-new Python version, some package "has no matching distribution"**
Very new Python releases (e.g. 3.14) are sometimes ahead of what
third-party packages have published wheels for yet. If this happens with
a *core* dependency (not the optional Roboflow one above), the easiest
fix is installing a slightly older, well-supported Python (3.11 or 3.12)
alongside your current one, just for this project.

**`pip install` fails, is very slow, or says "no space left on device"**
`ultralytics` depends on PyTorch, which by default downloads several GB
of CUDA (GPU) files you don't need for this app — it only ever runs a
small model on CPU. Install the much smaller CPU-only version first,
*then* the rest:
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

**Camera not found / wrong camera**
Go to the Settings tab and click the refresh (🔄) button next to the
camera dropdown.

**App runs, but the AI guesses feel unreliable**
Normal until you've trained your own model — see [section 4](#4-training-your-own-model-optional-but-the-best-way-to-improve-accuracy).
The label in the top-right corner of the app tells you whether it's using
your trained model or the basic fallback.

**Roboflow button doesn't work**
Check the Settings tab — it tells you exactly why (not installed, no API
key, or the request failed).

**Still stuck**
Copy the exact error text from the terminal and send it to me — that's
the fastest way for me to pinpoint it.

---

## 9. AI-assisted detection (experimental)

Finding the egg in frame (as opposed to judging its quality) uses classic
computer vision, not a trained model — see the comment at the top of
`egg_inspector_yolo.py` for why. It combines several segmentation methods
(global threshold, adaptive local threshold, background subtraction) plus a
shape check (solidity + ellipse fit), specifically so that a shadow falling
across the egg or the egg being rotated doesn't break detection — none of
those methods depend on the egg being oriented a particular way, and
background subtraction in particular only cares that the egg is different
from the empty table, not how bright any part of it is.

If your setup is still tricky enough (very cluttered background, very low
light) that this misses your egg, there's a second, optional detection path:
**Settings → Detection (experimental) → "AI-assisted detection"**. This adds
a real pretrained model (YOLO-World) that recognizes "egg" from its name
alone, no dataset or training required, and merges its findings in alongside
the classic detector.

Trade-offs, honestly:
- **First enable downloads ~360MB** (a CLIP text encoder + YOLO-World
  weights) and needs an internet connection *and* Git installed on the
  machine (used once, to install the `clip` package). After that first
  download, it works offline.
- **It's slow** — about 400ms per detection on a CPU, versus a few
  milliseconds for the classic detector. It runs on its own slower cadence
  in the background rather than every frame, so it won't freeze the video,
  but it also won't catch an egg that's only in frame briefly.
- **Zero-shot accuracy on "egg" specifically isn't guaranteed.** This is a
  general-purpose model that was never trained specifically on eggs; treat
  it as a second opinion that sometimes helps, not a replacement for the
  classic detector.

Leave it off unless you've actually hit a case the classic detector misses —
it's not needed for the normal detect → candle → classify flow to work.

---

## 10. Packaging as a standalone .exe (optional)

```
pyinstaller --noconfirm --onefile egg_inspector_yolo.py
```

If the packaged `.exe` can't find `models/best-cls.pt`, keep that file
next to the `.exe` rather than trying to bundle it inside.
