"""Throwaway stand-in for the three calls in CONTRACT.md section 4.1.

WHAT THIS IS FOR
    It lets the ESP32-S3 be tested end to end -- load cell, LCD, LEDs,
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
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 3001                        # same port the Node backend uses, so the board
                                   # can swap between stub and real without reflashing
                                   # (run one or the other, not both)
DEVICE_KEY = "replace-me"          # must match secrets.h
AUTO_VERDICT_AFTER_S = 1.5         # set to None to disable invented verdicts

_LABELS = ["good", "defective", "not_an_egg"]

_lock = threading.Lock()
_next_id = 1
_inspections = {}                  # id -> {weight_g, created, label, confidence}
_label_cursor = 0

_ASSESS_RE = re.compile(r"^/api/inspections/(\d+)/assessment$")
_RESULT_RE = re.compile(r"^/api/inspections/(\d+)/result$")


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

        self._send(404, {"error": "not found"})

    def do_GET(self):
        if not self._authorised():
            return

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

        self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass   # our own prints are the log; this one is noise


if __name__ == "__main__":
    print(f"stub server on 0.0.0.0:{PORT}  (CONTRACT.md 4.1)")
    print(f"  device key : {DEVICE_KEY}")
    print(f"  auto verdict: {AUTO_VERDICT_AFTER_S}s, cycling {' -> '.join(_LABELS)}")
    print("  nothing is stored. Ctrl+C to stop.\n")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
