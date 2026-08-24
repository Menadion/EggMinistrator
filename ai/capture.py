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
        C  switch camera (cycles through 0, 1, 2 and whatever --camera you started on)
        F  toggle autofocus on/off
        [ or ]  manual focus down / up  (takes effect once autofocus is off)
        L  toggle a rule-of-thirds grid over the preview (framing aid, never saved)
        M  toggle fullscreen (also --fullscreen to start that way)
        arrow keys  pan the crop up/down/left/right (once zoomed in past 1.0x)
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
    pass --camera 1 (or 2). Index 0 is usually the built-in. You can also just
    press C while the preview is open to cycle to the next camera without
    quitting -- handy when you are not sure which index the USB webcam is on.

    FOCUS. Press F to flip the webcam's autofocus off, then [ and ] to step
    focus down or up by hand. Candling distance is close enough that autofocus
    on some webcams hunts back and forth instead of settling, so manual focus
    can be the difference between a sharp photo and a soft one. Not every
    webcam has a focus motor -- if the picture does not change, yours does not.

    IF THE PICTURE LOOKS ZOOMED IN EVEN AT SOFTWARE ZOOM 1.0X, that is the
    driver, not this script -- some webcam/phone-camera drivers digitally crop
    at their top resolution instead of scaling down. --width and --height
    (default 1280x720) ask the driver for a smaller, honest mode instead. Pass
    --width 0 --height 0 to leave the driver's own default alone.

    PAN. Once zoomed in, the arrow keys shift the crop instead of it always
    sitting dead-centre -- handy if the camera is not perfectly aligned with
    the candler. Does nothing at zoom 1.0x, since the whole frame is already
    the picture there. 0 resets pan back to centre along with the zoom.

    GRID. Press L for a rule-of-thirds grid over the preview, egg-centring at a
    glance. It is drawn on the preview only -- never on the saved file.

    FULLSCREEN. Press M to fill the screen with the preview, or start with
    --fullscreen so it opens that way. Press M again (or Q) to get the window
    back / quit.

    SETTINGS THAT STICK. Everything you set up -- camera index, zoom, pan,
    focus, grid, fullscreen, requested resolution -- is written to
    ai/capture_settings.json the instant you change it, and read back the next
    time you run the script. You frame the shot once and every later session
    opens on that framing.

    THE CAMERA ITSELF REMEMBERS NOTHING. Closing this script releases the USB
    device, and webcam drivers reset focus to their own default when that
    happens. That is fine, because the camera is not what remembers -- the file
    is. On the next run the script opens the camera and tells it the same
    numbers again. Nothing relies on the hardware holding a setting.

    Written on every change rather than on quit, so a crash, a Ctrl+C, or
    closing the window with the X still leaves the settings saved.

    The file is per-machine and gitignored: J's camera index and focus range
    are not M's. Pass --forget to delete it and start from the defaults, or
    --no-remember to run once without reading or writing it. An explicit flag
    always beats the saved file, so --zoom 1.8 still wins for that one run.

SENDING THEM BACK
    ai/dataset/ is gitignored on purpose -- photos do not belong in git. Zip the
    three class folders and send the archive. The --tag is stamped into every
    filename so two people's batches merge without overwriting each other.

    Send a SMALL first batch (10-15) and have it checked before shooting
    hundreds. Focus, framing and candler position are much cheaper to fix after
    fifteen photos than after three hundred.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import cv2

DATASET_ROOT = Path("ai/dataset")

# Where the "keep the camera how I left it" state lives. Gitignored and
# per-machine on purpose: it records one physical rig's camera index, focus
# value and framing, none of which transfer to somebody else's webcam.
SETTINGS_PATH = Path("ai/capture_settings.json")

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

# Arrow keys shift the crop instead of always centring it -- useful once
# zoomed in, if the egg is not dead-centre in the chamber. cv2.waitKey()'s
# usual `& 0xFF` masking collapses every arrow to 0, so arrows are matched
# against the UNMASKED code from cv2.waitKeyEx() instead. These extended
# codes are the ones Windows' highgui backend reports; a different platform
# would need different values here.
PAN_STEP = 20
ARROW_LEFT_KEYS = {2424832}
ARROW_UP_KEYS = {2490368}
ARROW_RIGHT_KEYS = {2555904}
ARROW_DOWN_KEYS = {2621440}

# Cycling cameras live means never having to quit and retype --camera 1 to
# find the USB webcam. The candidates are the common indices; whatever index
# the script actually started on is folded in too, so cycling always includes
# it even if someone passed --camera 3.
CAMERA_SWITCH_KEYS = {ord("c")}
CAMERA_CANDIDATES = [0, 1, 2]

# Most UVC webcams expose focus as 0-255 in fixed-size steps, so this is a
# reasonable range/step even though the real hardware range varies by camera.
AUTOFOCUS_TOGGLE_KEYS = {ord("f")}
FOCUS_IN_KEYS = {ord("]")}
FOCUS_OUT_KEYS = {ord("[")}
FOCUS_MIN = 0
FOCUS_MAX = 255
FOCUS_STEP = 5
FOCUS_DEFAULT = 128

# A modest, widely-supported request. High-res phone/webcam drivers tend to
# digitally crop at their maximum mode instead of scaling, which is what made
# camera 1 look pre-zoomed even at software zoom 1.0x -- see
# apply_requested_resolution().
DEFAULT_CAPTURE_WIDTH = 1280
DEFAULT_CAPTURE_HEIGHT = 720

WINDOW_NAME = "EggMinistrator capture"

GRID_TOGGLE_KEYS = {ord("l")}
GRID_COLOR = (0, 220, 0)   # drawn on the preview only, so it never ends up in a saved photo

FULLSCREEN_TOGGLE_KEYS = {ord("m")}


def clamp_zoom(value):
    # round() keeps repeated += 0.1 from drifting to 1.7999999999999998, which
    # would otherwise end up in a filename.
    return round(min(ZOOM_MAX, max(ZOOM_MIN, value)), 2)


def clamp_focus(value):
    return int(min(FOCUS_MAX, max(FOCUS_MIN, value)))


def pan_bounds(frame_shape, zoom):
    """How far the crop can move off-centre, in pixels, each direction."""
    height, width = frame_shape[:2]
    crop_width = max(MIN_CROP_PIXELS, int(width / zoom))
    crop_height = max(MIN_CROP_PIXELS, int(height / zoom))
    return (width - crop_width) // 2, (height - crop_height) // 2


def clamp_pan(value, max_value):
    return max(-max_value, min(max_value, value))


def crop_to_zoom(frame, zoom, pan_x=0, pan_y=0):
    """Off-centre-crop the frame by the zoom factor and pan offset.

    Returns the frame itself at 1.0 zoom -- there is nothing to pan when the
    whole frame is already the picture.
    """
    if zoom <= ZOOM_MIN:
        return frame

    height, width = frame.shape[:2]
    crop_width = max(MIN_CROP_PIXELS, int(width / zoom))
    crop_height = max(MIN_CROP_PIXELS, int(height / zoom))
    max_left = width - crop_width
    max_top = height - crop_height

    # Clamped again here (not just where pan_x/pan_y are updated) so a pan
    # left over from a larger zoom level can never push the crop off the
    # edge of the frame once zoom changes.
    left = min(max_left, max(0, max_left // 2 + pan_x))
    top = min(max_top, max(0, max_top // 2 + pan_y))
    return frame[top:top + crop_height, left:left + crop_width]


def zoom_tag(zoom):
    """1.8 -> 'z18'. No dot, because a dot in a filename reads as an extension."""
    return f"z{int(round(zoom * 10)):02d}"


def resize_window_to_frame(frame):
    """Make the window match the frame's own resolution.

    WINDOW_NORMAL (needed so M can toggle fullscreen) does not autosize to the
    image the way the old default window did. Left alone, the window can open
    at whatever small size the platform defaults to, and everything drawn on
    the preview -- overlay text included -- gets squeezed down to fit it,
    which is what made the controls unreadable.
    """
    height, width = frame.shape[:2]
    cv2.resizeWindow(WINDOW_NAME, width, height)


def draw_grid(frame):
    """Rule-of-thirds lines over the preview, to help centre the egg by eye.

    Called on the preview copy only, same as draw_overlay -- it must never
    touch `shot`, the frame that actually gets saved.
    """
    height, width = frame.shape[:2]
    for fraction in (1 / 3, 2 / 3):
        x = int(width * fraction)
        cv2.line(frame, (x, 0), (x, height), GRID_COLOR, 1, cv2.LINE_AA)
        y = int(height * fraction)
        cv2.line(frame, (0, y), (width, y), GRID_COLOR, 1, cv2.LINE_AA)


def apply_requested_resolution(camera, width, height):
    """Ask the driver for a specific frame size, if one was requested.

    Some webcam/phone-camera drivers only hand back the full sensor view at a
    modest requested resolution; asked for their maximum, they digitally zoom
    in and crop instead of scaling, so the picture looks zoomed even though
    crop_to_zoom never touched it. Requesting a sane size up front (the same
    one for every camera index) heads that off, so switching cameras with C
    does not also silently switch how tightly framed the shot is.
    """
    if width:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


def open_camera(index, width=None, height=None):
    """Open a camera, falling back to DirectShow if the default backend will not.

    On Windows OpenCV defaults to Media Foundation, which frequently fails or
    hangs for ten-plus seconds on high-resolution UVC webcams -- a 4K camera is
    exactly the case that trips it. DirectShow opens the same device without
    complaint. Trying the default first means nothing changes on machines where
    it already works.
    """
    camera = cv2.VideoCapture(index)
    if camera.isOpened():
        apply_requested_resolution(camera, width, height)
        return camera

    camera.release()
    fallback = getattr(cv2, "CAP_DSHOW", None)
    if fallback is not None:
        camera = cv2.VideoCapture(index, fallback)
        if camera.isOpened():
            apply_requested_resolution(camera, width, height)
            print(f"Camera {index} opened with the DirectShow backend (the default one refused).")
            return camera
        camera.release()
    return None


def open_next_camera(current_camera, current_index, candidates, width=None, height=None):
    """Cycle to the next camera index that actually opens.

    Tries each candidate in turn (starting right after the current index,
    wrapping around) and keeps the current camera if nothing else opens --
    switching should never leave the preview with no feed at all.
    """
    ordered = sorted(set(candidates) | {current_index})
    start_pos = ordered.index(current_index)

    for step in range(1, len(ordered)):
        candidate_index = ordered[(start_pos + step) % len(ordered)]
        candidate_camera = open_camera(candidate_index, width, height)
        if candidate_camera is not None:
            current_camera.release()
            print(f"Switched to camera {candidate_index}.")
            return candidate_camera, candidate_index
        print(f"Camera {candidate_index} did not open, trying the next one...")

    print(f"No other camera available; staying on camera {current_index}.")
    return current_camera, current_index


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


def draw_overlay(frame, counts, tag, zoom, crop_shape, camera_index, autofocus, focus_value, grid_on, fullscreen, pan_x, pan_y):
    height, width = frame.shape[:2]
    pan_text = f"   [arrows] pan ({pan_x:+d},{pan_y:+d})" if zoom > ZOOM_MIN else "   [arrows] pan (zoom in first)"
    zoom_line = f"[+/-] zoom {zoom:.1f}x ({zoom_tag(zoom)})   [0] reset{pan_text}"
    focus_text = "auto" if autofocus else str(focus_value)
    camera_line = f"[C] camera {camera_index}   [F] autofocus {'ON' if autofocus else 'OFF'}   [[/]] focus {focus_text}"
    display_line = f"[L] grid {'ON' if grid_on else 'OFF'}   [M] fullscreen {'ON' if fullscreen else 'OFF'}"
    lines = [
        f"[G] good {counts['good']}   [D] defective {counts['defective']}   [N] not_an_egg {counts['not_an_egg']}",
        zoom_line,
        camera_line,
        display_line,
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


def load_settings():
    """Read the saved camera setup, or {} if there is nothing usable to read.

    Never raises. A missing file is the normal first-run case, and a corrupt
    one must not stop a shoot -- the defaults are always a working setup, so
    the worst case is re-framing once.
    """
    if not SETTINGS_PATH.exists():
        return {}
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as file:
            saved = json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Could not read {SETTINGS_PATH} ({error}); starting from the defaults.")
        return {}
    if not isinstance(saved, dict):
        print(f"{SETTINGS_PATH} is not a settings object; starting from the defaults.")
        return {}
    return saved


def save_settings(state):
    """Write the current setup. Warns once and carries on if the disk says no.

    Called on every change rather than at exit, so settings survive a crash or
    a window closed with the X instead of Q.
    """
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, sort_keys=True)
    except OSError as error:
        print(f"Could not write {SETTINGS_PATH} ({error}); this session will not be remembered.")


def main():
    parser = argparse.ArgumentParser(description="Capture labelled egg photos into ai/dataset/.")
    parser.add_argument("--tag", required=True, help="Who is shooting, e.g. --tag jasfer. Goes into every filename.")
    parser.add_argument("--camera", type=int, default=None, help="Camera index. 0 is usually the built-in; try 1 for a USB webcam. Defaults to the saved one.")
    parser.add_argument(
        "--zoom",
        type=float,
        default=None,
        help=f"Starting zoom, {ZOOM_MIN}-{ZOOM_MAX}. Pass the same number every session so the whole dataset is framed alike.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help=f"Requested capture width (default {DEFAULT_CAPTURE_WIDTH}). Some drivers digitally "
        "crop instead of scaling at their maximum resolution, which looks zoomed even at software "
        "zoom 1.0x; a modest width usually gets the full sensor view back. Pass 0 to leave it alone.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help=f"Requested capture height (default {DEFAULT_CAPTURE_HEIGHT}), paired with --width. Pass 0 to leave it alone.",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        default=None,
        help="Start with the preview filling the screen. Press M any time to toggle it instead.",
    )
    parser.add_argument(
        "--forget",
        action="store_true",
        help=f"Delete {SETTINGS_PATH} and start from the built-in defaults. Use it when the rig moved.",
    )
    parser.add_argument(
        "--no-remember",
        action="store_true",
        help="Run without reading or writing the saved settings. Leaves an existing file untouched.",
    )
    args = parser.parse_args()

    tag = "".join(character for character in args.tag.lower() if character.isalnum())
    if not tag:
        raise SystemExit("--tag must contain at least one letter or number.")

    if args.forget and SETTINGS_PATH.exists():
        SETTINGS_PATH.unlink()
        print(f"Deleted {SETTINGS_PATH}; starting from the built-in defaults.")

    remember = not args.no_remember
    saved = load_settings() if remember and not args.forget else {}

    def setting(name, flag_value, default):
        """Explicit flag beats the saved file, which beats the built-in default.

        A flag that was not passed arrives as None -- which is why every
        argparse default above is None rather than the real default. The real
        defaults live here, where the saved file can be consulted first.
        """
        if flag_value is not None:
            return flag_value
        if name in saved:
            return saved[name]
        return default

    # Wrapped in try/except so a hand-edited settings file with a string where
    # a number should be re-frames the shot instead of crashing the shoot.
    try:
        camera_index = int(setting("camera", args.camera, 0))
        width = int(setting("width", args.width, DEFAULT_CAPTURE_WIDTH))
        height = int(setting("height", args.height, DEFAULT_CAPTURE_HEIGHT))
        requested_zoom = float(setting("zoom", args.zoom, ZOOM_MIN))
        pan_x = int(setting("pan_x", None, 0))
        pan_y = int(setting("pan_y", None, 0))
        autofocus = bool(setting("autofocus", None, True))
        focus_value = clamp_focus(setting("focus", None, FOCUS_DEFAULT))
        grid_on = bool(setting("grid", None, False))
        fullscreen = bool(setting("fullscreen", args.fullscreen, False))
    except (TypeError, ValueError) as error:
        print(f"{SETTINGS_PATH} has a bad value ({error}); starting from the defaults.")
        saved = {}
        camera_index = args.camera if args.camera is not None else 0
        width = args.width if args.width is not None else DEFAULT_CAPTURE_WIDTH
        height = args.height if args.height is not None else DEFAULT_CAPTURE_HEIGHT
        requested_zoom = args.zoom if args.zoom is not None else ZOOM_MIN
        pan_x, pan_y = 0, 0
        autofocus, focus_value = True, FOCUS_DEFAULT
        grid_on, fullscreen = False, bool(args.fullscreen)

    zoom = clamp_zoom(requested_zoom)
    if zoom != requested_zoom:
        print(f"zoom {requested_zoom} is outside {ZOOM_MIN}-{ZOOM_MAX}; using {zoom}.")

    if saved:
        print(f"Restored the last setup from {SETTINGS_PATH} (camera {camera_index}, zoom {zoom:.1f}x).")
        print("Pass --forget to start from the defaults instead, e.g. after the rig has moved.")

    camera = open_camera(camera_index, width, height)
    if camera is None:
        raise SystemExit(
            f"""Could not open camera {camera_index}.
  - The built-in camera is usually 0, so a USB webcam is 1 or 2. Try --camera 1.
  - Close anything else using it: Teams, Zoom, Discord, a browser tab.
  - Windows Settings > Privacy & security > Camera > allow desktop apps.
  - If the saved camera index is simply gone, --forget clears it."""
        )

    # THE POINT OF THE SETTINGS FILE. Releasing the camera at the end of the
    # last run handed the device back to the driver, which reset focus to its
    # own default -- webcams do not remember anything across a process exit and
    # nothing here assumes they do. The file remembered instead, so the camera
    # gets told the same numbers again now. Only touched when the saved state
    # says autofocus was deliberately turned off, so a rig nobody has focused
    # by hand is still left exactly as the driver set it up.
    if not autofocus:
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        applied = camera.set(cv2.CAP_PROP_FOCUS, focus_value)
        print(f"Re-applied manual focus {focus_value}." + ("" if applied else " (this camera may not support it.)"))

    window_sized = False   # set once the first frame's real resolution is known

    def snapshot():
        """The current setup as it would be written to disk.

        Reads the enclosing local variables at call time, so it stays correct
        as they are reassigned in the loop, and a setting added later only has
        to be added here.
        """
        return {
            "camera": camera_index,
            "width": width,
            "height": height,
            "zoom": zoom,
            "pan_x": pan_x,
            "pan_y": pan_y,
            "autofocus": autofocus,
            "focus": focus_value,
            "grid": grid_on,
            "fullscreen": fullscreen,
        }

    last_saved = snapshot()

    # WINDOW_NORMAL (not the imshow default) so setWindowProperty can flip it
    # in and out of fullscreen later -- an autosize window can't be resized.
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    if fullscreen:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        window_sized = True   # fullscreen controls its own size; don't fight it

    counts = {name: count_images(name) for name in CLASS_KEYS.values()}
    print("Capturing. Focus the preview window, then press G / D / N to save, Q to quit.")
    print("Zoom with + and -, 0 resets. Set it before the batch and leave it alone.")
    print("Press C to switch camera, F to toggle autofocus, [ and ] for manual focus.")
    print("Press L for a framing grid, M for fullscreen, arrow keys to pan once zoomed in.")
    print(f"Starting counts: {counts}")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Lost the camera feed. Check the cable and rerun.")
                break

            if not window_sized:
                resize_window_to_frame(frame)
                window_sized = True

            # What the shutter would save right now. Everything below previews
            # this, so the window is a true viewfinder rather than a hint.
            shot = crop_to_zoom(frame, zoom, pan_x, pan_y)

            # Blown back up to the full frame size for display only, so the
            # window does not shrink as you zoom in. The saved file keeps the
            # crop's real pixels.
            if zoom > ZOOM_MIN:
                preview = cv2.resize(shot, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
            else:
                preview = shot.copy()   # overlay on a copy, never on what gets saved

            if grid_on:
                draw_grid(preview)
            draw_overlay(
                preview, counts, tag, zoom, shot.shape, camera_index, autofocus, focus_value,
                grid_on, fullscreen, pan_x, pan_y,
            )
            cv2.imshow(WINDOW_NAME, preview)

            # waitKeyEx (not waitKey) because arrow keys only survive in the
            # unmasked code -- waitKey()'s usual `& 0xFF` collapses all four
            # of them to the same value.
            raw_key = cv2.waitKeyEx(1)
            key = raw_key & 0xFF
            if key in QUIT_KEYS:
                break
            if key in ZOOM_IN_KEYS:
                zoom = clamp_zoom(zoom + ZOOM_STEP)
            elif key in ZOOM_OUT_KEYS:
                zoom = clamp_zoom(zoom - ZOOM_STEP)
            elif key in ZOOM_RESET_KEYS:
                zoom = ZOOM_MIN
                pan_x, pan_y = 0, 0
            elif raw_key in ARROW_LEFT_KEYS or raw_key in ARROW_RIGHT_KEYS or raw_key in ARROW_UP_KEYS or raw_key in ARROW_DOWN_KEYS:
                max_x, max_y = pan_bounds(frame.shape, zoom)
                if raw_key in ARROW_LEFT_KEYS:
                    pan_x = clamp_pan(pan_x - PAN_STEP, max_x)
                elif raw_key in ARROW_RIGHT_KEYS:
                    pan_x = clamp_pan(pan_x + PAN_STEP, max_x)
                elif raw_key in ARROW_UP_KEYS:
                    pan_y = clamp_pan(pan_y - PAN_STEP, max_y)
                elif raw_key in ARROW_DOWN_KEYS:
                    pan_y = clamp_pan(pan_y + PAN_STEP, max_y)
            elif key in CAMERA_SWITCH_KEYS:
                camera, camera_index = open_next_camera(
                    camera, camera_index, CAMERA_CANDIDATES, width, height
                )
                # The new camera may negotiate a different resolution, so
                # re-size the window to it once its first frame comes in
                # (skipped while fullscreen -- that size is not ours to pick).
                window_sized = fullscreen
                # Re-apply focus state to whatever camera we ended up on, so
                # switching cameras does not silently forget a manual focus.
                camera.set(cv2.CAP_PROP_AUTOFOCUS, 1 if autofocus else 0)
                if not autofocus:
                    camera.set(cv2.CAP_PROP_FOCUS, focus_value)
            elif key in AUTOFOCUS_TOGGLE_KEYS:
                autofocus = not autofocus
                applied = camera.set(cv2.CAP_PROP_AUTOFOCUS, 1 if autofocus else 0)
                if not autofocus:
                    camera.set(cv2.CAP_PROP_FOCUS, focus_value)
                print(f"Autofocus {'on' if autofocus else 'off'}." + ("" if applied else " (this camera may not support it.)"))
            elif key in FOCUS_IN_KEYS or key in FOCUS_OUT_KEYS:
                if autofocus:
                    autofocus = False
                    camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                step = FOCUS_STEP if key in FOCUS_IN_KEYS else -FOCUS_STEP
                focus_value = clamp_focus(focus_value + step)
                applied = camera.set(cv2.CAP_PROP_FOCUS, focus_value)
                print(f"Focus {focus_value}." + ("" if applied else " (this camera may not support manual focus.)"))
            elif key in GRID_TOGGLE_KEYS:
                grid_on = not grid_on
            elif key in FULLSCREEN_TOGGLE_KEYS:
                fullscreen = not fullscreen
                cv2.setWindowProperty(
                    WINDOW_NAME,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL,
                )
                # Coming back out of fullscreen needs an explicit resize too,
                # or the window is left at whatever size fullscreen leaves it.
                window_sized = fullscreen
            elif key in CLASS_KEYS:
                class_name = CLASS_KEYS[key]
                path = save_frame(shot, class_name, tag, zoom)
                counts[class_name] += 1
                print(f"saved {path}  ({class_name}: {counts[class_name]})")

            # Saved here rather than at exit, so the setup survives a crash or
            # a window closed with the X. Compared against the last write so a
            # loop running at camera framerate only touches the disk when a
            # key actually changed something.
            if remember:
                state = snapshot()
                if state != last_saved:
                    save_settings(state)
                    last_saved = state
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print(f"Final counts: {counts}")
    total = sum(counts.values())
    print(f"{total} image(s) in ai/dataset/. Zip that folder and send it on.")
    if total:
        if remember:
            print(f"Shot at zoom {zoom:.1f}x. Saved to {SETTINGS_PATH}, so the next run opens framed the same way.")
        else:
            print(f"Shot at zoom {zoom:.1f}x. Use --zoom {zoom:.1f} next session so the framing matches.")

    # A model cannot learn a class it has barely seen, and it will happily call
    # everything by whichever label it saw most. Say so before it wastes a run.
    if total and min(counts.values()) * 3 < max(counts.values()):
        print("\nWARNING: the classes are badly unbalanced. Shoot more of the smaller ones")
        print("before training, or the model will just learn to guess the common class.")


if __name__ == "__main__":
    main()
