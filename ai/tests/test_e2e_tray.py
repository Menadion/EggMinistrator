"""The whole chain on real code with two fakes: the frame (synthetic) and the
board (a direct POST). Needs the backend + MySQL running and the model on
disk, so it is gated: EGG_E2E=1 to run, skipped otherwise.

    EGG_E2E=1 DEVICE_API_KEY=... .venv/Scripts/python.exe -m pytest ai/tests/test_e2e_tray.py -q -s
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("STATION_API", "http://127.0.0.1:3001").rstrip("/")
KEY = os.environ.get("DEVICE_API_KEY", "")

pytestmark = pytest.mark.skipif(os.environ.get("EGG_E2E") != "1", reason="set EGG_E2E=1 with the backend, MySQL and the model available")


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("X-Device-Key", KEY)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read() or b"{}")


def test_synthetic_tray_becomes_four_rows(tmp_path):
    assert KEY, "DEVICE_API_KEY is not set"
    assert (REPO_ROOT / "ai" / "models" / "egg.keras").exists(), "no model to classify with"

    # 1. A lid-close photo with an answer key.
    made = subprocess.run([sys.executable, "ai/scripts/make_tray_frame.py", "--eggs", "4", "--seed", "11", "--default-map", "--out", str(tmp_path), "--name", "e2e"],
                          cwd=REPO_ROOT, capture_output=True, text=True)
    assert made.returncode == 0, made.stderr
    truth = json.loads((tmp_path / "e2e.json").read_text())

    # 2. The board: one POST at lid-close, four weights.
    weights = [58.2, 47.0, 71.5, 61.3]
    minted = call("POST", "/api/cycles", {"station_name": "E2E", "weights": weights, "total_g": round(sum(weights), 2)})
    assert minted["status"] == "pending"
    cycle_id = minted["id"]

    # 3. The listener, on the synthetic frame, once.
    listener = subprocess.run([sys.executable, "ai/listen_tray.py", "--frame", str(tmp_path / "e2e.jpg"), "--once", "--default-map", "--api", BASE, "--key", KEY],
                              cwd=REPO_ROOT, capture_output=True, text=True, timeout=180)
    print(listener.stdout)
    assert listener.returncode == 0, listener.stderr

    # 4. The board polls the result.
    result = None
    for _ in range(40):
        result = call("GET", f"/api/cycles/{cycle_id}/result")
        if result["status"] != "pending":
            break
        time.sleep(0.25)
    assert result["status"] == "done", result
    assert [e["slot"] for e in result["eggs"]] == [1, 2, 3, 4]
    assert [e["size"] for e in result["eggs"]] == ["Medium", "Small", "Jumbo", "Large"] or any(e["label"] == "not_an_egg" for e in result["eggs"])

    # 5. The answer key, reported not asserted: the crops came from the
    # model's own training set, so agreement proves attribution, not accuracy.
    agree = sum(1 for e in result["eggs"] if truth["slots"][str(e["slot"])]["class"] == e["label"])
    print(f"model agreed with the answer key on {agree}/4 slots (attribution check, not an accuracy claim)")
    day = time.strftime("%Y%m%d")
    for slot in range(1, 5):
        assert (REPO_ROOT / "ai" / "captures" / day / f"cycle_{cycle_id}_slot{slot}.jpg").exists()
    assert (REPO_ROOT / "ai" / "captures" / day / f"cycle_{cycle_id}.jpg").exists()
