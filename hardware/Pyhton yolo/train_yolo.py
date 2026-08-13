"""Train a YOLOv8 *classification* model on the eggs you've candled with
the app. This is the accuracy-focused redesign: a classifier learns much
faster than an object detector from a small, self-collected dataset,
because it only has to answer "what class is this crop", not also learn
to draw a precise bounding box. Localization is handled separately by
plain OpenCV contour detection (EggLocator in egg_inspector_yolo.py) --
no labeling tool, no bounding-box annotation needed at all.

Workflow:
1. Run egg_inspector_yolo.py and candle a good number of eggs. Every
   finalized result gets its cropped photo auto-saved to
   dataset/collected/<label>/ -- correct any wrong AI guesses with the
   Override button first, so the saved label is actually right. This
   IS your labeled dataset; there's no separate annotation step.
2. Run: python prepare_dataset.py
   This splits dataset/collected/ into dataset/train/ and dataset/val/,
   and warns you about class imbalance (defective eggs are naturally
   rarer -- your project doc flags this explicitly).
3. Run: python train_yolo.py

The trained weights land in runs/classify/train/weights/best.pt. This
script copies that to models/best-cls.pt automatically, which is the
path egg_inspector_yolo.py looks for.
"""

import shutil
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"           # must contain train/ and val/ subfolders per class
BASE_MODEL = "yolov8n-cls.pt"                # small pretrained classifier, fine-tuned from here
EPOCHS = 60
IMG_SIZE = 224                               # standard for classification; crops don't need to be large


def main() -> None:
    train_dir = DATASET_DIR / "train"
    val_dir = DATASET_DIR / "val"
    if not train_dir.exists() or not val_dir.exists():
        print(f"Expected {train_dir} and {val_dir} to exist. Run prepare_dataset.py first.")
        return

    model = YOLO(BASE_MODEL)
    model.train(data=str(DATASET_DIR), epochs=EPOCHS, imgsz=IMG_SIZE, patience=15)

    best = Path("runs/classify/train/weights/best.pt")
    if best.exists():
        (BASE_DIR / "models").mkdir(exist_ok=True)
        dest = BASE_DIR / "models" / "best-cls.pt"
        shutil.copy(best, dest)
        print(f"\nTraining complete. Copied {best} -> {dest}")
        print("Reload the model in egg_inspector_yolo.py (or just restart it) to use it.")
    else:
        print("Training finished but best.pt was not found; check runs/classify/train/weights/")


if __name__ == "__main__":
    main()
