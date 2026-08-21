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
        + or =  zoom in       (also -- or _ to zoom out, 0 to reset)
        Q  quit

    ZOOM. The webcam sees more of the chamber than the egg. Zooming crops in on
    the middle of the frame so the egg fills more of the picture, and the crop
    is what gets SAVED, not just what you see. That is the point: an egg that
    fills the frame gives the model more to look at than an egg sitting in the
    middle of a mostly-black photo.

    SET THE ZOOM ONCE AND LEAVE IT. Every photo in the dataset should be framed
    the same way, because the station will be framed that way at inference too.
    Fiddling with it mid-batch teaches the model that scale is meaningless. Find
    the number on the first few shots, then start it there every time with
    --zoom 1.8 so you never have to remember. The zoom is stamped into every
    filename (z18) so a batch shot at the wrong setting can be found later
    instead of quietly poisoning the training run.

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

# Zoom is a centre crop, not an optical change -- the webcam has no zoom motor.
# Cropping throws pixels away, so there is a floor on how far in it can go
# before the saved image is too small to be worth training on.
ZOOM_MIN = 1.0
ZOOM_MAX = 4.0
ZOOM_STEP = 0.1
MIN_CROP_PIXELS = 64

# train.py feeds the network 224x224. Cropping below that means the training
# stack has to upscale, which invents nothing and just softens the very detail
# a hairline crack is made of. Warn rather than forbid -- a higher-resolution
# webcam setting fixes it without lowering the zoom.
TRAINING_INPUT_PIXELS = 224

ZOOM_IN_KEYS = {ord("+"), ord("=")}    # = as well, so nobody has to hold shift
ZOOM_OUT_KEYS = {ord("-"), ord("_")}
ZOOM_RESET_KEYS = {ord("0")}


def clamp_zoom(value):
    # round() keeps repeated += 0.1 from drifting to 1.7999999999999998, which
    # would otherwise end up in a filename.
    return round(min(ZOOM_MAX, max(ZOOM_MIN, value)), 2)


def crop_to_zoom(frame, zoom):
    """Centre-crop the frame by the zoom factor. Returns the frame itself at 1.0."""
    if zoom <= ZOOM_MIN:
        return frame

    height, width = frame.shape[:2]
    crop_width = max(MIN_CROP_PIXELS, int(width / zoom))
    crop_height = max(MIN_CROP_PIXELS, int(height / zoom))
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    return frame[top:top + crop_height, left:left + crop_width]


def zoom_tag(zoom):
    """1.8 -> 'z18'. No dot, because a dot in a filename reads as an extension."""
    return f"z{int(round(zoom * 10)):02d}"


def open_camera(index):
    """Open a camera, falling back to DirectShow if the default backend will not.

    On Windows OpenCV defaults to Media Foundation, which frequently fails or
    hangs for ten-plus seconds on high-resolution UVC webcams -- a 4K camera is
    exactly the case that trips it. DirectShow opens the same device without
    complaint. Trying the default first means nothing changes on machines where
    it already works.
    """
    camera = cv2.VideoCapture(index)
    if camera.isOpened():
        return camera

    camera.release()
    fallback = getattr(cv2, "CAP_DSHOW", None)
    if fallback is not None:
        camera = cv2.VideoCapture(index, fallback)
        if camera.isOpened():
            print(f"Camera {index} opened with the DirectShow backend (the default one refused).")
            return camera
        camera.release()
    return None


def count_images(class_name):
    folder = DATASET_ROOT / class_name
    if not folder.exists():
        return 0
    return sum(1 for path in folder.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})


def save_frame(frame, class_name, tag, zoom):
    folder = DATASET_ROOT / class_name
    folder.mkdir(parents=True, exist_ok=True)

    # Timestamp to the second plus the shooter's tag. Two people can shoot at
    # the same moment on different machines and still not collide, and the
    # filename says who took it when a photo turns out to be bad.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zoom_part = zoom_tag(zoom)
    path = folder / f"{class_name}_{tag}_{stamp}_{zoom_part}.jpg"

    # If you fire twice inside one second, don't overwrite the first shot.
    suffix = 1
    while path.exists():
        path = folder / f"{class_name}_{tag}_{stamp}_{zoom_part}_{suffix}.jpg"
        suffix += 1

    # Saved at the crop's native resolution, NOT 224x224 and NOT scaled back up
    # to the full frame size. Upscaling a crop invents no detail and only makes
    # the file bigger. train.py resizes on the way in, and keeping the originals
    # means a future model can be trained at a different size without reshooting
    # everything. The folder name is the label, so the filename is free to carry
    # the tag and the zoom without confusing training.
    cv2.imwrite(str(path), frame)
    return path


def draw_overlay(frame, counts, tag, zoom, crop_shape):
    height, width = frame.shape[:2]
    zoom_line = f"[+/-] zoom {zoom:.1f}x ({zoom_tag(zoom)})   [0] reset"
    lines = [
        f"[G] good {counts['good']}   [D] defective {counts['defective']}   [N] not_an_egg {counts['not_an_egg']}",
        zoom_line,
        f"[Q] quit    tag: {tag}",
    ]
    # The sensor resolution OpenCV actually negotiated, which is not always the
    # one the camera can do. A wide-angle webcam asked for a smaller or squarer
    # frame often CENTRE-CROPS rather than scaling, so the picture looks zoomed
    # in while the zoom factor is still 1.0. Showing both makes that obvious
    # instead of looking like a bug in the crop.
    lines.append(f"sensor {width}x{height}   saving {crop_shape[1]}x{crop_shape[0]}")

    crop_height, crop_width = crop_shape[:2]
    if min(crop_width, crop_height) < TRAINING_INPUT_PIXELS:
        lines.append(f"TOO FAR IN: saving {crop_width}x{crop_height}, training wants {TRAINING_INPUT_PIXELS}")

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
    parser.add_argument(
        "--zoom",
        type=float,
        default=ZOOM_MIN,
        help=f"Starting zoom, {ZOOM_MIN}-{ZOOM_MAX}. Pass the same number every session so the whole dataset is framed alike.",
    )
    args = parser.parse_args()

    tag = "".join(character for character in args.tag.lower() if character.isalnum())
    if not tag:
        raise SystemExit("--tag must contain at least one letter or number.")

    zoom = clamp_zoom(args.zoom)
    if zoom != args.zoom:
        print(f"--zoom {args.zoom} is outside {ZOOM_MIN}-{ZOOM_MAX}; using {zoom}.")

    camera = open_camera(args.camera)
    if camera is None:
        raise SystemExit(
            f"""Could not open camera {args.camera}.
  - The built-in camera is usually 0, so a USB webcam is 1 or 2. Try --camera 1.
  - Close anything else using it: Teams, Zoom, Discord, a browser tab.
  - Windows Settings > Privacy & security > Camera > allow desktop apps."""
        )

    counts = {name: count_images(name) for name in CLASS_KEYS.values()}
    print("Capturing. Focus the preview window, then press G / D / N to save, Q to quit.")
    print("Zoom with + and -, 0 resets. Set it before the batch and leave it alone.")
    print(f"Starting counts: {counts}")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Lost the camera feed. Check the cable and rerun.")
                break

            # What the shutter would save right now. Everything below previews
            # this, so the window is a true viewfinder rather than a hint.
            shot = crop_to_zoom(frame, zoom)

            # Blown back up to the full frame size for display only, so the
            # window does not shrink as you zoom in. The saved file keeps the
            # crop's real pixels.
            if zoom > ZOOM_MIN:
                preview = cv2.resize(shot, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
            else:
                preview = shot.copy()   # overlay on a copy, never on what gets saved

            draw_overlay(preview, counts, tag, zoom, shot.shape)
            cv2.imshow("EggMinistrator capture", preview)

            key = cv2.waitKey(1) & 0xFF
            if key in QUIT_KEYS:
                break
            if key in ZOOM_IN_KEYS:
                zoom = clamp_zoom(zoom + ZOOM_STEP)
            elif key in ZOOM_OUT_KEYS:
                zoom = clamp_zoom(zoom - ZOOM_STEP)
            elif key in ZOOM_RESET_KEYS:
                zoom = ZOOM_MIN
            elif key in CLASS_KEYS:
                class_name = CLASS_KEYS[key]
                path = save_frame(shot, class_name, tag, zoom)
                counts[class_name] += 1
                print(f"saved {path}  ({class_name}: {counts[class_name]})")
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print(f"Final counts: {counts}")
    total = sum(counts.values())
    print(f"{total} image(s) in ai/dataset/. Zip that folder and send it on.")
    if total:
        print(f"Shot at zoom {zoom:.1f}x. Use --zoom {zoom:.1f} next session so the framing matches.")

    # A model cannot learn a class it has barely seen, and it will happily call
    # everything by whichever label it saw most. Say so before it wastes a run.
    if total and min(counts.values()) * 3 < max(counts.values()):
        print("\nWARNING: the classes are badly unbalanced. Shoot more of the smaller ones")
        print("before training, or the model will just learn to guess the common class.")


if __name__ == "__main__":
    main()
