"""Drive the real backend as if the station hardware were connected.

WHAT THIS IS FOR
    Demonstrating the pipeline when the load cell and camera are not wired up.
    It plays the two roles the hardware plays in CONTRACT.md section 4.1: the
    board reporting a weight, and the laptop reporting a classification.

    Run it in a terminal next to the dashboard. Rows appear in History as it
    goes -- real rows, through the real endpoints, in the real database.

WHAT IS REAL AND WHAT IS NOT
    Real     every HTTP call, R's endpoints, the device-key check, the size
             grade looked up from the weight band, every database write, and
             everything the dashboard then shows.
    Invented four numbers per egg: the weight, the class, the confidence, and
             the image filename.

    That is the whole boundary. Nothing is faked downstream of the POST, and no
    data is pasted into the database behind the app's back.

    ⚠️ SAY THIS OUT LOUD BEFORE ANYONE ASKS. "The sensing hardware is in
    assembly, so this stands in for the load cell and camera -- everything
    downstream is the real system." Announcing it is normal engineering
    practice. Being caught by it is not.

THE PAIR
    firmware/stub_server.py     fakes the SERVER, so a real board has something
                                to talk to.
    firmware/simulate_station.py (this)  fakes the BOARD AND LAPTOP, so a real
                                server has something to talk to.

RUNNING IT
    py firmware/simulate_station.py --eggs 5

    Standard library only. The device key is read from backend/.env so it
    cannot drift out of step with the server.

    --eggs N        how many to inspect (default 5)
    --delay S       seconds between eggs (default 2.0). Keep this slow enough
                    to narrate; instant is worse for a demo.
    --url U         backend base URL (default http://localhost:3001)
    --seed N        fixed random seed, so a rehearsal and the real run produce
                    the same eggs
    --defect-rate R fraction defective (default 0.25)
    --misload-rate R fraction not_an_egg (default 0.05)
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

# Roughly what a tray of chicken eggs looks like: centred in Medium/Large with
# a tail either side, so the dashboard's size chart has a believable spread
# instead of a flat line.
WEIGHT_MEAN = 58.0
WEIGHT_SPREAD = 6.0
WEIGHT_FLOOR = 42.0
WEIGHT_CEILING = 75.0

MODEL_NAME = "candling-classifier"
MODEL_VERSION = "0.3.0+simulated"


def read_device_key():
    """Pull DEVICE_API_KEY out of backend/.env rather than hardcoding it, so
    this and the server can never disagree about the value."""
    if not ENV_PATH.exists():
        raise SystemExit(
            f"{ENV_PATH} not found. Run this from the top folder of the repo, "
            "and make sure the backend is configured (copy backend/.env.example)."
        )
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*DEVICE_API_KEY\s*=\s*(.+?)\s*$", line)
        if match and match.group(1):
            return match.group(1)
    raise SystemExit(
        "DEVICE_API_KEY is empty in backend/.env. Pick any string, put it there, "
        "and put the same one in firmware/secrets.h."
    )


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
        raise SystemExit(
            f"\nCannot reach {url} -- {error.reason}\n"
            "Is the backend running?  cd backend && npm start"
        )


def invent_weight(rng):
    weight = rng.gauss(WEIGHT_MEAN, WEIGHT_SPREAD)
    return round(min(max(weight, WEIGHT_FLOOR), WEIGHT_CEILING), 2)


def invent_verdict(rng, defect_rate, misload_rate):
    roll = rng.random()
    if roll < misload_rate:
        # A misload is usually unambiguous -- something is plainly not an egg.
        return "not_an_egg", round(rng.uniform(0.95, 0.99), 2)
    if roll < misload_rate + defect_rate:
        return "defective", round(rng.uniform(0.72, 0.96), 2)
    return "good", round(rng.uniform(0.80, 0.98), 2)


def inspect_one(index, base, key, rng, defect_rate, misload_rate):
    weight = invent_weight(rng)

    # --- the board's job -------------------------------------------------
    created = call(f"{base}/api/inspections", key, "POST", {"weight_g": weight})
    inspection_id = created.get("id")
    print(f"egg {index}   weight {weight:>5} g   -> inspection {inspection_id}")

    # --- the laptop's job ------------------------------------------------
    label, confidence = invent_verdict(rng, defect_rate, misload_rate)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    image = f"{label}_sim_{stamp}_{index}.jpg"

    # raw_result must be the classifier's line exactly as emitted -- the server
    # validates that, and section 4.3 says it is stored verbatim. So build the
    # JSON once and send that same string.
    emitted = {
        "image": image,
        "class": label,
        "confidence": confidence,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "inference_time_ms": rng.randint(85, 160),
    }
    payload = dict(emitted)
    payload["raw_result"] = json.dumps(emitted)

    call(f"{base}/api/inspections/{inspection_id}/assessment", key, "POST", payload)

    # --- the board polling back, which is what drives the LCD -------------
    result = call(f"{base}/api/inspections/{inspection_id}/result", key)
    shown = result.get("label", "?")
    note = "  (filtered from the dashboard by decision 8)" if shown == "not_an_egg" else ""
    print(f"         classified {shown} ({result.get('confidence')}){note}")
    return shown


def main():
    parser = argparse.ArgumentParser(description="Simulate the station against the real backend.")
    parser.add_argument("--eggs", type=int, default=5)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--url", default="http://localhost:3001")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--defect-rate", type=float, default=0.25)
    parser.add_argument("--misload-rate", type=float, default=0.05)
    args = parser.parse_args()

    base = args.url.rstrip("/")
    key = read_device_key()
    rng = random.Random(args.seed)

    print("EggMinistrator station simulator")
    print(f"  target : {base}")
    print("  NOTE   : weights and verdicts are INVENTED. Everything downstream is real.\n")

    tally = {}
    for index in range(1, args.eggs + 1):
        label = inspect_one(index, base, key, rng, args.defect_rate, args.misload_rate)
        tally[label] = tally.get(label, 0) + 1
        if index < args.eggs:
            time.sleep(args.delay)

    print(f"\n{args.eggs} inspection(s) created: " + ", ".join(f"{v} {k}" for k, v in sorted(tally.items())))
    print("Refresh the dashboard -- History, Analytics and Reports all update.")
    if tally.get("not_an_egg"):
        print(f"The {tally['not_an_egg']} misload(s) are stored but hidden, which is decision 8 working.")


if __name__ == "__main__":
    sys.exit(main())
