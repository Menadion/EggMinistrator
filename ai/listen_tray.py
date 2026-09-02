"""Watch for tray cycles opened by the board, photograph the tray once, crop
it six ways, classify the crops in one go, and report one bundle.

THIS IS THE FAN-OUT (spec docs/superpowers/specs/2026-09-02-software-fanout-design.md).

    board posts k weights at lid-close  ->  server mints a pending cycle
    -> THIS FILE: one frame -> k crops -> k verdicts -> one POST
    -> server mints k egg rows in one transaction -> board polls the result

NOT ai/listen_station.py. That is the v1 single-egg listener J's dataset rig
still uses. Same skeleton (poll, 404-means-sleep, settle, one printed line per
event), different middle. Shared pieces live in ai/station_common.py.

DIVISION OF LABOUR (spec section 4)
    server    checks the arithmetic: the weights add up to the total
    this file checks the optics: which holes are full, and that they are 1..k
    server    mints eggs, only inside the transaction, only if both agreed

THREE OUTCOMES PER CYCLE
    hold      every slot is dark: the candler is off. Nothing is posted; the
              cycle stays pending and is re-picked next poll. A dead lamp
              stalls a loaded tray, it never voids it.
    reject    the picture disagrees with the weights (count, or not a prefix).
              The frame is saved as evidence and the cycle is refused. The
              board shows RELOAD TRAY. No egg rows ever exist.
    assess    crops saved, classified, bundle posted. Six rows are born.

WHAT IT NEEDS
    ai/tray_map.json from ai/scripts/calibrate_tray.py (the six rectangles
    are only valid at the resolution the map was made at), the model trio in
    ai/models/, and DEVICE_API_KEY matching backend/.env.

RUNNING IT
    py ai/listen_tray.py
    py ai/listen_tray.py --frame ai/captures/synthetic/tray_7.jpg --once --default-map
        (the test seam: read a file instead of the camera, handle one cycle, exit)
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from station_common import (
    CAPTURE_DIR, DARK_HOLD_SECONDS, POLL_SECONDS,
    call, grab_current_frame, load_model_and_labels, open_camera, preprocess_frame, raw_result_line,
)
from tray_map import DEFAULT_TRAY_MAP, TRAY_MAP_PATH, TrayMapError, crop_slot, load_tray_map, slot_label
from tray_occupancy import all_dark, check_occupancy, classify_slots, occupied_slots

# The lid just closed. This waits for the chamber to stop vibrating, not for a
# hand -- the hand is outside a closed lid by definition.
LID_SETTLE_SECONDS = 0.3


def find_pending_cycle(base, key):
    """GET /api/cycles/pending -> {id, weights, created_at}, or None on 404."""
    return call(f"{base}/api/cycles/pending", key)


def classify_batch_with(model, classes, version):
    """Build the classifier: a list of crops in, a list of verdicts out, in ONE
    predict() call -- six inferences for roughly the cost of one."""
    def classify_batch(crops):
        batch = np.stack([preprocess_frame(crop) for crop in crops])
        started = time.perf_counter()
        probabilities = model.predict(batch, verbose=0)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return [
            {
                "class": classes[int(scores.argmax())],
                "confidence": float(scores.max()),
                "model_name": version["name"],
                "model_version": version["version"],
                "inference_time_ms": elapsed_ms,
                "raw_result": raw_result_line(classes, scores),
            }
            for scores in probabilities
        ]
    return classify_batch


def save_cycle_images(frame, crops_by_slot, cycle_id, capture_dir=CAPTURE_DIR):
    """Master frame + one crop per slot, under captures/YYYYMMDD/. The master
    frame is the audit ground truth when a per-egg verdict is disputed; the
    crop is what the model saw. Both are written BEFORE classifying, so the
    stored pixels are exactly the classified pixels."""
    day_folder = Path(capture_dir) / datetime.now().strftime("%Y%m%d")
    day_folder.mkdir(parents=True, exist_ok=True)
    frame_path = day_folder / f"cycle_{cycle_id}.jpg"
    cv2.imwrite(str(frame_path), frame)
    crop_paths = {}
    for slot, crop in crops_by_slot.items():
        path = day_folder / f"cycle_{cycle_id}_slot{slot}.jpg"
        cv2.imwrite(str(path), crop)
        crop_paths[slot] = path.as_posix()
    return frame_path.as_posix(), crop_paths


def run_cycle(cycle, frame, tray_map, classify_batch, save_images):
    """The whole decision for one cycle, with the two side effects injected
    (classifier and disk) so this runs in tests with neither TensorFlow nor a
    camera. Returns (outcome, payload)."""
    regimes = classify_slots(frame, tray_map)
    if all_dark(regimes):
        return "hold", {"regimes": regimes}

    weight_count = len(cycle["weights"])
    problem = check_occupancy(regimes, weight_count)
    if problem:
        reason, detail = problem
        frame_path, _ = save_images(frame, {}, cycle["id"])
        return "reject", {"reason": reason, "detail": detail, "occupied_slots": occupied_slots(regimes), "frame_path": frame_path}

    slots = list(range(1, weight_count + 1))
    crops = {slot: crop_slot(frame, tray_map, slot) for slot in slots}
    frame_path, crop_paths = save_images(frame, crops, cycle["id"])
    verdicts = classify_batch([crops[slot] for slot in slots])
    eggs = [{"slot": slot, "image_path": crop_paths[slot], **verdict} for slot, verdict in zip(slots, verdicts)]
    return "assess", {"frame_path": frame_path, "eggs": eggs}


def configure_camera(camera, capture):
    """Ask for the calibrated fourcc and size, then check we got them. Order
    matters on most drivers: the pixel format first, then the resolution --
    a 4K request in raw YUY2 silently falls back to something smaller."""
    fourcc = capture.get("fourcc")
    if fourcc:
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, capture["width"])
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, capture["height"])
    got = (int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)), int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    if got != (capture["width"], capture["height"]):
        raise SystemExit(
            f"Camera gives {got[0]}x{got[1]} but the tray map is calibrated for {capture['width']}x{capture['height']}"
            f" ({fourcc or 'default fourcc'}). Re-run ai/scripts/calibrate_tray.py on this rig."
        )


def main():
    parser = argparse.ArgumentParser(description="Classify a tray of eggs as the board opens cycles.")
    parser.add_argument("--api", default=os.environ.get("STATION_API", "http://127.0.0.1:3001"))
    parser.add_argument("--key", default=os.environ.get("DEVICE_API_KEY", ""))
    parser.add_argument("--map", default=str(TRAY_MAP_PATH), help="calibrated tray map (ai/scripts/calibrate_tray.py)")
    parser.add_argument("--default-map", dest="default_map", action="store_true", help="use the built-in synthetic geometry (tests only)")
    parser.add_argument("--frame", default=None, help="read this image instead of the camera (the test seam)")
    parser.add_argument("--once", action="store_true", help="handle one cycle, then exit (exit code 2 if it had to hold on a dark frame)")
    parser.add_argument("--settle", type=float, default=LID_SETTLE_SECONDS)
    parser.add_argument("--camera", type=int, default=None, help="camera index; defaults to the tray map's")
    arguments = parser.parse_args()

    if not arguments.key:
        raise SystemExit("No device key. Set DEVICE_API_KEY or pass --key (must match backend/.env).")
    try:
        tray_map = DEFAULT_TRAY_MAP if arguments.default_map else load_tray_map(arguments.map)
    except TrayMapError as error:
        raise SystemExit(str(error))

    model, classes, version = load_model_and_labels()
    classify_batch = classify_batch_with(model, classes, version)
    print(f"Model loaded: {version['name']} {version['version']}, classes {classes}")

    capture = tray_map["capture"]
    if arguments.frame:
        still = cv2.imread(arguments.frame)
        if still is None:
            raise SystemExit(f"Could not read {arguments.frame}")
        grab = lambda: still.copy()   # noqa: E731
        camera = None
        print(f"Frame source: {arguments.frame} (no camera).")
    else:
        index = arguments.camera if arguments.camera is not None else capture.get("camera", 0)
        camera = open_camera(index)
        if camera is None:
            raise SystemExit(f"Could not open camera {index}.")
        configure_camera(camera, capture)
        grab = lambda: grab_current_frame(camera)   # noqa: E731
        print(f"Camera {index} at {capture['width']}x{capture['height']} {capture.get('fourcc', '')}.")

    print(f"Tray map: {'built-in default' if arguments.default_map else arguments.map}. Six slots, labels A1..C2.")
    print(f"Listening at {arguments.api}. Close the lid. Ctrl+C to stop.")
    handled = 0
    dark_cycle = None
    exit_code = 0

    try:
        while True:
            try:
                cycle = find_pending_cycle(arguments.api, arguments.key)
            except RuntimeError as error:
                print(f"  api: {error}")
                time.sleep(1.0)
                continue
            if not cycle:
                time.sleep(POLL_SECONDS)
                continue

            time.sleep(arguments.settle)
            try:
                frame = grab()
                outcome, payload = run_cycle(cycle, frame, tray_map, classify_batch, save_cycle_images)
            except TrayMapError as error:
                raise SystemExit(str(error))

            if outcome == "hold":
                if dark_cycle != cycle["id"]:
                    print(f"  cycle {cycle['id']}: CANDLER DARK on every slot. Nothing will be classified until the light is back.")
                    dark_cycle = cycle["id"]
                if arguments.once:
                    exit_code = 2
                    break
                time.sleep(DARK_HOLD_SECONDS)
                continue
            if dark_cycle is not None:
                print("  candler is back. Resuming.")
                dark_cycle = None

            try:
                if outcome == "reject":
                    call(f"{arguments.api}/api/cycles/{cycle['id']}/reject", arguments.key, "POST", payload)
                    print(f"cycle {cycle['id']}  REJECTED  {payload['reason']}: {payload['detail']}  {payload['frame_path']}")
                else:
                    call(f"{arguments.api}/api/cycles/{cycle['id']}/assessment", arguments.key, "POST", payload)
                    print(f"cycle {cycle['id']}  {len(payload['eggs'])} egg(s)  {payload['frame_path']}")
                    for egg in payload["eggs"]:
                        print(f"    {slot_label(egg['slot'])}  {egg['class']:<11} {egg['confidence']:.2f}  {egg['inference_time_ms']:>4} ms  {egg['image_path']}")
            except RuntimeError as error:
                # Images are on disk; the cycle stays pending and comes back next poll.
                print(f"  cycle {cycle['id']}: could not report -> {error}")
                time.sleep(1.0)
                continue

            handled += 1
            if arguments.once:
                break
    except KeyboardInterrupt:
        print()
    finally:
        if camera is not None:
            camera.release()

    print(f"Stopped. {handled} cycle(s) handled this session.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
