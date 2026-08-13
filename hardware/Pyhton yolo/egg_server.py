"""EggMinistrator server -- receives one image + one weight reading per POST
from the ESP32-CAM firmware (EggMinistrator_ESP32CAM.ino), classifies the
egg using the SAME EggLocator/EggClassifier already built for the desktop
app (imported directly, not reimplemented), and returns the verdict as
JSON. Every inspection is also logged to the same inspection_log.csv the
desktop app writes to, so results from both sources end up in one history.

This is the piece that makes the desktop app "work with" the IoT hardware:
the ESP32 doesn't run any AI itself (per the project doc's design -- the
model runs on a computer, not the microcontroller), it just captures and
sends. This server is the computer side of that split.

Setup:
    pip install flask
    python egg_server.py

Then point the firmware's SERVER_HOST at the machine running this script's
LAN IP address (not the ESP32's), and SERVER_PORT at 5000 (the default
below).

Test without any ESP32 hardware at all:
    curl -X POST http://localhost:5000/inspect \\
      -F "weight=58.2" -F "image=@some_egg_photo.jpg"
"""

import csv
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, jsonify, request

from egg_inspector_yolo import (
    LOCATOR_MIN_AREA_LOW,
    LOG_PATH,
    EggClassifier,
    EggLocator,
    classify_size,
)

app = Flask(__name__)
locator = EggLocator()
classifier = EggClassifier()


def _log_result(label: str, confidence: float, weight_g, size_class, source: str = "esp32cam") -> None:
    """Appends one row to the same inspection_log.csv the desktop app
    writes to (same column order), so both sources share one history."""
    is_new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "label", "confidence", "weight_g", "size_class", "source"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            label,
            f"{confidence:.3f}",
            f"{weight_g:.2f}" if weight_g is not None else "",
            size_class or "-",
            source,
        ])


@app.route("/inspect", methods=["POST"])
def inspect():
    if "image" not in request.files:
        return jsonify({"error": "missing 'image' field"}), 400

    weight_raw = request.form.get("weight")
    try:
        weight_g = float(weight_raw) if weight_raw not in (None, "") else None
    except ValueError:
        weight_g = None

    file_bytes = np.frombuffer(request.files["image"].read(), dtype=np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "could not decode image"}), 400

    boxes = locator.locate(frame, min_area=LOCATOR_MIN_AREA_LOW)
    if not boxes:
        # Nothing egg-shaped found at all in the frame -- this maps
        # directly onto the doc's "not an egg" verdict rather than forcing
        # a crop-less frame through the classifier.
        label, confidence = "not_egg", 0.0
    else:
        x1, y1, x2, y2 = boxes[0]
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        label, confidence = classifier.classify(crop)

    size_class = classify_size(weight_g) if weight_g is not None else None

    _log_result(label, confidence, weight_g, size_class)

    return jsonify({
        "label": label,
        "confidence": round(float(confidence), 3),
        "weight_g": weight_g,
        "size_class": size_class,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "classifier": "custom-trained" if classifier.using_custom else "heuristic",
    })


if __name__ == "__main__":
    mode = "custom-trained (models/best-cls.pt)" if classifier.using_custom else \
        "heuristic (no training data yet -- train models/best-cls.pt for real accuracy)"
    print(f"Classifier: {mode}")
    print("Listening on http://0.0.0.0:5000 -- point the ESP32 firmware's")
    print("SERVER_HOST at this machine's LAN IP address (not the ESP32's).")
    app.run(host="0.0.0.0", port=5000)
