# ai/

The AI image-processing subsystem — Python, OpenCV, TensorFlow. Inference runs on the
**laptop/desktop**, not the ESP32-CAM.

## Structure

- `training/` — the Colab notebook and/or training script.
- `inference/` — the script that runs at the station (loads the model, classifies a captured egg).
- `models/` — the trained model file (`.h5` / `.keras`). **If it's over ~100 MB, don't commit it —
  link it here instead.**

## Dataset (NOT in the repo)

<!-- fill -->
- **Location:** <!-- Google Drive / Colab link --> 
- **Classes:** <!-- e.g. good, cracked, dirty, discolored / candling: fertile, blood-spot, ... -->
- **Image counts per class:** <!-- state them — imbalance matters -->

The dataset is kept out of git (thousands of photos blow past GitHub's limits and can't be cleanly
removed once committed). See the repo `CONTRIBUTING.md`.

## Model

<!-- fill -->
- **Accuracy (held-out test set):** <!-- external classification %, candling % -->
- **How to retrain:** <!-- open training/notebook in Colab, point it at the dataset link, run all -->

> Reminder: capture real sample images of cracked and fertile eggs early — the ESP32-CAM has to
> resolve hairline cracks in reflected light AND candle through a brown shell. Validate before
> committing to it.
