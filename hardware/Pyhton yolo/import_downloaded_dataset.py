"""Bulk-imports an externally-sourced folder of egg photos into this
project's dataset/collected/ structure, so you don't have to rename and
copy files by hand.

What it does:
  - Reads each subfolder of the source folder you point it at.
  - Maps each subfolder's name to one of the app's 3 classes (see
    FOLDER_NAME_MAP below -- add more aliases there if your folder names
    don't match).
  - Converts every image to .jpg (prepare_dataset.py only looks for *.jpg,
    so a downloaded PNG/WEBP/etc. would otherwise be silently skipped).
  - Copies into dataset/collected/<class>/, with filenames prefixed by
    their source folder so you can always trace an image back to where it
    came from later.

Usage:
    python import_downloaded_dataset.py "C:\\path\\to\\downloaded\\folder"

Then, as usual:
    python prepare_dataset.py
    python train_yolo.py

--------------------------------------------------------------------------
Before you run this, two things worth checking -- not blockers, just worth
five minutes:

1. License/provenance. Your project doc's own assumptions section states
   the team would source its own samples ("Sample collection is therefore
   treated as a scheduling risk"). If this folder came from a public
   dataset, check its license before using it in a submitted capstone
   project, and keep a note of the source for your documentation.

2. Camera/lighting mismatch. Your doc also flags this directly (Section
   3.2.4, Environmental Constraints): "Variations in lighting, camera
   position, or egg placement may affect image quality and AI
   classification accuracy." A downloaded dataset was almost certainly
   photographed on different equipment under different lighting than your
   actual station. A model trained mostly on those photos may not
   generalize well to what your ESP32-CAM/webcam actually sees. Mixing in
   a healthy number of photos from your OWN setup (via the app itself)
   matters more than the total photo count.
--------------------------------------------------------------------------
"""

import argparse
import sys
from pathlib import Path

import cv2

BASE_DIR = Path(__file__).resolve().parent
COLLECTED_DIR = BASE_DIR / "dataset" / "collected"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

# Add aliases here if your downloaded folder names don't match -- keys are
# matched case-insensitively, with spaces/underscores/hyphens ignored.
FOLDER_NAME_MAP = {
    "good": "good",
    "goodeggs": "good",
    "cracked": "cracked-damaged",
    "crack": "cracked-damaged",
    "crackeddamaged": "cracked-damaged",
    "damaged": "cracked-damaged",
    "bloodspot": "blood-meat-spot",
    "blood": "blood-meat-spot",
    "bloodmeatspot": "blood-meat-spot",
    "meatspot": "blood-meat-spot",
    # Per project doc, "spoiled"/murky eggs aren't a separate output class
    # -- merged into blood-meat-spot, the closest of the 3 defined classes.
    "spoiled": "blood-meat-spot",
    "spoilt": "blood-meat-spot",
}


def _normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="Path to the folder containing your downloaded class subfolders")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        print(f"'{source}' isn't a folder. Point this at the folder that CONTAINS your class subfolders "
              f"(the one with 'spoiled', 'cracked', etc. inside it), not one of those subfolders itself.")
        raise SystemExit(1)

    subfolders = [d for d in source.iterdir() if d.is_dir()]
    if not subfolders:
        print(f"No subfolders found inside '{source}'.")
        raise SystemExit(1)

    unmapped = []
    totals: dict[str, int] = {}

    for folder in subfolders:
        key = _normalize(folder.name)
        mapped_class = FOLDER_NAME_MAP.get(key)
        if mapped_class is None:
            unmapped.append(folder.name)
            continue

        images = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
        if not images:
            print(f"'{folder.name}' -> {mapped_class}: no image files found, skipping.")
            continue

        dest_dir = COLLECTED_DIR / mapped_class
        dest_dir.mkdir(parents=True, exist_ok=True)
        source_tag = _normalize(folder.name)

        count = 0
        for img_path in images:
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"  Couldn't read '{img_path.name}' (unsupported/corrupt?), skipping.")
                continue
            dest_name = f"{source_tag}_{img_path.stem}.jpg"
            ok = cv2.imwrite(str(dest_dir / dest_name), img)
            if ok:
                count += 1

        totals[mapped_class] = totals.get(mapped_class, 0) + count
        print(f"'{folder.name}' -> {mapped_class}: imported {count}/{len(images)} images")

    print(f"\n{'Class':<20}{'Total in dataset/collected/ now':>32}")
    print("-" * 52)
    for cls in sorted(COLLECTED_DIR.iterdir()) if COLLECTED_DIR.exists() else []:
        if cls.is_dir():
            n = len(list(cls.glob("*.jpg")))
            print(f"{cls.name:<20}{n:>32}")

    if unmapped:
        print(f"\nDidn't recognize these subfolder names, so they were skipped: {unmapped}")
        print("Rename them to match one of: good, cracked-damaged, blood-meat-spot")
        print("(or add an alias for them in FOLDER_NAME_MAP at the top of this script), then re-run.")

    print("\nNext: python prepare_dataset.py   then   python train_yolo.py")


if __name__ == "__main__":
    main()
