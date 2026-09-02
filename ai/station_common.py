"""The pieces both listeners share.

    ai/listen_station.py   v1: one egg, one frame, one verdict (J's dataset rig).
    ai/listen_tray.py      v2: one tray, one frame, up to six verdicts (the product).

Everything in here was extracted from listen_station.py on 2026-09-02 without
changing a line of behaviour (spec D4: v1 stays provably untouched). If it is
in this file, both listeners depend on it; change it with both in mind.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np

# Re-exported so the listeners have one place to import framing from.
from capture import crop_to_zoom, open_camera  # noqa: F401

# THE BRIGHTNESS GATE (Session 12's close, written 2026-08-24).
#
# A candler that has failed does not produce a dim image, it produces a black
# one -- and the model does not error on a black image. It picks one of its
# three classes and reports it with a confidence score, because that is all a
# classifier can do. The discipline has to live OUTSIDE the model, and it has
# to run BEFORE it: check afterwards and you are arguing with a confident
# number that should never have existed.
#
# This is not hypothetical. On the first end-to-end run of this file, on
# 2026-08-24, the webcam was covered. The frame came out at mean brightness 0.9
# and the system recorded "not_an_egg, confidence 0.385" without a murmur.
#
# THE THRESHOLD IS MEASURED, NOT GUESSED. Across J's 2026-08-23 set, 38 real
# candling frames at the rig's own zoom:
#
#     darkest real candling frame    49.4   (a defective egg; an egg blocks light)
#     empty lit platform            87-215  (nothing blocking the candler)
#     covered lens                     0.9
#
# 15 sits about 3x below the darkest real frame and about 16x above a dark one.
# No egg is opaque enough to reach down to it and no dead candler climbs up.
#
# ⚠️ RIG-DEPENDENT. Exposure, candler brightness and the zoom crop all move
# these numbers. If the rig is rebuilt, re-measure rather than trusting 15:
#     py -c "import cv2,glob,statistics; print(statistics.median([cv2.imread(p).mean() for p in glob.glob('ai/dataset/train/*/*.jpg')]))"
BRIGHTNESS_MIN = 15.0

# A knocked switch comes back. Retry briefly before declaring the candler dead,
# so a two-second interruption recovers on its own and nobody ever notices.
DARK_RETRIES = 5
DARK_RETRY_SECONDS = 1.0

# Once it HAS been declared dead, stop hammering the camera and the console.
# The station is deliberately stuck at this point -- see the loop below.
DARK_HOLD_SECONDS = 5.0

MODEL_DIR = Path("ai/models")
CAPTURE_DIR = Path("ai/captures")

# The model was trained at this size -- see ai/scripts/train.py. If one changes
# the other has to change with it, or every prediction is made on a differently
# shaped image than the network was fitted to.
INPUT_SIZE = (224, 224)

# How often to ask the server whether an egg is waiting. Fast enough that the
# operator does not notice, slow enough that an idle station is not hammering
# the API several hundred times a minute.
POLL_SECONDS = 0.25

# A webcam hands back the frame it captured most recently, which may be seconds
# old if nothing has read from it for a while. Reading and discarding a few
# frames forces a genuinely current one. Without this the first egg of a session
# gets photographed as an empty platform.
STALE_FRAMES_TO_DISCARD = 4

# ⚠️ MUST MATCH THE ZOOM THE DATASET WAS SHOT AT. capture.py stamps it into every
# filename (z18 = 1.8), so it is recoverable from ai/dataset/ if nobody wrote it
# down. Getting this wrong does not crash anything; it just makes the model worse
# in a way that looks like a bad model rather than a bad setting.
DEFAULT_ZOOM = 1.0

# The load cell settles for 800 ms before the board sends a weight, but that is
# the EGG holding still, not the scene. The operator's hand is often still in
# shot when the inspection opens. Pausing here costs a fraction of a second per
# egg and buys a frame of the platform rather than of somebody reaching away
# from it. Tunable per rig with --settle, since it depends on how the operator
# actually works rather than on anything about the hardware.
CAPTURE_SETTLE_SECONDS = 0.5

# capture.py writes this when the dataset is shot, and the station has to read
# back MORE than the zoom out of it.
#
# ⚠️ pan_x/pan_y are the reason this exists. crop_to_zoom() takes an OFF-centre
# crop, and the listener used to call it with the pan defaulted to 0,0 while the
# dataset was shot with whatever the arrow keys left behind. On the rig this was
# found on, pan_y was -160 against a 360 px crop: the training images came from
# the top of the frame and the station was looking at the middle. That is not a
# subtle drift, it is close to a different picture, and it presents as "the
# camera looks tilted" rather than as a settings bug.
SETTINGS_PATH = Path(__file__).resolve().parent / "capture_settings.json"


def load_capture_settings():
    """Return capture.py's saved setup, or an empty dict if there is not one.

    Never raises. A missing or corrupt file means the CLI defaults apply, which
    is the same position the station was in before it read this at all.
    """
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return saved if isinstance(saved, dict) else {}


def setting(saved, name, kind, fallback):
    """One value out of the saved settings, coerced, with a fallback.

    bool is a subclass of int, so it is excluded explicitly: True would sail
    through an int() cast and become a zoom of 1 or a camera index of 1.
    """
    value = saved.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return kind(value)


def load_model_and_labels():
    """Import TensorFlow late, so --help and argument errors do not wait on it."""
    import tensorflow as tf

    model_path = MODEL_DIR / "egg.keras"
    if not model_path.exists():
        raise SystemExit(
            f"No model at {model_path}. Train one first with ai/scripts/train.py.\n"
            "There is nothing to classify with until the dataset exists."
        )

    model = tf.keras.models.load_model(str(model_path))
    classes = json.loads((MODEL_DIR / "classes.json").read_text())
    version = json.loads((MODEL_DIR / "version.json").read_text())

    # WARM THE MODEL BEFORE THE FIRST EGG, not during it.
    #
    # TensorFlow traces the graph on the first predict() call, not at load time.
    # Measured on this machine: first call 1.59 s, every call after it 0.12 s.
    #
    # The board gives the whole pipeline RESULT_TIMEOUT_MS to produce a verdict.
    # Spending 1.5 s of that budget on a one-off warmup made the FIRST egg of
    # every session time out on the LCD ("No response. Try again.") while the
    # verdict still landed in the database a moment later, so the dashboard
    # disagreed with the station. Paying it here costs a second of startup and
    # nothing at all per egg.
    model.predict(np.zeros((1, *INPUT_SIZE, 3), dtype=np.float32), verbose=0)

    return model, classes, version


def call(url, key, method="GET", payload=None):
    """One HTTP call carrying the device key. Returns parsed JSON, or None on 404."""
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("X-Device-Key", key)
    if data is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        detail = error.read().decode(errors="replace")[:200]
        raise RuntimeError(f"{method} {url} -> {error.code} {detail}") from error


def grab_current_frame(camera):
    """Return a frame that is actually current, not one left in the buffer."""
    for _ in range(STALE_FRAMES_TO_DISCARD):
        camera.grab()
    ok, frame = camera.read()
    if not ok:
        raise RuntimeError("Lost the camera feed. Check the cable and restart.")
    return frame


def frame_brightness(frame):
    """Mean pixel value, 0-255. Deliberately the cheapest possible check.

    Nothing clever is needed. The failure being caught is not "slightly dim",
    it is "the light is off", and that is a difference of fifty times.
    """
    return float(frame.mean())


def preprocess_frame(frame):
    """Resize to the model's input and swap BGR -> RGB. Same maths as
    ai/inference/classify.py; keep the three in step (CONTRACT 4.2)."""
    resized = cv2.resize(frame, INPUT_SIZE)
    return cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)


def raw_result_line(classes, probabilities):
    """Every class score as one JSON string. Serialised HERE, once, because
    raw_result is stored verbatim and the API validates it as a string (the
    2026-08-25 lesson)."""
    return json.dumps({name: float(score) for name, score in zip(classes, probabilities)})
