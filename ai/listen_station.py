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
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# The SAME centre-crop used when the dataset was shot. Imported rather than
# copied, deliberately: if these two ever disagree, the model trains on one
# framing and infers on another, and nothing about the failure looks like a
# framing problem. See --zoom below.
from capture import crop_to_zoom, open_camera

from station_common import (
    BRIGHTNESS_MIN, CAPTURE_DIR, CAPTURE_SETTLE_SECONDS, DARK_HOLD_SECONDS, DARK_RETRIES, DARK_RETRY_SECONDS,
    DEFAULT_ZOOM, INPUT_SIZE, MODEL_DIR, POLL_SECONDS, STALE_FRAMES_TO_DISCARD,
    call, frame_brightness, grab_current_frame, load_capture_settings, load_model_and_labels,
    preprocess_frame, raw_result_line, setting,
)


def find_open_inspection(base, key):
    """Ask the server whether an inspection is waiting for a verdict.

    THIS IS THE ONE FUNCTION TO CHANGE if the trigger mechanism changes. It
    currently expects GET /api/inspections/pending, which returns the oldest
    inspection that has no assessment yet, or 404 when there is nothing waiting.
    Swapping to a database read or a different endpoint touches only this.
    """
    return call(f"{base}/api/inspections/pending", key)


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
    batch = np.expand_dims(preprocess_frame(frame), 0)

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
        "raw_result": raw_result_line(classes, probabilities),
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
