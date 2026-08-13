"""Turns the app's auto-collected snapshots (dataset/collected/<label>/*.jpg)
into a train/val split ready for train_yolo.py.

Run this after you've candled a good number of eggs with the app (and
corrected any wrong AI guesses using the Override button, so the saved
labels are actually correct). Safe to re-run any time you've collected
more images -- it recomputes the split from scratch each time.

Usage:
    python prepare_dataset.py
    python prepare_dataset.py --val-fraction 0.2
"""

import argparse
import random
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
COLLECTED_DIR = BASE_DIR / "dataset" / "collected"
TRAIN_DIR = BASE_DIR / "dataset" / "train"
VAL_DIR = BASE_DIR / "dataset" / "val"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--val-fraction", type=float, default=0.15,
                         help="Fraction of each class held out for validation (default 0.15)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not COLLECTED_DIR.exists():
        print(f"No {COLLECTED_DIR} folder found yet. Run the app and candle some eggs first.")
        return

    class_dirs = [d for d in COLLECTED_DIR.iterdir() if d.is_dir()]
    if not class_dirs:
        print(f"{COLLECTED_DIR} exists but has no class subfolders yet.")
        return

    # Wipe any previous split so re-running doesn't mix stale files with new ones.
    for d in (TRAIN_DIR, VAL_DIR):
        if d.exists():
            shutil.rmtree(d)

    rng = random.Random(args.seed)
    print(f"{'Class':<12}{'Total':>8}{'Train':>8}{'Val':>8}")
    print("-" * 36)

    total_all = 0
    counts = {}
    for class_dir in sorted(class_dirs):
        label = class_dir.name
        images = sorted(class_dir.glob("*.jpg"))
        rng.shuffle(images)
        if not images:
            continue

        n_val = max(1, int(len(images) * args.val_fraction)) if len(images) > 3 else 0
        val_images = images[:n_val]
        train_images = images[n_val:]

        (TRAIN_DIR / label).mkdir(parents=True, exist_ok=True)
        (VAL_DIR / label).mkdir(parents=True, exist_ok=True)
        for img in train_images:
            shutil.copy(img, TRAIN_DIR / label / img.name)
        for img in val_images:
            shutil.copy(img, VAL_DIR / label / img.name)

        counts[label] = len(images)
        total_all += len(images)
        print(f"{label:<12}{len(images):>8}{len(train_images):>8}{len(val_images):>8}")

    print("-" * 36)
    print(f"Total images: {total_all}")

    if len(counts) < 2:
        print("\nWarning: you only have images for one class so far. A classifier needs at "
              "least two classes (e.g. 'good' and at least one defect type) to learn anything.")

    if counts:
        biggest = max(counts.values())
        smallest = min(counts.values())
        if biggest > 0 and smallest / biggest < 0.15:
            print(f"\nWarning: class imbalance is severe (smallest class is only "
                  f"{smallest/biggest:.0%} the size of the largest). This matches the risk "
                  "your project doc flags -- defective eggs are naturally rarer. Consider "
                  "deliberately collecting more of the underrepresented class(es) before training, "
                  "or duplicating some of their images as a quick (imperfect) workaround.")

    print(f"\nReady. Now run: python train_yolo.py")


if __name__ == "__main__":
    main()
