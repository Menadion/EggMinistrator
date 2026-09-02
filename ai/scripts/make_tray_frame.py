"""Build a synthetic lid-close frame: k dataset crops pasted into a dark 4K
canvas at the tray map's rectangles, plus a JSON answer key.

WHAT THIS IS FOR
    Testing the fan-out before the enclosure exists. listen_tray.py --frame
    reads the JPEG this writes instead of opening a camera; everything from
    occupancy onward runs on real code. The JSON says which class went into
    which slot so the end-to-end test can check the database against it.

WHAT IT DOES NOT TEST
    The model. The crops come from the model's own training set, so a correct
    verdict proves the right pixels reached the right slot, nothing more.
    Accuracy needs real eggs it has never seen (J's track) and real tray
    photos from the finished rig. A pasted crop on black does not reproduce
    light leaking between holes or tray shadows.

RUNNING IT
    py ai/scripts/make_tray_frame.py --eggs 4 --seed 7 --default-map
    -> ai/captures/synthetic/tray_7.jpg + tray_7.json

    --classes good,defective   (default) which folders to draw from
    --source ai/dataset/train  where the class folders are
    --map ai/tray_map.json     the calibrated map; --default-map to ignore it
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # ai/ on the path, as the listeners have it
from tray_map import DEFAULT_TRAY_MAP, SLOT_COUNT, TRAY_MAP_PATH, load_tray_map, slot_rect  # noqa: E402

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


def pick_sources(source_dir, classes, k, rng):
    """k (class, path) pairs drawn with replacement across the asked classes."""
    pool = []
    for cls in classes:
        folder = Path(source_dir) / cls
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES) if folder.is_dir() else []
        pool.extend((cls, path) for path in files)
    if not pool:
        raise SystemExit(f"No images under {source_dir} for classes {classes}. Is the dataset present?")
    return [rng.choice(pool) for _ in range(k)]


def build_frame(tray_map, assignments):
    """assignments: slot -> image path, or None for an empty (lit) hole."""
    capture = tray_map["capture"]
    frame = np.zeros((capture["height"], capture["width"], 3), dtype=np.uint8)
    for slot in range(1, SLOT_COUNT + 1):
        x, y, w, h = slot_rect(tray_map, slot)
        source = assignments.get(slot)
        if source is None:
            level = int(round(tray_map["occupancy"]["levels"][str(slot)]["empty"]))
            frame[y:y + h, x:x + w] = level
            continue
        image = cv2.imread(str(source))
        if image is None:
            raise SystemExit(f"Could not read {source}")
        frame[y:y + h, x:x + w] = cv2.resize(image, (w, h))
    return frame


def write_frame(out_dir, name, frame, truth):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jpg = out_dir / f"{name}.jpg"
    meta = out_dir / f"{name}.json"
    cv2.imwrite(str(jpg), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    truth = {"frame": jpg.as_posix(), **truth}
    meta.write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")
    return jpg, meta


def main():
    parser = argparse.ArgumentParser(description="Build a synthetic tray frame and its answer key.")
    parser.add_argument("--eggs", type=int, default=SLOT_COUNT, help="how many slots to fill, 1..6, always the prefix 1..k")
    parser.add_argument("--source", default="ai/dataset/train")
    parser.add_argument("--classes", default="good,defective")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", default="ai/captures/synthetic")
    parser.add_argument("--map", default=str(TRAY_MAP_PATH))
    parser.add_argument("--default-map", dest="default_map", action="store_true", help="use the built-in synthetic geometry even if a calibrated map exists")
    parser.add_argument("--name", default=None)
    args = parser.parse_args()
    if not 1 <= args.eggs <= SLOT_COUNT:
        raise SystemExit(f"--eggs must be 1..{SLOT_COUNT}")

    tray_map = DEFAULT_TRAY_MAP if args.default_map else load_tray_map(args.map)
    rng = random.Random(args.seed)
    classes = [c.strip() for c in args.classes.split(",") if c.strip()]
    picks = pick_sources(args.source, classes, args.eggs, rng)
    assignments = {slot: path for slot, (_, path) in zip(range(1, args.eggs + 1), picks)}
    frame = build_frame(tray_map, assignments)

    name = args.name or f"tray_{args.seed if args.seed is not None else datetime.now().strftime('%Y%m%d_%H%M%S')}"
    truth = {
        "tray_map": "default" if args.default_map else Path(args.map).as_posix(),
        "eggs": args.eggs,
        "slots": {str(slot): ({"class": picks[slot - 1][0], "source": picks[slot - 1][1].as_posix()} if slot <= args.eggs else None)
                  for slot in range(1, SLOT_COUNT + 1)},
    }
    jpg, meta = write_frame(args.out, name, frame, truth)
    print(f"wrote {jpg} and {meta}")
    for slot in range(1, SLOT_COUNT + 1):
        entry = truth["slots"][str(slot)]
        print(f"  slot {slot}: {entry['class'] + '  <- ' + entry['source'] if entry else 'empty'}")


if __name__ == "__main__":
    main()
