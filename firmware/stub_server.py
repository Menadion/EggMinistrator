"""Throwaway stand-in for CONTRACT.md sections 4.1 (single egg) and 4.5 (tray cycle).

WHAT THIS IS FOR
    It lets the ESP32 be tested end to end -- load cell, LCD, LEDs,
    buzzer -- before the real backend has any of these routes. Flash the
    sketch, run this, put something on the platform, and watch the station
    react.

WHAT THIS IS NOT
    It is not the backend and it is not a preview of the backend. It says
    nothing about whether R's implementation is correct, because it is not
    R's implementation. What it tests is THE BOARD AGAINST THE SPEC. If this
    stub and the real backend both satisfy section 4.1, the firmware cannot
    tell them apart -- and if the real one differs, the firmware will fail
    against it, which is the signal you want rather than a surprise later.

    Nothing is stored. Everything lives in memory and dies with the process.
    Do not point the dashboard at this. Do not deploy it anywhere.

RUNNING IT
    python firmware/stub_server.py

    Standard library only -- no pip install, no Flask. Then set SERVER_HOST
    in your secrets.h to this machine's LAN IP (ipconfig -> IPv4 Address),
    and SERVER_PORT to 3001 -- the same port the real backend uses, so you can
    stop the stub and start the real thing without reflashing the board.

    Both machines must be on the same Wi-Fi. If the board cannot reach it,
    the usual cause is Windows Firewall blocking inbound python.exe -- allow
    it on private networks, or test with the firewall off briefly.

HOW THE VERDICT APPEARS
    There is no classifier here. AUTO_VERDICT_AFTER_S seconds after a weight
    arrives, the stub invents one, cycling good -> defective -> not_an_egg so
    that all three LED and buzzer paths get exercised without you having to
    stage a real defective egg.

    The real assessment route is implemented too, so if the laptop side is
    running it can post a genuine verdict and that wins over the invented one.
"""

import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("STUB_PORT", "3001"))   # same port the Node backend uses by default, so the board
                                                  # can swap between stub and real without reflashing
                                                  # (run one or the other, not both). STUB_PORT for tests.
DEVICE_KEY = "replace-me"          # must match secrets.h
# 🔴 TURN THIS OFF BEFORE RUNNING ai/listen_station.py AGAINST THIS STUB:
#
#     set STUB_AUTO_VERDICT=off  &&  py firmware/stub_server.py
#
# Left on, it races the real classifier and usually wins, so the board shows a
# verdict, everything looks like it worked, and the model was never consulted.
# That is exactly how the 2026-08-23 "end to end" run passed without the AI.
#
# Read from the environment rather than edited in place, because a hand-edited
# constant is a constant somebody forgets to change back.
AUTO_VERDICT_AFTER_S = None if os.environ.get("STUB_AUTO_VERDICT", "").lower() in {"off", "0", "false", "none"} else 1.5

_LABELS = ["good", "defective", "not_an_egg"]

_lock = threading.Lock()
_next_id = 1
_inspections = {}                  # id -> {weight_g, created, label, confidence}
_label_cursor = 0

_ASSESS_RE = re.compile(r"^/api/inspections/(\d+)/assessment$")
_RESULT_RE = re.compile(r"^/api/inspections/(\d+)/result$")

# ---- v2 tray cycle (CONTRACT.md section 4.5) -------------------------------
# Same idea as the v1 routes: THE BOARD AGAINST THE SPEC, in memory, nothing
# stored. A real v2 board can be bench-tested against these before (or without)
# the Node backend. The size bands are the PNS ones so the result grid the TFT
# draws looks like the real thing.
_cycles = {}                        # id -> dict(status, station_name, weights, total_g, frame_path, rejected_reason, eggs)
_next_cycle_id = 1
_CYCLE_ASSESS_RE = re.compile(r"^/api/cycles/(\d+)/assessment$")
_CYCLE_REJECT_RE = re.compile(r"^/api/cycles/(\d+)/reject$")
_CYCLE_RESULT_RE = re.compile(r"^/api/cycles/(\d+)/result$")
_SUM_TOLERANCE_G = 3.0
_DISPOSITION = {"good": "accepted", "defective": "rejected", "not_an_egg": "no_egg"}
_REJECT_REASONS = {"occupancy_mismatch", "not_prefix"}


def _size_label(grams):
    """PNS/BAFS 321:2021 bands, matching database/sample-data.sql."""
    if grams < 45.0:
        return "Pewee"
    if grams < 55.0:
        return "Small"
    if grams < 60.0:
        return "Medium"
    if grams < 65.0:
        return "Large"
    if grams < 70.0:
        return "Extra Large"
    return "Jumbo"


def _auto_cycle_verdict(cycle_id):
    """Invent a verdict per slot a moment later, unless the listener beat us to it."""
    global _label_cursor
    time.sleep(AUTO_VERDICT_AFTER_S)
    with _lock:
        cycle = _cycles.get(cycle_id)
        if cycle is None or cycle["status"] != "pending":
            return
        cycle["eggs"] = []
        for slot, grams in enumerate(cycle["weights"], start=1):
            label = _LABELS[_label_cursor % len(_LABELS)]
            _label_cursor += 1
            cycle["eggs"].append({"slot": slot, "label": label, "disposition": _DISPOSITION[label],
                                  "size": None if label == "not_an_egg" else _size_label(grams)})
        cycle["status"] = "done"
        print(f"  [auto] cycle {cycle_id} -> {[e['label'] for e in cycle['eggs']]}")


def _auto_verdict(inspection_id):
    """Invent a verdict a moment later, unless a real one arrived first."""
    global _label_cursor
    time.sleep(AUTO_VERDICT_AFTER_S)
    with _lock:
        row = _inspections.get(inspection_id)
        if row is None or row.get("label") is not None:
            return                 # gone, or the laptop beat us to it
        row["label"] = _LABELS[_label_cursor % len(_LABELS)]
        row["confidence"] = 0.83
        _label_cursor += 1
        print(f"  [auto] id={inspection_id} -> {row['label']}")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorised(self):
        if self.headers.get("X-Device-Key") == DEVICE_KEY:
            return True
        # Loud on purpose: a mismatched key is otherwise a silent 401 that
        # looks exactly like a wiring problem from the board's side.
        print(f"  !! rejected: X-Device-Key was {self.headers.get('X-Device-Key')!r}, "
              f"expected {DEVICE_KEY!r} -- check secrets.h")
        self._send(401, {"error": "bad or missing X-Device-Key"})
        return False

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_POST(self):
        global _next_id
        if not self._authorised():
            return

        # Step 1 -- the board sends weight, we mint the row and hand back its id.
        if self.path == "/api/inspections":
            weight = self._body().get("weight_g")
            with _lock:
                inspection_id = _next_id
                _next_id += 1
                _inspections[inspection_id] = {
                    "weight_g": weight,
                    "created": time.time(),
                    "label": None,
                    "confidence": None,
                }
            print(f"POST /api/inspections  weight={weight} -> id={inspection_id}")
            if AUTO_VERDICT_AFTER_S is not None:
                threading.Thread(target=_auto_verdict, args=(inspection_id,),
                                 daemon=True).start()
            return self._send(201, {"id": inspection_id})

        # Step 2 -- the laptop posts the real classifier output.
        match = _ASSESS_RE.match(self.path)
        if match:
            inspection_id = int(match.group(1))
            payload = self._body()
            with _lock:
                row = _inspections.get(inspection_id)
                if row is None:
                    return self._send(404, {"error": "no such inspection"})
                row["label"] = payload.get("class")
                row["confidence"] = payload.get("confidence")
            print(f"POST assessment id={inspection_id} -> {payload.get('class')} "
                  f"({payload.get('confidence')})")
            return self._send(201, {"ok": True})

        # ---- v2: lid-close mints a cycle ---------------------------------
        if self.path == "/api/cycles":
            global _next_cycle_id
            body = self._body()
            weights = body.get("weights")
            if not isinstance(weights, list) or not 1 <= len(weights) <= 6 or not all(isinstance(w, (int, float)) and 0 < w <= 1000 for w in weights):
                return self._send(400, {"error": "weights must hold 1..6 grams in slot order", "code": "WEIGHTS_REQUIRED"})
            try:
                total = float(body.get("total_g"))
            except (TypeError, ValueError):
                return self._send(400, {"error": "total_g must be a number", "code": "INVALID_TOTAL"})
            mismatch = abs(sum(weights) - total) > _SUM_TOLERANCE_G
            with _lock:
                cycle_id = _next_cycle_id
                _next_cycle_id += 1
                _cycles[cycle_id] = {
                    "status": "rejected" if mismatch else "pending",
                    "station_name": body.get("station_name") or "Station 1",
                    "weights": [round(float(w), 2) for w in weights],
                    "total_g": total,
                    "frame_path": None,
                    "rejected_reason": "weights_sum_mismatch" if mismatch else None,
                    "eggs": [],
                }
            print(f"POST /api/cycles  weights={weights} total={total} -> id={cycle_id} {'REJECTED (sum)' if mismatch else 'pending'}")
            if not mismatch and AUTO_VERDICT_AFTER_S is not None:
                threading.Thread(target=_auto_cycle_verdict, args=(cycle_id,), daemon=True).start()
            return self._send(201, {"id": cycle_id, "status": _cycles[cycle_id]["status"]})

        # ---- v2: the listener's bundle -----------------------------------
        match = _CYCLE_ASSESS_RE.match(self.path)
        if match:
            cycle_id = int(match.group(1))
            body = self._body()
            eggs = body.get("eggs")
            with _lock:
                cycle = _cycles.get(cycle_id)
                if cycle is None:
                    return self._send(404, {"error": "no such cycle", "code": "CYCLE_NOT_FOUND"})
                if cycle["status"] != "pending":
                    return self._send(409, {"error": f"cycle is already {cycle['status']}", "code": "CYCLE_NOT_PENDING"})
                if not isinstance(eggs, list) or len(eggs) != len(cycle["weights"]):
                    return self._send(400, {"error": "eggs count must equal weights count", "code": "EGG_COUNT_MISMATCH"})
                slots = sorted(int(e.get("slot", 0)) for e in eggs)
                if slots != list(range(1, len(cycle["weights"]) + 1)):
                    return self._send(400, {"error": "slots must be exactly 1..k", "code": "SLOTS_NOT_PREFIX"})
                if any(e.get("class") not in _DISPOSITION for e in eggs):
                    return self._send(400, {"error": "class must be good, defective, or not_an_egg", "code": "INVALID_RESULT_LABEL"})
                cycle["eggs"] = []
                for e in sorted(eggs, key=lambda item: int(item["slot"])):
                    slot = int(e["slot"])
                    label = e["class"]
                    cycle["eggs"].append({"slot": slot, "label": label, "disposition": _DISPOSITION[label],
                                          "size": None if label == "not_an_egg" else _size_label(cycle["weights"][slot - 1])})
                cycle["frame_path"] = body.get("frame_path")
                cycle["status"] = "done"
            print(f"POST cycle assessment id={cycle_id} -> {[e['label'] for e in cycle['eggs']]}")
            return self._send(201, {"id": cycle_id, "status": "done", "inspections": [{"slot": e["slot"], "id": cycle_id * 10 + e["slot"]} for e in cycle["eggs"]]})

        # ---- v2: the listener's refusal ----------------------------------
        match = _CYCLE_REJECT_RE.match(self.path)
        if match:
            cycle_id = int(match.group(1))
            body = self._body()
            reason = body.get("reason")
            if reason not in _REJECT_REASONS:
                return self._send(400, {"error": "reason must be occupancy_mismatch or not_prefix", "code": "INVALID_REJECT_REASON"})
            with _lock:
                cycle = _cycles.get(cycle_id)
                if cycle is None:
                    return self._send(404, {"error": "no such cycle", "code": "CYCLE_NOT_FOUND"})
                if cycle["status"] != "pending":
                    return self._send(409, {"error": f"cycle is already {cycle['status']}", "code": "CYCLE_NOT_PENDING"})
                cycle["status"] = "rejected"
                cycle["rejected_reason"] = reason
                cycle["frame_path"] = body.get("frame_path") or cycle["frame_path"]
            print(f"POST cycle reject id={cycle_id} -> {reason}: {body.get('detail', '')}")
            return self._send(200, {"id": cycle_id, "status": "rejected", "reason": reason})

        self._send(404, {"error": "not found"})

    def do_GET(self):
        if not self._authorised():
            return

        # Step 2 -- the laptop's listener asks whether an egg is waiting for a
        # verdict. Mirrors the real backend's GET /api/inspections/pending so the
        # whole board -> listener -> model -> board loop can be exercised without
        # MySQL or R's backend running.
        #
        # 404 when nothing waits, deliberately: listen_station.py reads 404 as
        # "no egg right now" and sleeps.
        if self.path == "/api/inspections/pending":
            with _lock:
                waiting = [(key, row) for key, row in sorted(_inspections.items())
                           if row["label"] is None]
            if not waiting:
                return self._send(404, {"error": "nothing waiting"})
            inspection_id, row = waiting[0]
            print(f"GET /api/inspections/pending -> id={inspection_id}")
            return self._send(200, {"id": inspection_id, "weight_g": row["weight_g"]})

        # Step 3 -- the board polls until a verdict exists.
        match = _RESULT_RE.match(self.path)
        if match:
            inspection_id = int(match.group(1))
            with _lock:
                row = _inspections.get(inspection_id)
            if row is None:
                return self._send(404, {"error": "no such inspection"})
            if row["label"] is None:
                return self._send(200, {"status": "pending"})
            return self._send(200, {
                "label": row["label"],
                "confidence": row["confidence"],
            })

        # ---- v2: the listener asks for the oldest pending tray ------------
        if self.path == "/api/cycles/pending":
            with _lock:
                waiting = [(key, row) for key, row in sorted(_cycles.items()) if row["status"] == "pending"]
            if not waiting:
                return self._send(404, {"error": "No cycle is waiting.", "code": "NO_PENDING_CYCLE"})
            cycle_id, cycle = waiting[0]
            print(f"GET /api/cycles/pending -> id={cycle_id}")
            return self._send(200, {"id": cycle_id, "weights": cycle["weights"], "created_at": None})

        # ---- v2: the board polls until terminal ---------------------------
        match = _CYCLE_RESULT_RE.match(self.path)
        if match:
            cycle_id = int(match.group(1))
            with _lock:
                cycle = _cycles.get(cycle_id)
                if cycle is None:
                    return self._send(404, {"error": "no such cycle", "code": "CYCLE_NOT_FOUND"})
                if cycle["status"] == "pending":
                    return self._send(200, {"status": "pending"})
                if cycle["status"] == "rejected":
                    return self._send(200, {"status": "rejected", "reason": cycle["rejected_reason"]})
                return self._send(200, {"status": "done", "eggs": list(cycle["eggs"]),
                                        "any_defective": any(e["label"] == "defective" for e in cycle["eggs"])})

        self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass   # our own prints are the log; this one is noise


if __name__ == "__main__":
    print(f"stub server on 0.0.0.0:{PORT}  (CONTRACT.md 4.1 and 4.5)")
    print(f"  device key : {DEVICE_KEY}")
    print(f"  auto verdict: {AUTO_VERDICT_AFTER_S}s, cycling {' -> '.join(_LABELS)}")
    print("  nothing is stored. Ctrl+C to stop.\n")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
