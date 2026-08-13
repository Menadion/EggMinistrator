"""Optional cloud-based egg quality detector, using the community-trained
Roboflow object-detection model "egg-quality-grading-wlgy5/1".

This is an *alternative* to the local OpenCV-locator + YOLO-classifier
pipeline in egg_inspector_yolo.py -- useful before you've collected enough
of your own candling photos to train models/best-cls.pt: the Roboflow
model was already trained on someone else's egg-quality dataset, so it
gives you a working quality check today, in exchange for needing an
internet connection (and Roboflow's usage limits/pricing) instead of
running fully offline.

Setup:
    pip install inference-sdk
    export ROBOFLOW_API_KEY="your-key-here"      # never commit this value

Standalone usage (run inference on one image from the command line):
    python roboflow_classifier.py path/to/egg.jpg
    python roboflow_classifier.py https://example.com/egg.jpg
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple, Union

import numpy as np

MODEL_ID = "egg-quality-grading-wlgy5/1"
API_URL = "https://serverless.roboflow.com"
API_KEY_ENV_VAR = "ROBOFLOW_API_KEY"  # set this in your shell/.env -- never hardcode the key

# Matches the (x1, y1, x2, y2, label, confidence) shape egg_inspector_yolo.py
# already uses for a single-shot image analysis (see EggInspectorYOLO.analyze_frame),
# so results from either backend can be rendered/logged the same way.
Detection = Tuple[int, int, int, int, str, float]


class RoboflowUnavailable(RuntimeError):
    """Raised when the cloud classifier can't be used: missing SDK, missing
    API key, or the API request itself failed (network, auth, rate limit)."""


class RoboflowEggClassifier:
    """Thin wrapper around Roboflow's hosted serverless inference API for
    the 'egg-quality-grading-wlgy5/1' object-detection model.

    Because this model both finds *and* grades each egg in one cloud call,
    it can stand in for the app's whole EggLocator + EggClassifier pair --
    but only for single still images (the "Open Image" flow). It is
    deliberately NOT wired into the live webcam loop, which samples several
    times a second; doing that here would mean a network round trip per
    frame, which is slow, rate-limit-unfriendly, and would rack up
    Roboflow usage fast.
    """

    def __init__(self, api_key: str | None = None, model_id: str = MODEL_ID, api_url: str = API_URL) -> None:
        self.model_id = model_id
        self.api_url = api_url
        self.api_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        self._client = None
        self._init_error: str | None = None

        if not self.api_key:
            self._init_error = f"{API_KEY_ENV_VAR} is not set"
            return
        try:
            from inference_sdk import InferenceHTTPClient
        except ImportError:
            self._init_error = "the 'inference-sdk' package isn't installed (pip install inference-sdk)"
            return
        self._client = InferenceHTTPClient(api_url=self.api_url, api_key=self.api_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def status(self) -> str:
        return "ready" if self.available else f"unavailable ({self._init_error})"

    def detect(self, image: Union[str, Path, np.ndarray]) -> List[Detection]:
        """Runs the cloud model on a file path, an image URL, or an
        in-memory BGR (OpenCV-style) frame, and returns detections in the
        (x1, y1, x2, y2, label, confidence) shape the rest of the app uses."""
        if not self.available:
            raise RoboflowUnavailable(
                f"Roboflow isn't configured: {self._init_error}."
            )

        tmp_path: Path | None = None
        try:
            if isinstance(image, np.ndarray):
                import cv2  # local import: only needed for this in-memory-frame path
                fd, tmp_name = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                tmp_path = Path(tmp_name)
                cv2.imwrite(str(tmp_path), image)
                target = str(tmp_path)
            else:
                target = str(image)

            try:
                result = self._client.infer(target, model_id=self.model_id)
            except Exception as e:
                raise RoboflowUnavailable(f"Roboflow inference request failed: {e}") from e
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

        # infer() returns one dict for a single image, or a list of dicts if
        # given a list of images -- normalize to a single dict either way.
        if isinstance(result, list):
            result = result[0] if result else {}

        detections: List[Detection] = []
        for pred in result.get("predictions", []):
            try:
                cx, cy = float(pred["x"]), float(pred["y"])
                w, h = float(pred["width"]), float(pred["height"])
                label = str(pred.get("class", "unknown"))
                conf = float(pred.get("confidence", 0.0))
            except (KeyError, TypeError, ValueError):
                continue  # skip any malformed prediction rather than fail the whole batch
            x1, y1 = int(cx - w / 2), int(cy - h / 2)
            x2, y2 = int(cx + w / 2), int(cy + h / 2)
            detections.append((x1, y1, x2, y2, label, conf))
        return detections


if __name__ == "__main__":
    import json

    if len(sys.argv) != 2:
        print("Usage: python roboflow_classifier.py <path-to-image-or-url>")
        raise SystemExit(1)

    classifier = RoboflowEggClassifier()
    if not classifier.available:
        print(f"Can't run: {classifier.status}.")
        print(f"Set {API_KEY_ENV_VAR} in your environment and `pip install inference-sdk`, then retry.")
        raise SystemExit(1)

    try:
        found = classifier.detect(sys.argv[1])
    except RoboflowUnavailable as e:
        print(f"Inference failed: {e}")
        raise SystemExit(1)

    print(json.dumps(
        [{"box_xyxy": [x1, y1, x2, y2], "label": label, "confidence": round(conf, 4)}
         for x1, y1, x2, y2, label, conf in found],
        indent=2,
    ))
    print(f"\n{len(found)} egg(s) detected.")
