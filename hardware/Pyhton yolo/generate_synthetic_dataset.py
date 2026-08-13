"""Generates fake, procedurally-drawn "candled egg" images for exactly one
purpose: testing that the training pipeline (prepare_dataset.py ->
train_yolo.py -> models/best-cls.pt -> EggClassifier) works end to end,
before you've collected any real egg photos.

THIS IS NOT A SOURCE OF REAL TRAINING DATA. A model trained on these images
has only ever seen crude procedural shapes -- solid ellipses, straight
lines, and blobs -- not real eggshell texture, real candling light physics,
real shell color variation, or what a real crack or blood spot actually
looks like under transillumination. It will NOT be accurate on real eggs.
Delete dataset/collected/, dataset/train/, dataset/val/, and
models/best-cls.pt before collecting real data, so none of these synthetic
images end up mixed into your real training set.

Usage:
    python generate_synthetic_dataset.py
    python generate_synthetic_dataset.py --count 150
"""

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "dataset" / "collected"
IMG_SIZE = 220


def _blank_canvas(rng: random.Random) -> np.ndarray:
    """A dark candling-chamber background with a bright, warm-toned egg
    silhouette roughly centered in frame -- loosely mimics the color palette
    of a real transillumination photo (dark surround, warm interior) without
    attempting to mimic real shell texture."""
    canvas = np.full((IMG_SIZE, IMG_SIZE, 3), (8, 6, 5), dtype=np.uint8)  # near-black BGR
    cx = IMG_SIZE // 2 + rng.randint(-10, 10)
    cy = IMG_SIZE // 2 + rng.randint(-10, 10)
    ax = rng.randint(70, 90)
    ay = rng.randint(85, 100)
    angle = rng.randint(-8, 8)
    base_brightness = rng.randint(150, 200)
    # warm (yellow/orange-leaning) candling tone in BGR
    color = (base_brightness - 40, base_brightness - 10, base_brightness + 20)
    cv2.ellipse(canvas, (cx, cy), (ax, ay), angle, 0, 360, color, -1)
    cv2.ellipse(canvas, (cx, cy), (ax, ay), angle, 0, 360,
                tuple(max(0, c - 25) for c in color), 2)  # subtle shell-edge ring
    return canvas, (cx, cy, ax, ay, angle)


def _add_noise(img: np.ndarray, rng: random.Random) -> np.ndarray:
    noise = np.zeros_like(img, dtype=np.int16)
    cv2.randn(noise, 0, rng.randint(4, 10))
    out = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(out, (3, 3), 0)


def make_good(rng: random.Random) -> np.ndarray:
    canvas, _ = _blank_canvas(rng)
    return _add_noise(canvas, rng)


def make_cracked_damaged(rng: random.Random) -> np.ndarray:
    canvas, (cx, cy, ax, ay, _angle) = _blank_canvas(rng)
    # one long, fairly straight line crossing the egg silhouette
    theta = rng.uniform(0, np.pi)
    length = rng.randint(int(ax * 1.2), int(ax * 1.8))
    dx, dy = np.cos(theta) * length / 2, np.sin(theta) * length / 2
    p1 = (int(cx - dx), int(cy - dy))
    p2 = (int(cx + dx), int(cy + dy))
    line_color = (30, 30, 30) if rng.random() < 0.5 else (240, 240, 245)
    cv2.line(canvas, p1, p2, line_color, rng.choice([1, 1, 2]))
    return _add_noise(canvas, rng)


def make_blood_meat_spot(rng: random.Random) -> np.ndarray:
    canvas, (cx, cy, ax, ay, _angle) = _blank_canvas(rng)
    n_spots = rng.choice([1, 1, 1, 2])
    for _ in range(n_spots):
        offset_x = rng.randint(-ax // 2, ax // 2)
        offset_y = rng.randint(-ay // 2, ay // 2)
        radius = rng.randint(8, 18)
        # dark reddish-brown blotch (BGR: low blue, low-mid green, mid-high red)
        spot_color = (rng.randint(10, 30), rng.randint(15, 40), rng.randint(60, 110))
        cv2.circle(canvas, (cx + offset_x, cy + offset_y), radius, spot_color, -1)
    return _add_noise(canvas, rng)


GENERATORS = {
    "good": make_good,
    "cracked-damaged": make_cracked_damaged,
    "blood-meat-spot": make_blood_meat_spot,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=120, help="Images per class (default 120)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    if OUT_DIR.exists():
        print(f"Removing existing {OUT_DIR} so this run starts clean...")
        shutil.rmtree(OUT_DIR)

    for label, gen_fn in GENERATORS.items():
        out_dir = OUT_DIR / label
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(args.count):
            img = gen_fn(rng)
            cv2.imwrite(str(out_dir / f"synthetic_{i:04d}.jpg"), img)
        print(f"{label:<18} {args.count} images -> {out_dir}")

    print(f"\nDone. {args.count * len(GENERATORS)} synthetic images written under {OUT_DIR}")
    print("Reminder: these are procedural placeholders for pipeline-testing only.")
    print("Next: python prepare_dataset.py   then   python train_yolo.py")


if __name__ == "__main__":
    main()
