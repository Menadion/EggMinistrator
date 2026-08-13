"""Serial bridge between the ESP32-S3 board (load cell + OLED + LEDs +
buzzer -- see EggMinistrator_ESP32S3.ino) and this desktop app.

The board does NOT handle the camera -- that's a regular webcam plugged
into this computer, which egg_inspector_yolo.py already captures directly.
This bridge only carries two things over USB serial:
    ESP32 -> PC:  a weight reading whenever an egg is placed on the platform
    PC -> ESP32:  the finalized classification, so the board can show it on
                  its own OLED/LEDs/buzzer (FR-15)

Protocol (plain text, one line at a time, 115200 baud):
    ESP32 -> PC:  W:<grams>\\n              e.g. W:58.23
    PC -> ESP32:  R:<label>:<confidence>\\n e.g. R:good:0.83

This is entirely optional -- if no board is connected, or pyserial isn't
installed, the app just doesn't get live weight/physical feedback and
everything else keeps working exactly as before (manual weight entry).
"""

from __future__ import annotations

import threading
import time
from typing import Optional


class ESP32BridgeUnavailable(RuntimeError):
    """Raised when the bridge can't be used: missing pyserial, no port
    found/openable, or similar setup problem."""


class ESP32Bridge:
    """Background-threaded reader/writer for the ESP32-S3's USB serial
    connection. Non-blocking: call `.latest_weight()` any time to get the
    most recent reading (or None if nothing's been received yet), and
    `.send_result(label, confidence)` to push a verdict back to the board."""

    def __init__(self, port: Optional[str] = None, baud: int = 115200, timeout: float = 1.0) -> None:
        self.port = port
        self.baud = baud
        self._serial = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_weight: Optional[float] = None
        self._latest_weight_at: float = 0.0
        self._init_error: Optional[str] = None

        try:
            import serial  # local import: pyserial is an optional dependency
        except ImportError:
            self._init_error = "the 'pyserial' package isn't installed (pip install pyserial)"
            return

        target_port = port or self._autodetect_port(serial)
        if target_port is None:
            self._init_error = "no serial port found -- is the board plugged in?"
            return

        try:
            self._serial = serial.Serial(target_port, baud, timeout=timeout)
        except Exception as e:
            self._init_error = f"couldn't open {target_port}: {e}"
            return

        self.port = target_port
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    @staticmethod
    def _autodetect_port(serial_module) -> Optional[str]:
        """Picks the first serial port whose description looks like a USB
        UART bridge (how most ESP32 boards show up), since there's often
        exactly one such device plugged in. Falls back to the first port
        at all if nothing matches that pattern."""
        try:
            from serial.tools import list_ports
        except ImportError:
            return None
        ports = list(list_ports.comports())
        if not ports:
            return None
        for p in ports:
            desc = (p.description or "").lower()
            if any(tag in desc for tag in ("cp210", "ch340", "usb serial", "usb-serial", "uart")):
                return p.device
        return ports[0].device

    @property
    def available(self) -> bool:
        return self._serial is not None

    @property
    def status(self) -> str:
        if self.available:
            return f"connected on {self.port}"
        return f"unavailable ({self._init_error})"

    def latest_weight(self, max_age_seconds: float = 3.0) -> Optional[float]:
        """Returns the most recent weight reading, or None if there isn't
        one yet or it's gone stale (the egg was probably removed)."""
        with self._lock:
            if self._latest_weight is None:
                return None
            if time.monotonic() - self._latest_weight_at > max_age_seconds:
                return None
            return self._latest_weight

    def send_result(self, label: str, confidence: float) -> None:
        if not self.available:
            raise ESP32BridgeUnavailable(f"ESP32 board isn't connected: {self._init_error}")
        line = f"R:{label}:{confidence:.3f}\n"
        try:
            self._serial.write(line.encode("utf-8"))
        except Exception as e:
            raise ESP32BridgeUnavailable(f"failed writing to {self.port}: {e}") from e

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass

    # -- internal --------------------------------------------------------
    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._serial.readline()
            except Exception:
                break   # port went away (unplugged) -- stop quietly, .available still reports True
                        # until the next send_result()/read fails too; acceptable for a background reader
            if not raw:
                continue
            self._handle_line(raw.decode("utf-8", errors="ignore").strip())

    def _handle_line(self, line: str) -> None:
        weight = parse_weight_line(line)
        if weight is not None:
            with self._lock:
                self._latest_weight = weight
                self._latest_weight_at = time.monotonic()


def parse_weight_line(line: str) -> Optional[float]:
    """Parses a 'W:<grams>' line from the board. Split out as a standalone
    function so it can be unit tested without any real serial hardware."""
    if not line.startswith("W:"):
        return None
    try:
        return float(line[2:].strip())
    except ValueError:
        return None
