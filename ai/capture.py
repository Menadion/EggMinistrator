"""Shoot labelled egg photos straight into the dataset folders.

FR-01: capture egg images using a stationary camera.
FR-11: capture a candling image under transillumination.

WHO RUNS THIS
    Whoever has the webcam and the candler. Collection is team work, not one
    person's job -- see CONTRACT.md section 7 item 1. Read
    ai/how-to-add-images.md before shooting; it covers how to set the egg up.

WHAT IT NEEDS
    pip install opencv-python

    That is the whole dependency list. This script deliberately does NOT import
    TensorFlow, so you do not need the training stack on the machine that takes
    the photos.

RUNNING IT
    py ai/capture.py --tag yourname

    A preview window opens. Put an egg on the candler, look at it, then press
    the key for what it actually is:

        G  good
        D  defective
        N  not an egg   (empty platform, a hand, anything that is not one egg)
        Q  quit

    You label at the moment you shoot, because that is when you are looking at
    the egg and know what it is. Sorting 200 unlabelled photos afterwards means
    deciding all over again from a screen, slower and with more mistakes.

    If the preview shows your laptop's built-in camera instead of the USB one,
    pass --camera 1 (or 2). Index 0 is usually the built-in.

SENDING THEM BACK
    ai/dataset/ is gitignored on purpose -- photos do not belong in git. Zip the
    three class folders and send the archive. The --tag is stamped into every
    filename so two people's batches merge without overwriting each other.

    Send a SMALL first batch (10-15) and have it checked before shooting
    hundreds. Focus, framing and candler position are much cheaper to fix after
    fifteen photos than after three hundred.
"""

import argparse
from datetime import datetime
from pathlib import Path

import cv2

DATASET_ROOT = Path("ai/dataset")

# The three class folders train.py reads. Decision G spelling, lowercase, with
# underscores -- these names ARE the labels, so do not rename them casually.
CLASS_KEYS = {
    ord("g"): "good",
    ord("d"): "defective",
    ord("n"): "not_an_egg",
}

QUIT_KEYS = {ord("q"), 27}   # q or Esc


def count_images(class_name):
    folder = DATASET_ROOT / class_name
    if not folder.exists():
        return 0
    return sum(1 for path in folder.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})


def save_frame(frame, class_name, tag):
    folder = DATASET_ROOT / class_name
    folder.mkdir(parents=True, exist_ok=True)

    # Timestamp to the second plus the shooter's tag. Two people can shoot at
    # the same moment on different machines and still not collide, and the
    # filename says who took it when a photo turns out to be bad.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = folder / f"{class_name}_{tag}_{stamp}.jpg"

    # If you fire twice inside one second, don't overwrite the first shot.
    suffix = 1
    while path.exists():
        path = folder / f"{class_name}_{tag}_{stamp}_{suffix}.jpg"
        suffix += 1

    # Saved at the camera's native resolution, NOT 224x224. train.py resizes on
    # the way in, and keeping the originals means a future model can be trained
    # at a different size without reshooting everything.
    cv2.imwrite(str(path), frame)
    return path


def draw_overlay(frame, counts, tag):
    lines = [
        f"[G] good {counts['good']}   [D] defective {counts['defective']}   [N] not_an_egg {counts['not_an_egg']}",
        f"[Q] quit    tag: {tag}",
    ]
    for index, text in enumerate(lines):
        origin = (10, 25 + index * 26)
        # Drawn twice: a thick dark pass under a thin light one, so the text
        # stays readable against both a bright candled egg and a dark chamber.
        cv2.putText(frame, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)


def main():
    parser = argparse.ArgumentParser(description="Capture labelled egg photos into ai/dataset/.")
    parser.add_argument("--tag", required=True, help="Who is shooting, e.g. --tag jasfer. Goes into every filename.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index. 0 is usually the built-in; try 1 for a USB webcam.")
    args = parser.parse_args()

    tag = "".join(character for character in args.tag.lower() if character.isalnum())
    if not tag:
        raise SystemExit("--tag must contain at least one letter or number.")

    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        raise SystemExit(
            f"Could not open camera {args.camera}. If the USB webcam is plugged in, try --camera 1 or --camera 2."
        )

    counts = {name: count_images(name) for name in CLASS_KEYS.values()}
    print("Capturing. Focus the preview window, then press G / D / N to save, Q to quit.")
    print(f"Starting counts: {counts}")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Lost the camera feed. Check the cable and rerun.")
                break

            preview = frame.copy()          # overlay on the copy, never on what gets saved
            draw_overlay(preview, counts, tag)
            cv2.imshow("EggMinistrator capture", preview)

            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                break
            if key in CLASS_KEYS:
                class_name = CLASS_KEYS[key]
                path = save_frame(frame, class_name, tag)
                counts[class_name] += 1
                print(f"saved {path}  ({class_name}: {counts[class_name]})")
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print(f"Final counts: {counts}")
    total = sum(counts.values())
    print(f"{total} image(s) in ai/dataset/. Zip that folder and send it on.")

    # A model cannot learn a class it has barely seen, and it will happily call
    # everything by whichever label it saw most. Say so before it wastes a run.
    if total and min(counts.values()) * 3 < max(counts.values()):
        print("\nWARNING: the classes are badly unbalanced. Shoot more of the smaller ones")
        print("before training, or the model will just learn to guess the common class.")


if __name__ == "__main__":
    main()
