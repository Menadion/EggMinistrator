"""Watch for inspections opened by the board, photograph the egg, classify it, report back.

THIS IS THE MISSING MIDDLE OF THE SYSTEM (FR-01, FR-11).

    board posts a weight  ->  server opens an inspection row  ->  ??? -> verdict

    This file is the ???. Without it the board can weigh an egg and the model can
    classify a file on disk, but nothing connects the two, so no inspection ever
    gets a verdict. See CONTRACT.md section 4.1.

NOT ai/capture.py. That is the dataset collection tool: a person watches a preview
window, presses G / D / N, and images go into ai/dataset/ folders and never touch
the API. Same webcam, completely different job. Confusing the two is easy and has
already happened once.

WHY IT IS A LONG-RUNNING PROCESS
    Loading TensorFlow takes seconds and opening a webcam takes about a second.
    The paper targets three seconds per egg. So the model stays loaded and the
    camera stays open, and this sits in a loop. Spawning a script per egg cannot
    hit the target and is not worth trying.

WHAT IT NEEDS
    pip install opencv-python tensorflow

    A trained model at ai/models/egg.keras, plus classes.json and version.json
    beside it. If ai/models/ is empty this will not start, and that is correct:
    there is nothing to classify with.

RUNNING IT
    py ai/listen_station.py

    Environment, or pass the flags:
        DEVICE_API_KEY   must match backend/.env exactly, or every call is a 401
        STATION_API      default http://127.0.0.1:3001

    Leave it running beside the backend. It prints one line per egg.

STOPPING IT
    Ctrl+C. The camera is released on the way out.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# The SAME centre-crop used when the dataset was shot. Imported rather than
# copied, deliberately: if these two ever disagree, the model trains on one
# framing and infers on another, and nothing about the failure looks like a
# framing problem. See --zoom below.
from capture import crop_to_zoom, open_camera

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


def find_open_inspection(base, key):
    """Ask the server whether an inspection is waiting for a verdict.

    THIS IS THE ONE FUNCTION TO CHANGE if the trigger mechanism changes. It
    currently expects GET /api/inspections/pending, which returns the oldest
    inspection that has no assessment yet, or 404 when there is nothing waiting.
    Swapping to a database read or a different endpoint touches only this.
    """
    return call(f"{base}/api/inspections/pending", key)


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


def grab_lit_frame(camera, zoom, pan_x=0, pan_y=0):
    """Return (frame, brightness) once the candler is clearly on, or (None, b).

    Retries rather than failing on the first dark frame: an operator who
    brushed the switch has a few seconds to put it back, and a recovery nobody
    notices is worth more than a correct error message.
    """
    brightness = 0.0
    for attempt in range(DARK_RETRIES):
        frame = crop_to_zoom(grab_current_frame(camera), zoom, pan_x, pan_y)
        brightness = frame_brightness(frame)
        if brightness >= BRIGHTNESS_MIN:
            return frame, brightness
        if attempt < DARK_RETRIES - 1:
            time.sleep(DARK_RETRY_SECONDS)
    return None, brightness


def save_frame(frame, inspection_id):
    """Write the image to disk and return the path recorded against the inspection.

    The API requires an image path on every assessment, and it is also the only
    audit trail: without the file, a disputed verdict cannot be reviewed later.
    """
    day_folder = CAPTURE_DIR / datetime.now().strftime("%Y%m%d")
    day_folder.mkdir(parents=True, exist_ok=True)
    path = day_folder / f"inspection_{inspection_id}.jpg"
    cv2.imwrite(str(path), frame)
    return path.as_posix()


def classify(model, classes, version, frame, image_path):
    """Same maths as ai/inference/classify.py, on a frame already in memory.

    classify.py reads a file off disk and prints JSON, which is right for
    checking one photo by hand and wrong for a loop that already has the pixels.
    Keep the two in step: if the preprocessing changes in one, change it in both.
    """
    resized = cv2.resize(frame, INPUT_SIZE)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    batch = np.expand_dims(rgb, 0)

    started = time.perf_counter()
    probabilities = model.predict(batch, verbose=0)[0]
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    return {
        "image": image_path,
        "class": classes[int(probabilities.argmax())],
        "confidence": float(probabilities.max()),
        "model_name": version["name"],
        "model_version": version["version"],
        "inference_time_ms": elapsed_ms,
        # Every class score, not just the winner. A verdict of "defective" at 0.51
        # and one at 0.99 look identical on the dashboard; this is what tells them
        # apart when someone questions a call after the fact.
        #
        # Serialised HERE rather than sent as an object. raw_result is LONGTEXT and
        # the API stores the line verbatim, so it validates with hasText() before
        # JSON.parse(): an object arrives as a JSON object, fails the string check,
        # and every inspection comes back 400 RAW_RESULT_REQUIRED with the image
        # already written to disk. Found the night before the demo, 2026-08-25.
        "raw_result": json.dumps({name: float(score) for name, score in zip(classes, probabilities)}),
    }


def main():
    # capture.py's own record of how the dataset was shot. Every framing default
    # below comes from here, so the station reproduces the dataset's framing
    # without anyone having to retype it, and gets it wrong in one place instead
    # of four if the file is missing.
    saved = load_capture_settings()

    parser = argparse.ArgumentParser(description="Classify eggs as the board opens inspections.")
    parser.add_argument("--camera", type=int, default=setting(saved, "camera", int, 0), help="Camera index. Defaults to the one capture.py last used. Indices move between reboots and USB ports, so override with 1 or 2 if the wrong camera opens.")
    parser.add_argument("--zoom", type=float, default=setting(saved, "zoom", float, DEFAULT_ZOOM), help="MUST match the zoom the dataset was shot at, e.g. --zoom 1.8. Defaults to the saved one.")
    parser.add_argument("--pan-x", type=int, dest="pan_x", default=setting(saved, "pan_x", int, 0), help="Horizontal crop offset in pixels. MUST match the dataset, same as zoom.")
    parser.add_argument("--pan-y", type=int, dest="pan_y", default=setting(saved, "pan_y", int, 0), help="Vertical crop offset in pixels. MUST match the dataset, same as zoom.")
    parser.add_argument("--settle", type=float, default=CAPTURE_SETTLE_SECONDS, help="Seconds to wait after an inspection opens before photographing, so the operator's hand is out of shot. Raise it if captures look rushed.")
    parser.add_argument("--api", default=os.environ.get("STATION_API", "http://127.0.0.1:3001"), help="Backend base URL.")
    parser.add_argument("--key", default=os.environ.get("DEVICE_API_KEY", ""), help="Device key. Must match backend/.env.")
    arguments = parser.parse_args()

    if not arguments.key:
        raise SystemExit(
            "No device key. Set DEVICE_API_KEY or pass --key.\n"
            "It must match DEVICE_API_KEY in backend/.env exactly, or every call returns 401."
        )

    model, classes, version = load_model_and_labels()
    print(f"Model loaded: {version['name']} {version['version']}, classes {classes}")

    camera = open_camera(arguments.camera)
    if camera is None:
        raise SystemExit(
            f"""Could not open camera {arguments.camera}.
The built-in is usually 0, so a USB webcam is 1 or 2. Also check that nothing
else is holding it, and that Windows allows desktop apps to use the camera."""
        )

    # Printed together, and printed loudly, because these three are the ones
    # that fail silently. A wrong zoom or pan does not crash and does not look
    # like a settings problem; it looks like a bad model.
    source = "capture_settings.json" if saved else "defaults (no capture_settings.json found)"
    print(f"Framing: zoom {arguments.zoom:.1f}x, pan ({arguments.pan_x:+d},{arguments.pan_y:+d}), from {source}.")
    print("This must match the dataset, or the model sees a framing it was never trained on.")
    print(f"Camera {arguments.camera}, settling {arguments.settle:.2f}s before each capture.")
    print(f"Listening at {arguments.api}. Place an egg on the platform. Ctrl+C to stop.")
    handled = 0
    # Which inspection the gate is currently stuck on, so the warning prints
    # once per egg rather than once per poll.
    dark_inspection = None

    try:
        while True:
            try:
                inspection = find_open_inspection(arguments.api, arguments.key)
            except RuntimeError as error:
                # A backend restart or a dropped connection should not end the
                # session. Say so and keep asking.
                print(f"  api: {error}")
                time.sleep(1.0)
                continue

            if not inspection:
                time.sleep(POLL_SECONDS)
                continue

            inspection_id = inspection["id"]

            # THE GATE. Before the model, never after.
            #
            # Nothing is POSTed when it trips, which means this inspection stays
            # unassessed and /pending hands back the SAME id next time round.
            # The station stops. That is the intended behaviour, not an
            # oversight: a candler that has failed should halt the line rather
            # than let it keep producing confident verdicts in the dark. The
            # database has no fourth result_label for "could not assess"
            # (result_label is ENUM('good','defective','not_an_egg')), and
            # writing 'not_an_egg' instead would be the exact lie that a dark
            # frame is an absent egg.
            # Let the scene stop moving before looking at it. The board already
            # waited for the egg to stop rocking; this waits for the hand that
            # put it there to get out of shot.
            time.sleep(arguments.settle)

            frame, brightness = grab_lit_frame(camera, arguments.zoom, arguments.pan_x, arguments.pan_y)
            if frame is None:
                if dark_inspection != inspection_id:
                    print(f"  inspection {inspection_id}: CANDLER DARK "
                          f"(brightness {brightness:.1f}, needs {BRIGHTNESS_MIN:.0f}).")
                    print("  Nothing will be classified until the light is back. Check that the")
                    print("  candler is switched on, powered, and that the chamber is closed.")
                    dark_inspection = inspection_id
                time.sleep(DARK_HOLD_SECONDS)
                continue
            if dark_inspection is not None:
                print(f"  candler is back (brightness {brightness:.1f}). Resuming.")
                dark_inspection = None

            # Crop first, then save and classify the SAME pixels, so the stored
            # image is exactly what the model saw.
            image_path = save_frame(frame, inspection_id)
            assessment = classify(model, classes, version, frame, image_path)

            try:
                call(f"{arguments.api}/api/inspections/{inspection_id}/assessment",
                     arguments.key, "POST", assessment)
            except RuntimeError as error:
                # The image is already on disk, so nothing is lost, but this
                # inspection stays open and will come back on the next poll.
                print(f"  inspection {inspection_id}: could not report -> {error}")
                time.sleep(1.0)
                continue

            handled += 1
            print(f"inspection {inspection_id}  {assessment['class']:<11} "
                  f"{assessment['confidence']:.2f}  {assessment['inference_time_ms']:>4} ms  {image_path}")
    except KeyboardInterrupt:
        print()
    finally:
        camera.release()

    print(f"Stopped. {handled} egg(s) classified this session.")


if __name__ == "__main__":
    main()
