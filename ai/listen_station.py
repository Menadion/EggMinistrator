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
        "raw_result": {name: float(score) for name, score in zip(classes, probabilities)},
    }


def main():
    parser = argparse.ArgumentParser(description="Classify eggs as the board opens inspections.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index. 0 is usually the built-in; try 1 for the USB webcam.")
    parser.add_argument("--zoom", type=float, default=DEFAULT_ZOOM, help="MUST match the zoom the dataset was shot at, e.g. --zoom 1.8. Check a filename in ai/dataset/ for the z-number.")
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

    print(f"Zoom {arguments.zoom:.1f}x. This must match the dataset, or the model sees a framing it was never trained on.")
    print(f"Listening at {arguments.api}. Place an egg on the platform. Ctrl+C to stop.")
    handled = 0

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
            # Crop first, then save and classify the SAME pixels, so the stored
            # image is exactly what the model saw.
            frame = crop_to_zoom(grab_current_frame(camera), arguments.zoom)
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
