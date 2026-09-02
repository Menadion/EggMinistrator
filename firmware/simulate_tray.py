"""Drive the real backend's TRAY routes as if a v2 board and the listener existed.

WHAT THIS IS FOR
    Demonstrating the fan-out when no enclosure, no v2 firmware and no camera
    are wired up. It plays both hardware roles in CONTRACT.md section 4.5:
    the board sending one POST at lid-close, and the laptop listener sending
    one bundle of verdicts. Rows appear in History as it goes -- real rows,
    through the real endpoints, in one real transaction per tray.

WHAT IS REAL AND WHAT IS NOT
    Real     every HTTP call, the sum check, the count/prefix check, the daily
             batch, the sequence numbers, the size grades, the transaction,
             every database write, and everything the dashboard then shows.
    Invented the weights, the classes, the confidences, the image names.

    ⚠️ SAY THIS OUT LOUD BEFORE ANYONE ASKS. "The tray hardware is being built,
    so this stands in for the board and the camera -- everything downstream is
    the real system."

THE FAMILY
    firmware/stub_server.py       fakes the SERVER for a real board.
    firmware/simulate_station.py  fakes board+laptop for the v1 single-egg path.
    firmware/simulate_tray.py     (this) fakes board+listener for the tray path.

RUNNING IT
    py firmware/simulate_tray.py --trays 3
    py firmware/simulate_tray.py --trays 5 --eggs-per-tray 0 --mismatch-rate 0.2 --seed 7

    Standard library only. The device key is read from backend/.env.
"""

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_PATH = Path("backend/.env")

WEIGHT_MEAN = 58.0
WEIGHT_SPREAD = 6.0
WEIGHT_FLOOR = 42.0
WEIGHT_CEILING = 75.0
MISMATCH_OFFSET_G = 10.0     # far outside the ±3 g tolerance, so a mismatch is unambiguous

MODEL_NAME = "candling-classifier"
MODEL_VERSION = "0.3.0+simulated"
SLOT_LABELS = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2"}
POLL_SECONDS = 0.25
POLL_LIMIT = 40


def read_device_key():
    if not ENV_PATH.exists():
        raise SystemExit(f"{ENV_PATH} not found. Run this from the top folder of the repo.")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*DEVICE_API_KEY\s*=\s*(.+?)\s*$", line)
        if match and match.group(1):
            return match.group(1)
    raise SystemExit("DEVICE_API_KEY is empty in backend/.env.")


def call(url, key, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("X-Device-Key", key)
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        raise SystemExit(f"\n{method} {url}\n  HTTP {error.code}: {body}")
    except urllib.error.URLError as error:
        raise SystemExit(f"\nCannot reach {url} -- {error.reason}\nIs the backend running?  cd backend && npm start")


def invent_weight(rng):
    return round(min(max(rng.gauss(WEIGHT_MEAN, WEIGHT_SPREAD), WEIGHT_FLOOR), WEIGHT_CEILING), 2)


def invent_verdict(rng, defect_rate, misload_rate):
    roll = rng.random()
    if roll < misload_rate:
        return "not_an_egg", round(rng.uniform(0.95, 0.99), 2)
    if roll < misload_rate + defect_rate:
        return "defective", round(rng.uniform(0.72, 0.96), 2)
    return "good", round(rng.uniform(0.80, 0.98), 2)


def poll_result(base, key, cycle_id):
    for _ in range(POLL_LIMIT):
        result = call(f"{base}/api/cycles/{cycle_id}/result", key)
        if result.get("status") != "pending":
            return result
        time.sleep(POLL_SECONDS)
    raise SystemExit(f"cycle {cycle_id} never became terminal")


def run_tray(index, base, key, rng, args):
    k = args.eggs_per_tray if args.eggs_per_tray else rng.randint(1, 6)
    weights = [invent_weight(rng) for _ in range(k)]
    total = round(sum(weights), 2)
    mismatch = rng.random() < args.mismatch_rate
    if mismatch:
        total = round(total + MISMATCH_OFFSET_G, 2)

    # --- the board's job: one POST at lid-close --------------------------
    minted = call(f"{base}/api/cycles", key, "POST", {"station_name": "Station 1", "weights": weights, "total_g": total})
    cycle_id = minted["id"]
    print(f"tray {index}  {k} egg(s)  weights {weights}  total {total} g  -> cycle {cycle_id} {minted['status']}")
    if minted["status"] == "rejected":
        result = poll_result(base, key, cycle_id)
        print(f"         board reads: RELOAD TRAY ({result['reason']})  -- no eggs recorded, audit row kept")
        return "rejected", 0

    # --- the listener's job: one bundle ----------------------------------
    pending = call(f"{base}/api/cycles/pending", key)
    assert pending["id"] == cycle_id, f"pending returned cycle {pending['id']}, expected {cycle_id} -- drain old pending cycles first"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    eggs = []
    for slot in range(1, k + 1):
        label, confidence = invent_verdict(rng, args.defect_rate, args.misload_rate)
        emitted = {"image": f"sim_{stamp}_cycle{cycle_id}_slot{slot}.jpg", "class": label, "confidence": confidence,
                   "model_name": MODEL_NAME, "model_version": MODEL_VERSION, "inference_time_ms": rng.randint(30, 60)}
        eggs.append({"slot": slot, "image_path": emitted["image"], "class": label, "confidence": confidence,
                     "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
                     "inference_time_ms": emitted["inference_time_ms"], "raw_result": json.dumps(emitted)})
    call(f"{base}/api/cycles/{cycle_id}/assessment", key, "POST", {"frame_path": f"sim_{stamp}_cycle{cycle_id}.jpg", "eggs": eggs})

    # --- the board polling back, which is what drives the TFT --------------
    result = poll_result(base, key, cycle_id)
    cells = "  ".join(f"{SLOT_LABELS[e['slot']]}:{e['label']}/{e['size'] or '-'}" for e in result["eggs"])
    print(f"         TFT grid: {cells}   buzzer={'ON' if result['any_defective'] else 'off'}")
    return "done", k


def main():
    parser = argparse.ArgumentParser(description="Simulate tray cycles against the real backend.")
    parser.add_argument("--trays", type=int, default=3)
    parser.add_argument("--eggs-per-tray", dest="eggs_per_tray", type=int, default=6, help="1..6, or 0 for a random count per tray")
    parser.add_argument("--mismatch-rate", dest="mismatch_rate", type=float, default=0.0)
    parser.add_argument("--defect-rate", dest="defect_rate", type=float, default=0.25)
    parser.add_argument("--misload-rate", dest="misload_rate", type=float, default=0.05)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--url", default="http://localhost:3001")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--key", default=None, help="Device key; defaults to DEVICE_API_KEY in backend/.env")
    args = parser.parse_args()
    if not 0 <= args.eggs_per_tray <= 6:
        raise SystemExit("--eggs-per-tray must be 0..6")

    base = args.url.rstrip("/")
    key = args.key or read_device_key()
    rng = random.Random(args.seed)

    print("EggMinistrator tray simulator")
    print(f"  target : {base}")
    print("  NOTE   : weights and verdicts are INVENTED. Everything downstream is real.\n")

    done = rejected = eggs = 0
    for index in range(1, args.trays + 1):
        status, count = run_tray(index, base, key, rng, args)
        if status == "done":
            done += 1
            eggs += count
        else:
            rejected += 1
        if index < args.trays:
            time.sleep(args.delay)

    print(f"\n{args.trays} tray(s): {done} done ({eggs} eggs recorded), {rejected} rejected.")
    print("Refresh the dashboard -- the eggs are ordinary rows in History.")


if __name__ == "__main__":
    sys.exit(main())
