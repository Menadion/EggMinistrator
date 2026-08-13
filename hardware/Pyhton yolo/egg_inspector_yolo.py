"""YOLO-based Egg Quality Inspector (single laptop app).

Architecture (this is the accuracy-focused redesign):
  - Finding the egg in frame uses plain OpenCV contour analysis
    (EggLocator) -- no model, no download, deterministic. A detection
    model was overkill for "find one round blob"; classic computer
    vision is faster and just as reliable for that specific job.
  - Judging quality uses a YOLOv8 *classification* model (EggClassifier,
    models/best-cls.pt) run only on the cropped, candled egg region.
    Classifiers need far less training data than detectors and are the
    right tool when there's exactly one subject per crop -- which is
    exactly this setup. Falls back to a brightness heuristic before
    you've trained a model.

Detect -> wait for candling -> candle -> count workflow, plus:
  - Manual override of the AI's result, with operator name recorded.
  - Manual weight entry -> automatic PNS size classification.
  - A visible, scrollable session history.
  - Automatic snapshot collection: every finalized egg's candled crop
    is saved into dataset/collected/<label>/ -- this IS the training
    set for train_yolo.py. Correct wrong guesses with Override before
    moving to the next egg and the saved labels stay accurate without
    any separate labeling tool.
  - One-click session report export.
  - Audible confirmation when an egg is counted.
  - Automatic sync of every result to the web dashboard (if running).

See README.md for the full data-collection -> training workflow.

Dependencies: ultralytics, opencv-python, numpy, Pillow, requests
Run:      python egg_inspector_yolo.py
Package:  pyinstaller --noconfirm --onefile egg_inspector_yolo.py
"""

import csv
import json
import sys
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import cv2
    import numpy as np
    import requests
    from PIL import Image, ImageTk
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    import customtkinter as ctk
    from ultralytics import YOLO
except Exception as e:  # a broken/outdated dependency should never look like a silent crash
    print("=" * 72)
    print("Egg Inspector couldn't start: a required package failed to import.")
    print(f"\n  {type(e).__name__}: {e}\n")
    _msg = str(e)
    if "distutils" in _msg:
        print("This means an OLD 'customtkinter' is installed that doesn't support")
        print("your Python version (Python 3.12+ removed the 'distutils' module it")
        print("relies on). Fix it with:\n")
        print("    pip install --upgrade customtkinter\n")
    elif "tkinter" in _msg or "_tkinter" in _msg:
        print("Python's Tk support isn't installed. On Linux/WSL, install it with:\n")
        print("    sudo apt install python3-tk\n")
        print("(On Windows/macOS, reinstalling Python from python.org normally")
        print("includes this automatically.)\n")
    else:
        print("Try reinstalling this project's dependencies with:\n")
        print("    pip install -r requirements.txt\n")
    print("=" * 72)
    sys.exit(1)

try:
    from roboflow_classifier import RoboflowEggClassifier, RoboflowUnavailable
except ImportError:
    RoboflowEggClassifier = None    # roboflow_classifier.py missing entirely -- feature just stays off
    RoboflowUnavailable = Exception

try:
    from esp32_bridge import ESP32Bridge, ESP32BridgeUnavailable
except ImportError:
    ESP32Bridge = None    # esp32_bridge.py missing entirely -- feature just stays off
    ESP32BridgeUnavailable = Exception

ctk.set_appearance_mode("dark")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH_CUSTOM = BASE_DIR / "models" / "best-cls.pt"   # your trained quality classifier
LOG_PATH = BASE_DIR / "inspection_log.csv"
SNAPSHOT_DIR = BASE_DIR / "dataset" / "collected"
REPORTS_DIR = BASE_DIR / "reports"

INFERENCE_INTERVAL = 0.15

BASELINE_SAMPLE_COUNT = 4
CANDLING_BRIGHTNESS_DELTA_DEFAULT = 30

CANDLING_SECONDS = 2.5
MIN_CANDLING_SAMPLES = 3

# --- Offline heuristic classifier (used before you've trained a real model,
# and whenever the Roboflow cloud model isn't configured) --------------------
# These are starting points, not calibrated against any particular camera or
# lighting setup -- if it's consistently over/under-flagging, nudge the
# matching threshold. Higher threshold = harder to trigger.
# Class taxonomy matches the project doc (Scope / Technical Architecture):
# the model returns exactly ONE verdict per egg -- "good", "defective", or
# "not an egg" -- and does not report which specific defect was found. So
# unlike an earlier version of this file, cracks/damage and blood/meat spots
# are no longer separate classes -- either signal firing just means
# "defective". Surface dirt is explicitly out of scope per the doc -- eggs
# are cleaned upstream of this station -- so it plays no part here either.
HEURISTIC_SPOT_BRIGHTNESS = 90        # below this average brightness -> leans "defective"
HEURISTIC_CRACK_SCORE = 40            # longest straight edge segment (pixels) above this -> leans "defective"
HEURISTIC_STAIN_SCORE = 3             # patch-to-patch color variation above this -> leans "defective"

# After an egg finishes and is counted, ignore any new detection near that
# same spot for this long. Without this, a brief tracking hiccup (very
# possible with a busy background or a low candling-brightness threshold)
# can make the app think the same physical egg is a brand-new one and count
# it again -- this is what causes the same egg to be logged repeatedly.
RECOUNT_COOLDOWN_SECONDS = 5.0

MATCH_DISTANCE_PX = 130
TRACK_TIMEOUT_SECONDS = 3.0

# Egg-locator strictness range (contour minimum area in pixels^2). Mapped
# from the "Detection strictness" slider (0.1-0.9): higher = requires a
# bigger blob = fewer, more confident boxes.
LOCATOR_MIN_AREA_LOW = 200
LOCATOR_MIN_AREA_HIGH = 3200
STRICTNESS_DEFAULT = 0.35

HISTORY_MAX_ROWS = 200
# The 3 quality classes are the project's own output classes (see comment
# above). "not_egg" isn't a quality class -- it's a practical Override
# option for correcting a false-positive detection (the locator boxed
# something that wasn't an egg at all), kept separate from the 3 for that
# reason.
DEFAULT_CLASS_CHOICES = ["good", "defective", "not_egg"]
MAX_CAMERA_PROBE = 5  # how many device indices to check when listing cameras


def list_cameras() -> list[int]:
    """Probes device indices 0..MAX_CAMERA_PROBE-1 and returns the ones that
    actually open, so external/USB cameras show up alongside the built-in
    one. Brief flicker while probing is normal -- each candidate camera is
    opened just long enough to confirm it responds, then released."""
    available = []
    for idx in range(MAX_CAMERA_PROBE):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(idx)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                available.append(idx)
        cap.release()
    return available or [0]

# PNS egg size classes by weight in grams (see Table 10 in the project doc).
def classify_size(weight_g: float) -> str:
    if weight_g < 45:
        return "Peewee"
    if weight_g < 55:
        return "Small"
    if weight_g < 60:
        return "Medium"
    if weight_g < 65:
        return "Large"
    if weight_g < 70:
        return "Extra Large"
    return "Jumbo"

# --- Web dashboard sync ------------------------------------------------------
WEB_API_BASE = "http://localhost:5000/api"
DEVICE_API_KEY = "eggministrator-local-key"   # must match backend/app.py's EGGMINISTRATOR_DEVICE_KEY
PENDING_SYNC_PATH = BASE_DIR / "pending_sync.jsonl"
SYNC_RETRY_INTERVAL_MS = 20000

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"          # falls back gracefully via tkinter's font matching
BG = "#121317"
BG_2 = "#0c0d10"                  # sits behind the video, darkest surface in the app
PANEL_BG = "#1b1d22"
PANEL_BG_2 = "#23262c"
PANEL_BG_3 = "#2a2e35"            # hover / raised elements
BORDER = "#2c2f36"
BORDER_SOFT = "#22252b"
TEXT = "#eef0f3"
MUTED = "#8d94a0"
ACCENT = "#33d6a6"
ACCENT_HOVER = "#28c197"
ACCENT_SOFT = "#1c3830"           # accent tinted onto a dark surface, for subtle highlights
ACCENT_DARK = "#08110d"           # text color placed on top of the accent color
DANGER = "#e8555a"

CLASS_COLORS_BGR = {
    "good": (94, 201, 74),
    "defective": (66, 63, 232),
    "not_egg": (150, 150, 150),
}
DEFAULT_COLOR_BGR = (180, 180, 180)
WAITING_COLOR_BGR = (222, 158, 74)
CANDLING_COLOR_BGR = (210, 200, 40)

CLASS_COLORS_HEX = {
    "good": "#4ac95e",
    "defective": "#e83f42",
    "not_egg": "#8d94a0",
}
DEFAULT_COLOR_HEX = "#9aa1ab"
WAITING_COLOR_HEX = "#4a9ede"
CANDLING_COLOR_HEX = "#28c8d2"


def color_bgr_for(label: str) -> tuple[int, int, int]:
    return CLASS_COLORS_BGR.get(label.lower(), DEFAULT_COLOR_BGR)


def color_hex_for(label: str) -> str:
    return CLASS_COLORS_HEX.get(label.lower(), DEFAULT_COLOR_HEX)


def region_brightness(frame: np.ndarray, box: tuple[int, int, int, int]) -> float:
    x1, y1, x2, y2 = box
    roi = frame[max(0, y1):y2, max(0, x1):x2]
    if roi.size == 0:
        return 0.0
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def beep() -> None:
    try:
        import winsound
        winsound.Beep(880, 120)
    except Exception:
        try:
            import sys
            print("\a", end="", file=sys.stderr)
        except Exception:
            pass


@dataclass
class Track:
    center: tuple[int, int]
    box: tuple[int, int, int, int]
    first_seen: float
    last_seen: float
    state: str = "waiting"          # "waiting" -> "candling" -> "done"
    baseline_samples: list[float] = field(default_factory=list)
    baseline_brightness: Optional[float] = None
    last_brightness: float = 0.0
    candling_started: Optional[float] = None
    samples: list[tuple[str, float]] = field(default_factory=list)
    final_label: str = ""
    final_conf: float = 0.0
    counted: bool = False
    weight_g: Optional[float] = None
    size_class: str = "-"
    tree_item: Optional[str] = None
    snapshot_path: Optional[Path] = None


class EggLocator:
    """Finds egg-shaped blobs in a frame using classic contour analysis.
    No model, no download, no training required. Tries both bright-on-dark
    and dark-on-bright segmentation since candled eggs can be either
    brighter (light shining through) or darker than background depending
    on your setup, and merges the results.

    Shape verification is deliberately strict: solidity (real eggs are
    convex; limbs/torsos/hands mostly aren't), an ellipse-fit residual
    (a real egg silhouette closely matches a fitted ellipse; irregular
    blobs don't, even under noisy segmentation), and a rotation-invariant
    axis ratio from that fitted ellipse (eggs are only mildly elongated).
    Honest limitation: this can't distinguish an egg from any other
    round/oval convex object (a ball, a face, a fist) -- only a trained
    classifier that has actually seen non-egg examples can do that. See
    the "not_egg" class support in the app for that."""

    def _boxes_for_polarity(self, gray: np.ndarray, invert: bool, min_area: int, max_area: float) -> list[tuple[int, int, int, int]]:
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        flag = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
        _, thresh = cv2.threshold(blurred, 0, 255, flag + cv2.THRESH_OTSU)
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            if w < 30 or h < 30:
                continue
            if len(c) < 5:  # cv2.fitEllipse requires at least 5 points
                continue

            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            if hull_area == 0:
                continue
            solidity = area / hull_area
            if solidity < 0.90:
                continue

            (_, _), (MA, ma), _ = cv2.fitEllipse(c)
            ellipse_area = np.pi * (MA / 2) * (ma / 2)
            if ellipse_area == 0:
                continue
            fit_ratio = area / ellipse_area
            if not (0.82 <= fit_ratio <= 1.12):
                continue

            axis_ratio = max(MA, ma) / max(min(MA, ma), 1.0)
            if not (1.0 <= axis_ratio <= 1.55):
                continue

            boxes.append((x, y, x + w, y + h))
        return boxes

    @staticmethod
    def _iou(a, b) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / float(area_a + area_b - inter)

    def locate(self, frame: np.ndarray, min_area: int) -> list[tuple[int, int, int, int]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_area = gray.shape[0] * gray.shape[1]
        max_area = frame_area * 0.45
        candidates = self._boxes_for_polarity(gray, invert=True, min_area=min_area, max_area=max_area) + \
            self._boxes_for_polarity(gray, invert=False, min_area=min_area, max_area=max_area)

        merged: list[tuple[int, int, int, int]] = []
        for box in candidates:
            if all(self._iou(box, m) < 0.4 for m in merged):
                merged.append(box)
        return merged


class EggClassifier:
    """Wraps a trained YOLOv8 classification model over a cropped egg
    region. Falls back to a rule-based, multi-signal heuristic (see
    _heuristic_classify) before you've trained a real model."""

    def __init__(self) -> None:
        self.using_custom = MODEL_PATH_CUSTOM.exists()
        if self.using_custom:
            self.model = YOLO(str(MODEL_PATH_CUSTOM))
            self.names = self.model.names
        else:
            self.model = None
            self.names = None

    def classify(self, crop: np.ndarray) -> tuple[str, float]:
        if crop.size == 0:
            return "good", 0.0
        if self.using_custom:
            result = self.model.predict(crop, verbose=False)[0]
            top1 = int(result.probs.top1)
            conf = float(result.probs.top1conf)
            label = self.names.get(top1, str(top1))
            return label, conf
        return self._heuristic_classify(crop)

    def _heuristic_classify(self, crop: np.ndarray) -> tuple[str, float]:
        """A rule-based fallback, NOT a trained AI model -- it's a small set
        of classic computer-vision measurements on the cropped egg. The
        project doc's model returns exactly one verdict per egg -- good or
        defective (never both, never a defect breakdown) -- so this checks
        the same signals as before but collapses them into that single
        binary call:

          - crack_score (longest straight edge segment): a crack or a piece
            of gross shell damage reads as one long, thin, fairly straight
            line cutting across the crop. Looking for straight line segments
            (via a Hough transform) targets that specific shape, rather than
            just "any sharp edge anywhere" -- which would also fire on a
            color blotch's boundary and confuse the two.
          - stain_score (patch-to-patch color spread): a blood or meat spot
            shows up as a localized patch of different color against an
            otherwise evenly-lit candled egg, so color varies more from one
            small patch of the crop to another than a clean egg's does.
          - brightness: overall light transmission through the shell/
            contents during candling. A spot large or dense enough to
            visibly block light lowers this in addition to (or instead of)
            showing a clear color difference, so it's treated as a second,
            weaker signal toward "defective".

        This can never produce "not an egg" -- it has no way to tell an
        actual egg apart from any other roughly oval object the locator
        boxed, that distinction can only come from a model trained on real
        photos of both. This will also never be as accurate as a model
        trained on your own photos more generally -- it can't learn what
        YOUR eggs, camera, and lighting actually look like, and it has no
        way to tell a real blood spot from a shadow or a smudge on the
        lens. See README section 4 for training a real model once you have
        data; that will beat this heuristic, and is the only way to get a
        trustworthy accuracy figure for the doc's success criteria."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Mask out the crop's four corners with an inscribed ellipse before
        # measuring anything. A rectangular bounding box around an oval egg
        # always leaves background showing in its four corners -- that's
        # geometry, not cropping error -- and that corner-vs-egg contrast is
        # bigger than almost any real defect, so left unmasked it swamps
        # every signal below and reads as "defective" on a perfectly good
        # egg. Restricting analysis to roughly the egg's own silhouette
        # avoids that.
        h, w = crop.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(mask, (w // 2, h // 2), (int(w * 0.42), int(h * 0.42)), 0, 0, 360, 255, -1)
        mask_bool = mask > 0

        if mask_bool.sum() < 16:  # crop too tiny for the mask to mean anything
            mask_bool = np.ones((h, w), dtype=bool)

        brightness = float(gray[mask_bool].mean())

        masked_gray = np.where(mask_bool, gray, 0).astype(np.uint8)
        edges = cv2.Canny(masked_gray, 50, 150)
        min_len = max(15, min(h, w) // 4)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=20,
                                 minLineLength=min_len, maxLineGap=4)
        crack_score = 0.0
        if lines is not None:
            crack_score = max(
                float(np.hypot(x2 - x1, y2 - y1)) for (x1, y1, x2, y2) in lines[:, 0]
            )

        gh, gw = max(1, h // 4), max(1, w // 4)
        patch_means = []
        for y in range(0, h - gh + 1, gh):
            for x in range(0, w - gw + 1, gw):
                patch_mask = mask_bool[y:y + gh, x:x + gw]
                if patch_mask.sum() < patch_mask.size * 0.6:
                    continue  # patch is mostly outside the egg silhouette -- skip it
                patch_means.append(crop[y:y + gh, x:x + gw][patch_mask].reshape(-1, 3).mean(axis=0))
        stain_score = float(np.std(patch_means, axis=0).mean()) if len(patch_means) > 1 else 0.0

        # Any signal crossing its threshold makes the call "defective" --
        # which one doesn't matter, since the doc's model never reports
        # that anyway. Strength is whichever signal is furthest past its
        # threshold, just to give a somewhat meaningful confidence value.
        crack_strength = (crack_score - HEURISTIC_CRACK_SCORE) / HEURISTIC_CRACK_SCORE
        stain_strength = (stain_score - HEURISTIC_STAIN_SCORE) / HEURISTIC_STAIN_SCORE
        dark_strength = (HEURISTIC_SPOT_BRIGHTNESS - brightness) / HEURISTIC_SPOT_BRIGHTNESS
        defect_strength = max(crack_strength, stain_strength, dark_strength)

        if defect_strength > 0:
            label = "defective"
            strength = defect_strength
        else:
            label = "good"
            strength = (brightness - HEURISTIC_SPOT_BRIGHTNESS) / HEURISTIC_SPOT_BRIGHTNESS

        conf = 0.55 + min(1.0, strength) * (0.35 if label != "good" else 0.3)
        return label, float(min(0.92, conf))


class EggInspectorYOLO:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Egg Inspector — YOLO")
        self._fit_window_to_screen()
        self.root.configure(fg_color=BG)

        self._init_style()

        self.status = tk.StringVar(value="Loading model...")
        self.model_info = tk.StringVar(value="Classifier: loading...")
        self.strictness_var = tk.DoubleVar(value=STRICTNESS_DEFAULT)
        self.strictness_readout = tk.StringVar()
        self.candling_delta_var = tk.DoubleVar(value=CANDLING_BRIGHTNESS_DELTA_DEFAULT)
        self.candling_delta_readout = tk.StringVar()
        self.operator_var = tk.StringVar(value="Inspector")
        self.weight_var = tk.StringVar(value="")
        self.size_readout = tk.StringVar(value="Size: -")
        self.autosave_var = tk.BooleanVar(value=True)
        self.override_var = tk.StringVar(value="")
        self.web_sync_var = tk.BooleanVar(value=True)
        self.web_sync_status = tk.StringVar(value="Dashboard: not checked yet")
        self.roboflow = None
        self.roboflow_status = tk.StringVar(value="Roboflow cloud: not checked yet")
        self.esp32 = None
        self.esp32_status = tk.StringVar(value="ESP32 board: not checked yet")
        self.esp32_autoweight_var = tk.BooleanVar(value=True)
        self.camera_var = tk.StringVar(value="Camera 0")
        self.available_cameras = [0]

        self.capture = None
        self.running = False
        self.last_inference = 0.0
        self.tracks: list[Track] = []
        self.recent_finalized: list[tuple[tuple[int, int], float]] = []
        self.latest: list[tuple[int, int, int, int, str, float]] = []
        self.total = 0
        self.per_class: dict[str, int] = {}
        self.last_track: Optional[Track] = None

        self._build_ui()
        self._refresh_counts()
        self.weight_var.trace_add("write", lambda *_: self._on_weight_change())
        self.root.after(100, self._load_model)
        self.root.after(400, self._refresh_cameras)
        self.root.after(1500, self._flush_pending_sync)

    def _fit_window_to_screen(self) -> None:
        """Size the window relative to the user's actual screen, then start
        maximized. A hardcoded pixel size (the old '1300x880') looks tiny on
        a large/high-DPI monitor and can run off-screen entirely on a small
        laptop display -- this scales to whatever screen it's opened on, and
        the window stays freely resizable afterward if you don't want it
        maximized."""
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        win_w = min(1300, int(screen_w * 0.92))
        win_h = min(880, int(screen_h * 0.88))
        self._window_w = win_w
        x = max(0, (screen_w - win_w) // 2)
        y = max(0, (screen_h - win_h) // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.minsize(min(1020, screen_w - 40), min(720, screen_h - 80))

        try:
            if sys.platform.startswith("win"):
                self.root.state("zoomed")
            else:
                # '-zoomed' is the X11/Linux and (best-effort) macOS equivalent of Windows' 'zoomed' state.
                self.root.attributes("-zoomed", True)
        except tk.TclError:
            pass  # window manager doesn't support it -- the geometry set above is still a sane fallback

    # -- theming ------------------------------------------------------------
    def _init_style(self) -> None:
        """CustomTkinter widgets (buttons, sliders, switches, entries, tabs,
        cards) draw their own rounded, modern chrome and don't go through
        ttk.Style at all. The one native ttk widget we keep is Treeview --
        CustomTkinter has no table widget -- so this only needs to style
        that, plus its scrollbar."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Treeview", background=PANEL_BG_2, fieldbackground=PANEL_BG_2, foreground=TEXT,
                         borderwidth=0, rowheight=27, font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background=PANEL_BG, foreground=MUTED, borderwidth=0,
                         relief="flat", font=(FONT_FAMILY, 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", ACCENT)])
        style.map("Treeview.Heading", background=[("active", PANEL_BG)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Vertical.TScrollbar", background=PANEL_BG_2, troughcolor=PANEL_BG,
                         arrowsize=12, borderwidth=0, relief="flat")

    # -- UI construction ------------------------------------------------------
    def _card(self, parent, **pack_opts) -> ctk.CTkFrame:
        """A real rounded, bordered panel -- used consistently for every
        section so the app reads as a set of distinct cards rather than one
        dense form. Returns an inner padded frame ready for children."""
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=PANEL_BG,
                             border_width=1, border_color=BORDER)
        card.pack(**pack_opts)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        return inner

    def _pill(self, parent, textvariable=None, text=None) -> ctk.CTkLabel:
        pill = ctk.CTkLabel(parent, text=text or (textvariable.get() if textvariable else ""),
                             font=(FONT_FAMILY, 11), text_color=MUTED, fg_color=PANEL_BG_2,
                             corner_radius=8, height=26)
        pill.pack_configure(ipadx=4)
        if textvariable is not None:
            self._bind_live_text(pill, textvariable)
        return pill

    def _bind_live_text(self, widget, var: tk.Variable) -> None:
        """CTk widgets don't reliably support Tk's textvariable= the way
        classic tk/ttk widgets do, so dynamic labels (status line, model
        info, live readouts) are kept in sync with their StringVars by
        hand via a trace instead."""
        def _update(*_args) -> None:
            widget.configure(text=var.get())
        var.trace_add("write", _update)
        _update()

    def _auto_wrap(self, label: ctk.CTkLabel) -> None:
        """Keeps a multi-line label's wrap width matched to its container's
        actual width, instead of a single hardcoded guess -- a fixed number
        is inevitably wrong on either a very small window (text overflows
        its container) or a very large one (text wraps too early).

        Binds to the *parent's* resize, not the label's own: binding to the
        label's own <Configure> creates a feedback loop, since changing
        wraplength changes the label's size, which re-fires <Configure>,
        forever. The parent's width isn't affected by this label's content,
        so it's stable to key off of. A minimum-change threshold avoids
        reacting to sub-pixel layout noise."""
        parent = label.master
        state = {"last_w": -1}

        def _apply(*_args) -> None:
            new_w = max(80, parent.winfo_width() - 24)
            if abs(new_w - state["last_w"]) < 4:
                return
            state["last_w"] = new_w
            label.configure(wraplength=new_w)

        parent.bind("<Configure>", _apply, add="+")
        label.after(50, _apply)

    def _build_ui(self) -> None:
        outer = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # -- Header: identity on the left, live status pills on the right --
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill=tk.X)
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side=tk.LEFT)
        ctk.CTkLabel(title_box, text="\U0001F95A  Egg Inspector", text_color=TEXT,
                     font=(FONT_FAMILY, 21, "bold")).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Point a camera at an egg, and I'll do the rest.",
                     text_color=MUTED, font=(FONT_FAMILY, 12)).pack(anchor="w", pady=(2, 0))

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.pack(side=tk.RIGHT, anchor="e")
        self._pill(header_right, textvariable=self.model_info).pack(anchor="e", pady=(0, 6))
        self._pill(header_right, textvariable=self.web_sync_status).pack(anchor="e")

        ctk.CTkFrame(outer, fg_color=BORDER, height=1, width=10).pack(fill=tk.X, pady=(16, 16))

        def _toolbar_button(parent, text, command, *, accent=False, danger=False, width=110):
            fg = ACCENT if accent else PANEL_BG_2
            hover = ACCENT_HOVER if accent else PANEL_BG_3
            fg_text = ACCENT_DARK if accent else (DANGER if danger else TEXT)
            weight = "bold" if accent else "normal"
            ctk.CTkButton(parent, text=text, corner_radius=8, height=36, width=width, fg_color=fg,
                          hover_color=hover, text_color=fg_text, font=(FONT_FAMILY, 12, weight),
                          command=command).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        # -- Main split: live view (left) + tabbed sidebar (right) --
        main = ctk.CTkFrame(outer, fg_color="transparent")
        main.pack(fill=tk.BOTH, expand=True)

        left = ctk.CTkFrame(main, fg_color="transparent")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Computed once, up front, so both the toolbar buttons and the
        # camera frame below can be sized off the same real number instead
        # of guessing.
        sidebar_w = max(300, min(370, int(self._window_w * 0.30)))
        left_w = max(480, self._window_w - 40 - sidebar_w - 18)

        # -- Toolbar: lives INSIDE the left column, above the camera frame,
        # so its total width always matches the camera frame's width below
        # it instead of spanning the whole app window. Each button gets an
        # explicit width computed from the actual available space -- plain
        # fill=X/expand=True only ADDS extra space when there's room to
        # spare, it never shrinks a button below its natural text width, so
        # seven full-label buttons would still silently overflow a narrow
        # screen without this.
        toolbar = ctk.CTkFrame(left, fg_color="transparent")
        toolbar.pack(fill=tk.X, pady=(0, 12))
        btn_w = max(70, (left_w - 6 * 8) // 7)
        _toolbar_button(toolbar, "\U0001F4F7 Webcam", self.start_camera, accent=True, width=btn_w)
        _toolbar_button(toolbar, "\u23F9 Stop", self.stop_camera, width=btn_w)
        _toolbar_button(toolbar, "\U0001F4C2 Open", self.open_image, width=btn_w)
        _toolbar_button(toolbar, "\u2601 Cloud", self.open_image_cloud, width=btn_w)
        _toolbar_button(toolbar, "\U0001F4C4 Export", self.export_report, width=btn_w)
        _toolbar_button(toolbar, "\u21BB Reload", self._load_model, width=btn_w)
        _toolbar_button(toolbar, "\u21BA Reset", self.reset_counts, danger=True, width=btn_w)

        # -- Camera frame: sized to fill the space naturally available on
        # first layout (so it can never push the override/status section
        # below it off the bottom of the window), then locked to that exact
        # size so it stays put afterward -- it won't grow, shrink, or
        # reflow if you resize the window later, which is steadier to line
        # a real camera rig up against than a frame that keeps changing.
        video_outer = ctk.CTkFrame(left, corner_radius=14, fg_color=PANEL_BG,
                                    border_width=1, border_color=BORDER)
        video_outer.pack(fill=tk.BOTH, expand=True)
        self._video_outer = video_outer
        video_card = ctk.CTkFrame(video_outer, fg_color="transparent")
        video_card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        self.preview = tk.Label(
            video_card, bg=BG_2, fg=MUTED,
            text="\U0001F95A\n\nReady when you are.\nClick \u201CStart Webcam\u201D or \u201COpen Image\u201D to begin.",
            font=(FONT_FAMILY, 13), justify=tk.CENTER,
        )
        self.preview.pack(expand=True, fill=tk.BOTH)

        legend = ctk.CTkFrame(left, fg_color="transparent")
        legend.pack(fill=tk.X, pady=(12, 0))
        self._legend_dot(legend, WAITING_COLOR_HEX, "Detected, waiting for candling")
        self._legend_dot(legend, CANDLING_COLOR_HEX, "Candling — sampling quality")
        self._legend_dot(legend, CLASS_COLORS_HEX["good"], "Result: good")
        self._legend_dot(legend, CLASS_COLORS_HEX["defective"], "Result: defective")

        self.badges_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.badges_frame.pack(fill=tk.X, pady=(12, 0))

        bottom_card = self._card(left, fill=tk.X, pady=(12, 0))
        override_row = ctk.CTkFrame(bottom_card, fg_color="transparent")
        override_row.pack(fill=tk.X)
        ctk.CTkLabel(override_row, text="Override last result:", text_color=TEXT,
                     font=(FONT_FAMILY, 11)).pack(side=tk.LEFT, padx=(0, 10))
        self.override_combo = ctk.CTkOptionMenu(
            override_row, variable=self.override_var, values=DEFAULT_CLASS_CHOICES, width=140,
            corner_radius=8, fg_color=PANEL_BG_2, button_color=PANEL_BG_3, button_hover_color=BORDER,
            dropdown_fg_color=PANEL_BG_2, text_color=TEXT, font=(FONT_FAMILY, 11),
        )
        self.override_combo.pack(side=tk.LEFT, padx=(0, 10))
        ctk.CTkButton(override_row, text="Apply Override", corner_radius=8, height=30,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_DARK,
                      font=(FONT_FAMILY, 11, "bold"), command=self.apply_override).pack(side=tk.LEFT)
        ctk.CTkFrame(bottom_card, fg_color=BORDER, height=1, width=10).pack(fill=tk.X, pady=12)
        status_label = ctk.CTkLabel(bottom_card, text="", text_color=TEXT, font=(FONT_FAMILY, 11),
                                     justify=tk.LEFT, anchor="w")
        status_label.pack(fill=tk.X)
        self._bind_live_text(status_label, self.status)
        self._auto_wrap(status_label)
        ctk.CTkLabel(
            bottom_card, text_color=MUTED, font=(FONT_FAMILY, 9), anchor="w",
            text=(f"Flow: detect (contour) \u2192 wait for candling \u2192 candle for {CANDLING_SECONDS:.1f}s "
                  f"\u2192 counted once.  Log: {LOG_PATH.name}"),
        ).pack(anchor="w", pady=(8, 0))

        # The video frame is intentionally left flexible (fill=BOTH,
        # expand=True) for now -- it gets locked to a fixed size in
        # _lock_video_size, but only after the window has actually finished
        # maximizing. That request (state('zoomed') in _fit_window_to_screen)
        # is handled asynchronously by the OS/window manager -- measuring
        # and locking a size here, synchronously, would capture the
        # *pre*-maximize window size and leave the real, larger, maximized
        # window with dead space below a too-small camera view.
        self.root.after(120, self._lock_video_size)

        # -- Right: tabbed sidebar (History / Settings) so controls used --
        # -- occasionally don't compete for space with the live view -----
        # Scales with the window instead of a fixed 370px, which left too
        # little room for the video view on a narrower laptop screen.
        sidebar_w = max(300, min(370, int(self._window_w * 0.30)))
        right = ctk.CTkFrame(main, fg_color="transparent", width=sidebar_w)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(18, 0))
        right.pack_propagate(False)

        tabview = ctk.CTkTabview(
            right, corner_radius=14, fg_color=PANEL_BG, border_width=1, border_color=BORDER,
            segmented_button_fg_color=PANEL_BG_2, segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=PANEL_BG_2, segmented_button_unselected_hover_color=PANEL_BG_3,
            text_color=ACCENT_DARK, segmented_button_font=(FONT_FAMILY, 11, "bold"),
        )
        tabview.pack(fill=tk.BOTH, expand=True)
        tabview.add("\U0001F4CB  History")
        tabview.add("\u2699  Settings")

        self._build_history_tab(tabview.tab("\U0001F4CB  History"))
        self._build_settings_tab(tabview.tab("\u2699  Settings"))

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._on_strictness_change(None)
        self._on_delta_change(None)

    def _lock_video_size(self) -> None:
        """Waits for the window to reach its real, final size before
        freezing the camera view's size there. The maximize request from
        _fit_window_to_screen is handled asynchronously by the OS, so the
        window can still be mid-resize for a while after _build_ui returns;
        locking a size immediately would capture the pre-maximize window
        and leave the real, larger window with dead space below a
        too-small camera view.

        Debounces off real <Configure> (resize) events instead of guessing
        a fixed delay: every resize restarts a short countdown, and the
        size is only frozen once resizing has actually stopped for a beat.
        A hard cap guarantees the camera view still becomes stable/usable
        even if something keeps the window resizing indefinitely."""
        video_outer = self._video_outer
        state = {"timer": None, "started": time.monotonic()}

        def _freeze() -> None:
            self.root.unbind("<Configure>", bind_id)
            self.root.update_idletasks()
            w, h = video_outer.winfo_width(), video_outer.winfo_height()
            if w <= 1 or h <= 1:
                w, h = max(w, 480), max(h, 400)
            h = max(220, h)
            video_outer.configure(width=w, height=h)
            video_outer.pack_propagate(False)
            video_outer.pack_configure(fill=tk.X, expand=False)

        def _schedule_freeze(_event=None) -> None:
            if state["timer"] is not None:
                self.root.after_cancel(state["timer"])
            if time.monotonic() - state["started"] > 3.0:
                _freeze()  # safety cap -- don't wait forever
                return
            state["timer"] = self.root.after(220, _freeze)

        bind_id = self.root.bind("<Configure>", _schedule_freeze, add="+")
        _schedule_freeze()  # arms the initial timer even if no more resizes happen at all

    def _build_history_tab(self, parent) -> None:
        tree_frame = tk.Frame(parent, bg=PANEL_BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(8, 4))
        columns = ("time", "result", "conf", "size", "source")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        for col, label, w in (("time", "Time", 62), ("result", "Result", 56), ("conf", "Conf", 38),
                               ("size", "Size", 50), ("source", "Source", 52)):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

    def _settings_section(self, parent, title: str) -> ctk.CTkFrame:
        ctk.CTkLabel(parent, text=title.upper(), text_color=MUTED,
                     font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(0, 8))
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill=tk.X, pady=(0, 20))
        return section

    def _build_settings_tab(self, parent) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Session
        session = self._settings_section(scroll, "Session")
        row = ctk.CTkFrame(session, fg_color="transparent")
        row.pack(fill=tk.X, pady=(0, 10))
        ctk.CTkLabel(row, text="Operator", text_color=TEXT, font=(FONT_FAMILY, 11), width=80,
                     anchor="w").pack(side=tk.LEFT)
        ctk.CTkEntry(row, textvariable=self.operator_var, corner_radius=8, fg_color=PANEL_BG_2,
                     border_width=0, text_color=TEXT).pack(side=tk.LEFT, fill=tk.X, expand=True)
        row2 = ctk.CTkFrame(session, fg_color="transparent")
        row2.pack(fill=tk.X)
        ctk.CTkLabel(row2, text="Weight (g)", text_color=TEXT, font=(FONT_FAMILY, 11), width=80,
                     anchor="w").pack(side=tk.LEFT)
        ctk.CTkEntry(row2, textvariable=self.weight_var, width=70, corner_radius=8, fg_color=PANEL_BG_2,
                     border_width=0, text_color=TEXT).pack(side=tk.LEFT, padx=(0, 10))
        size_label = ctk.CTkLabel(row2, text="", text_color=MUTED, font=(FONT_FAMILY, 11))
        size_label.pack(side=tk.LEFT)
        self._bind_live_text(size_label, self.size_readout)
        weight_hint = ctk.CTkLabel(session, text_color=MUTED, font=(FONT_FAMILY, 9), justify=tk.LEFT,
                     text="Weight is read the moment a result is finalized \u2014 enter it any time "
                          "before the candling window ends.")
        weight_hint.pack(anchor="w", fill=tk.X, pady=(8, 0))
        self._auto_wrap(weight_hint)

        # Camera
        camera = self._settings_section(scroll, "Camera")
        cam_row = ctk.CTkFrame(camera, fg_color="transparent")
        cam_row.pack(fill=tk.X)
        self.camera_combo = ctk.CTkOptionMenu(
            cam_row, variable=self.camera_var, values=["Camera 0"], corner_radius=8,
            fg_color=PANEL_BG_2, button_color=PANEL_BG_3, button_hover_color=BORDER,
            dropdown_fg_color=PANEL_BG_2, text_color=TEXT, font=(FONT_FAMILY, 11),
            command=self._on_camera_change,
        )
        self.camera_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ctk.CTkButton(cam_row, text="\U0001F504", width=36, corner_radius=8, fg_color=PANEL_BG_2,
                      hover_color=PANEL_BG_3, text_color=TEXT,
                      command=self._refresh_cameras).pack(side=tk.LEFT)

        # Detection tuning
        tuning = self._settings_section(scroll, "Detection tuning")
        strict_box = ctk.CTkFrame(tuning, fg_color="transparent")
        strict_box.pack(fill=tk.X, pady=(0, 14))
        head = ctk.CTkFrame(strict_box, fg_color="transparent")
        head.pack(fill=tk.X)
        ctk.CTkLabel(head, text="Detection strictness", text_color=TEXT,
                     font=(FONT_FAMILY, 11)).pack(side=tk.LEFT)
        strictness_label = ctk.CTkLabel(head, text="", text_color=MUTED, font=(FONT_FAMILY, 11))
        strictness_label.pack(side=tk.RIGHT)
        self._bind_live_text(strictness_label, self.strictness_readout)
        ctk.CTkSlider(strict_box, from_=0.1, to=0.9, variable=self.strictness_var, height=16,
                      progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                      fg_color=PANEL_BG_2, command=self._on_strictness_change).pack(fill=tk.X, pady=(6, 0))

        delta_box = ctk.CTkFrame(tuning, fg_color="transparent")
        delta_box.pack(fill=tk.X)
        head2 = ctk.CTkFrame(delta_box, fg_color="transparent")
        head2.pack(fill=tk.X)
        ctk.CTkLabel(head2, text="Candling brightness \u0394", text_color=TEXT,
                     font=(FONT_FAMILY, 11)).pack(side=tk.LEFT)
        delta_label = ctk.CTkLabel(head2, text="", text_color=MUTED, font=(FONT_FAMILY, 11))
        delta_label.pack(side=tk.RIGHT)
        self._bind_live_text(delta_label, self.candling_delta_readout)
        ctk.CTkSlider(delta_box, from_=15, to=80, variable=self.candling_delta_var, height=16,
                      progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                      fg_color=PANEL_BG_2, command=self._on_delta_change).pack(fill=tk.X, pady=(6, 0))

        # Data & sync
        data = self._settings_section(scroll, "Data & Sync")
        ctk.CTkSwitch(data, text="Auto-save training snapshots", variable=self.autosave_var,
                      progress_color=ACCENT, button_color=TEXT, text_color=TEXT,
                      font=(FONT_FAMILY, 11)).pack(anchor="w", pady=(0, 10))
        ctk.CTkSwitch(data, text="Sync to web dashboard", variable=self.web_sync_var,
                      progress_color=ACCENT, button_color=TEXT, text_color=TEXT,
                      font=(FONT_FAMILY, 11)).pack(anchor="w", pady=(0, 12))
        roboflow_label = ctk.CTkLabel(data, text="", text_color=MUTED, font=(FONT_FAMILY, 9),
                                       justify=tk.LEFT, anchor="w")
        roboflow_label.pack(anchor="w", fill=tk.X)
        self._bind_live_text(roboflow_label, self.roboflow_status)
        self._auto_wrap(roboflow_label)

        # ESP32 board (load cell / OLED / LEDs / buzzer -- not the camera,
        # that's the webcam this app already captures directly)
        esp32_section = self._settings_section(scroll, "ESP32 Board")
        ctk.CTkSwitch(esp32_section, text="Use live weight from the board", variable=self.esp32_autoweight_var,
                      progress_color=ACCENT, button_color=TEXT, text_color=TEXT,
                      font=(FONT_FAMILY, 11)).pack(anchor="w", pady=(0, 10))
        esp32_label = ctk.CTkLabel(esp32_section, text="", text_color=MUTED, font=(FONT_FAMILY, 9),
                                    justify=tk.LEFT, anchor="w")
        esp32_label.pack(anchor="w", fill=tk.X)
        self._bind_live_text(esp32_label, self.esp32_status)
        self._auto_wrap(esp32_label)

    def _legend_dot(self, parent, hex_color: str, text: str) -> None:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side=tk.LEFT, padx=(0, 18))
        ctk.CTkLabel(box, text="\u25CF", text_color=hex_color, font=(FONT_FAMILY, 12)).pack(side=tk.LEFT)
        ctk.CTkLabel(box, text=text, text_color=MUTED, font=(FONT_FAMILY, 10)).pack(side=tk.LEFT, padx=(4, 0))

    def _on_strictness_change(self, _value=None) -> None:
        self.strictness_readout.set(f"{self.strictness_var.get():.2f}")

    def _on_delta_change(self, _value=None) -> None:
        self.candling_delta_readout.set(f"{self.candling_delta_var.get():.0f}")

    def _on_weight_change(self) -> None:
        raw = self.weight_var.get().strip()
        try:
            w = float(raw)
            self.size_readout.set(f"Size: {classify_size(w)}")
        except ValueError:
            self.size_readout.set("Size: -")

    def _current_min_area(self) -> int:
        span = LOCATOR_MIN_AREA_HIGH - LOCATOR_MIN_AREA_LOW
        return int(LOCATOR_MIN_AREA_LOW + self.strictness_var.get() * span)

    def _refresh_counts(self) -> None:
        for w in self.badges_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.badges_frame, text=f"TOTAL   {self.total}", fg_color=ACCENT_SOFT,
                     text_color=ACCENT, font=(FONT_FAMILY, 12, "bold"), corner_radius=10,
                     height=34).pack(side=tk.LEFT, padx=(0, 8), ipadx=8)
        for label, count in sorted(self.per_class.items()):
            ctk.CTkLabel(self.badges_frame, text=f"{label.title()}   {count}", fg_color=PANEL_BG_2,
                         text_color=color_hex_for(label), font=(FONT_FAMILY, 12, "bold"),
                         corner_radius=10, height=34).pack(side=tk.LEFT, padx=(0, 8), ipadx=8)

    # -- model ---------------------------------------------------------------
    def _load_model(self) -> None:
        self.status.set("Loading...")
        self.root.update_idletasks()
        try:
            self.locator = EggLocator()
            self.classifier = EggClassifier()
            if self.classifier.using_custom:
                self.model_info.set("Classifier: custom-trained (models/best-cls.pt)")
                choices = sorted(set(self.classifier.names.values()))
            else:
                self.model_info.set("Classifier: heuristic (no training data yet) — train models/best-cls.pt for real accuracy")
                choices = DEFAULT_CLASS_CHOICES
            self.override_combo.configure(values=choices)

            # Optional: a community-trained cloud model, useful before your
            # own models/best-cls.pt exists. Its absence (no package, no key,
            # no network) is never an error -- it just leaves this feature off.
            self.roboflow = RoboflowEggClassifier() if RoboflowEggClassifier else None
            self.roboflow_status.set(
                f"Roboflow cloud: {self.roboflow.status}" if self.roboflow is not None
                else "Roboflow cloud: not installed (pip install inference-sdk)"
            )

            # Optional: the ESP32-S3 board (load cell + OLED + LEDs + buzzer --
            # see EggMinistrator_ESP32S3.ino). The webcam itself needs no
            # bridge at all; this only carries weight readings in and
            # results out over USB serial. Absent hardware, missing
            # pyserial, or no port found all just leave this feature off.
            if self.esp32 is not None:
                self.esp32.close()
            self.esp32 = ESP32Bridge() if ESP32Bridge else None
            self.esp32_status.set(
                f"ESP32 board: {self.esp32.status}" if self.esp32 is not None
                else "ESP32 board: not installed (pip install pyserial)"
            )

            self.status.set("Ready. Open an image or start the webcam.")
        except Exception as e:
            messagebox.showerror("Model error", str(e))
            self.status.set("Model failed to load — see the error dialog, then click 'Reload Model'.")

    # -- image / webcam handling -----------------------------------------------
    def open_image(self) -> None:
        path = filedialog.askopenfilename(title="Open image", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not path:
            return
        self.stop_camera()
        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror("Image error", "Could not read image.")
            return
        self.analyze_frame(frame)

    def open_image_cloud(self) -> None:
        """Same flow as Open Image, but sends the picture to the Roboflow
        'egg-quality-grading-wlgy5/1' model instead of the local pipeline.
        Useful before you've trained models/best-cls.pt -- this model was
        already trained on someone else's egg-quality dataset."""
        if self.roboflow is None or not self.roboflow.available:
            reason = self.roboflow.status if self.roboflow is not None else "inference-sdk isn't installed"
            messagebox.showinfo(
                "Roboflow not configured",
                f"Can't use the cloud model right now ({reason}).\n\n"
                "Set the ROBOFLOW_API_KEY environment variable (and `pip install inference-sdk` "
                "if needed), then click 'Reload Model'.",
            )
            return
        path = filedialog.askopenfilename(title="Open image for Roboflow analysis",
                                           filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not path:
            return
        self.stop_camera()
        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror("Image error", "Could not read image.")
            return
        self.analyze_frame_cloud(path, frame)

    def _selected_camera_index(self) -> int:
        try:
            return int(self.camera_var.get().replace("Camera", "").strip())
        except ValueError:
            return 0

    def _refresh_cameras(self) -> None:
        self.status.set("Checking for connected cameras...")
        self.root.update_idletasks()
        self.available_cameras = list_cameras()
        values = [f"Camera {i}" for i in self.available_cameras]
        self.camera_combo.configure(values=values)
        if self.camera_var.get() not in values:
            self.camera_var.set(values[0])
        self.status.set(f"Found {len(values)} camera(s): {', '.join(values)}.")

    def _on_camera_change(self, _event) -> None:
        if self.running:
            self.stop_camera()
            self.start_camera()

    def start_camera(self) -> None:
        if self.running:
            return
        if not hasattr(self, "classifier"):
            messagebox.showwarning("Model not ready", "The model hasn't finished loading yet.")
            return
        index = self._selected_camera_index()
        self.capture = cv2.VideoCapture(index, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(index)
        if not self.capture.isOpened():
            self.capture.release()
            self.capture = cv2.VideoCapture(index)
        if not self.capture.isOpened():
            messagebox.showerror(
                "Camera error",
                f"Couldn't open Camera {index}. If you're trying to use an external camera, "
                "make sure it's plugged in, then click 'Refresh Cameras' and pick it from the list.",
            )
            return
        self.running = True
        self.status.set(f"Webcam started (Camera {index}). Waiting for an egg...")
        self.last_inference = 0.0
        self.tracks.clear()
        self.latest = []
        self.preview.configure(text="")
        self.root.after(20, self._camera_loop)

    def stop_camera(self) -> None:
        self.running = False
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.status.set("Camera stopped.")
        self.preview.configure(
            image="",
            text="\U0001F95A\n\nReady when you are.\nClick \u201CStart Webcam\u201D or \u201COpen Image\u201D to begin.",
        )
        self.preview.image = None

    def reset_counts(self) -> None:
        self.tracks.clear()
        self.recent_finalized.clear()
        self.total = 0
        self.per_class = {}
        self.latest = []
        self.last_track = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_counts()
        self.status.set("Counts reset.")

    def close(self) -> None:
        self.stop_camera()
        if self.esp32 is not None:
            self.esp32.close()
        self.root.destroy()

    def _camera_loop(self) -> None:
        if not self.running or self.capture is None:
            return
        ok, frame = self.capture.read()
        if not ok:
            self.status.set("Failed to read camera frame.")
            self.stop_camera()
            return
        now = time.monotonic()
        if now - self.last_inference >= INFERENCE_INTERVAL:
            self.last_inference = now
            try:
                self._process_tick(frame)
            except Exception as e:
                self.status.set(f"Processing error: {e}")
        self.display_frame(frame, tracks=self.tracks)
        self.root.after(15, self._camera_loop)

    def analyze_frame(self, frame: Any) -> None:
        try:
            boxes = self.locator.locate(frame, min_area=self._current_min_area())
            detections = []
            for box in boxes:
                x1, y1, x2, y2 = box
                crop = frame[max(0, y1):y2, max(0, x1):x2]
                label, conf = self.classifier.classify(crop)
                detections.append((x1, y1, x2, y2, label, conf))

            self.latest = detections
            self.total = len(detections)
            self.per_class = {}
            self.last_track = None
            for x1, y1, x2, y2, label, conf in detections:
                self.per_class[label] = self.per_class.get(label, 0) + 1
                self._log_result(label, conf, source="ai")

                # Build a Track purely to reuse the exact same snapshot-saving
                # and Override machinery the live webcam flow uses -- so a
                # photo opened here becomes real, correctable training data
                # too, not just a one-off on-screen result.
                now = time.monotonic()
                t = Track(center=((x1 + x2) // 2, (y1 + y2) // 2), box=(x1, y1, x2, y2),
                          first_seen=now, last_seen=now, state="done",
                          final_label=label, final_conf=conf, counted=True)
                t.tree_item = self._add_history_row(label, conf, "-", "ai")
                if self.autosave_var.get():
                    self._save_snapshot(frame, t)
                self.last_track = t  # if several eggs were found, Override applies to the last one

            self._refresh_counts()
            self.status.set(f"Image: {self.total} egg(s) detected (single-shot, no candling window).")
            self.display_frame(frame, detections=detections)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.set(str(e))

    def analyze_frame_cloud(self, path: str, frame: np.ndarray) -> None:
        """Cloud counterpart to analyze_frame: sends the image to the
        Roboflow 'egg-quality-grading-wlgy5/1' model instead of the local
        locator+classifier pair. Whatever class names that model returns
        are used as-is (they won't necessarily match good/defective/not_egg)
        since it was trained by someone else on their own
        taxonomy."""
        self.status.set("Sending image to Roboflow...")
        self.root.update_idletasks()
        try:
            detections = self.roboflow.detect(path)
        except RoboflowUnavailable as e:
            messagebox.showerror("Roboflow error", str(e))
            self.status.set(f"Roboflow request failed: {e}")
            return

        self.latest = detections
        self.total = len(detections)
        self.per_class = {}
        for *_, label, conf in detections:
            self.per_class[label] = self.per_class.get(label, 0) + 1
            self._log_result(label, conf, source="roboflow")
            self._add_history_row(label, conf, "-", "roboflow")
        self._refresh_counts()
        self.status.set(f"Roboflow: {self.total} egg(s) detected (single-shot, cloud model).")
        self.display_frame(frame, detections=detections)

    # -- detect -> wait for candling -> candle -> count state machine ------------
    def _in_recount_cooldown(self, center: tuple[int, int], now: float) -> bool:
        self.recent_finalized = [
            (c, t) for c, t in self.recent_finalized if now - t < RECOUNT_COOLDOWN_SECONDS
        ]
        return any(
            np.hypot(center[0] - c[0], center[1] - c[1]) < MATCH_DISTANCE_PX
            for c, t in self.recent_finalized
        )

    def _process_tick(self, frame: np.ndarray) -> None:
        now = time.monotonic()
        boxes = self.locator.locate(frame, min_area=self._current_min_area())
        candling_delta = self.candling_delta_var.get()

        for box in boxes:
            x1, y1, x2, y2 = box
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            closest = min(
                self.tracks,
                key=lambda t: np.hypot(center[0] - t.center[0], center[1] - t.center[1]),
                default=None,
            )
            if closest is not None and np.hypot(center[0] - closest.center[0], center[1] - closest.center[1]) < MATCH_DISTANCE_PX:
                closest.center = center
                closest.box = box
                closest.last_seen = now
                self._update_track_state(closest, frame, box, now, candling_delta)
            elif self._in_recount_cooldown(center, now):
                self.status.set("Already counted this egg — move it out of frame before inspecting the next one.")
                continue
            else:
                t = Track(center=center, box=box, first_seen=now, last_seen=now)
                self._update_track_state(t, frame, box, now, candling_delta)
                self.tracks.append(t)
                self.status.set("Egg detected — waiting for it to be candled...")

        self.tracks = [t for t in self.tracks if now - t.last_seen < TRACK_TIMEOUT_SECONDS]

        for t in self.tracks:
            if t.state != "candling" or t.candling_started is None:
                continue
            window_done = now - t.candling_started >= CANDLING_SECONDS
            enough_samples = len(t.samples) >= MIN_CANDLING_SAMPLES
            if window_done and enough_samples:
                t.final_label, t.final_conf = self._finalize_quality(t.samples)
                t.state = "done"
                if not t.counted:
                    self._finalize_track(t, frame)

    def _update_track_state(self, t: Track, frame: np.ndarray, box, now: float, candling_delta: float) -> None:
        brightness = region_brightness(frame, box)
        t.last_brightness = brightness

        if t.state == "waiting":
            t.baseline_samples.append(brightness)
            if len(t.baseline_samples) >= BASELINE_SAMPLE_COUNT and t.baseline_brightness is None:
                t.baseline_brightness = sum(t.baseline_samples) / len(t.baseline_samples)

            if t.baseline_brightness is not None and (brightness - t.baseline_brightness) >= candling_delta:
                t.state = "candling"
                t.candling_started = now
                t.samples = [self._classify_box(frame, box)]
                self.status.set("Candling detected — checking quality...")
        elif t.state == "candling":
            t.samples.append(self._classify_box(frame, box))

    def _classify_box(self, frame: np.ndarray, box) -> tuple[str, float]:
        x1, y1, x2, y2 = box
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        try:
            return self.classifier.classify(crop)
        except Exception as e:
            self.status.set(f"Classify error: {e}")
            return "good", 0.0

    def _finalize_track(self, t: Track, frame: np.ndarray) -> None:
        t.counted = True
        self.total += 1
        self.per_class[t.final_label] = self.per_class.get(t.final_label, 0) + 1
        self.recent_finalized.append((t.center, time.monotonic()))

        # Prefer a live reading from the ESP32 board's load cell over the
        # manually-typed weight field, if one's available and the operator
        # hasn't turned that off -- this is what actually satisfies FR-13
        # ("measure the weight of each inspected egg") without someone
        # having to read a separate display and type it in by hand.
        esp32_weight = None
        if self.esp32 is not None and self.esp32.available and self.esp32_autoweight_var.get():
            esp32_weight = self.esp32.latest_weight()

        if esp32_weight is not None:
            t.weight_g = esp32_weight
            self.weight_var.set(f"{esp32_weight:.1f}")
        else:
            raw_weight = self.weight_var.get().strip()
            try:
                t.weight_g = float(raw_weight) if raw_weight else None
            except ValueError:
                t.weight_g = None
        t.size_class = classify_size(t.weight_g) if t.weight_g is not None else "-"

        self._log_result(t.final_label, t.final_conf, weight=t.weight_g, size_class=t.size_class, source="ai")
        t.tree_item = self._add_history_row(t.final_label, t.final_conf, t.size_class, "ai")
        self.last_track = t

        if self.autosave_var.get():
            self._save_snapshot(frame, t)

        if self.esp32 is not None and self.esp32.available:
            try:
                self.esp32.send_result(t.final_label, t.final_conf)
            except ESP32BridgeUnavailable:
                pass  # board was unplugged mid-session -- don't let this crash a finalized result

        self._refresh_counts()
        self.status.set(f"Result: '{t.final_label}' ({t.final_conf:.0%} confidence) — counted.")
        beep()

    def _finalize_quality(self, samples: list[tuple[str, float]]) -> tuple[str, float]:
        totals: dict[str, float] = {}
        counts: dict[str, int] = {}
        for label, conf in samples:
            totals[label] = totals.get(label, 0.0) + conf
            counts[label] = counts.get(label, 0) + 1
        best_label = max(totals, key=totals.get)
        avg_conf = totals[best_label] / counts[best_label]
        return best_label, avg_conf

    # -- override --------------------------------------------------------------
    def apply_override(self) -> None:
        if self.last_track is None:
            messagebox.showinfo("No result yet", "There's no finalized result to override yet.")
            return
        new_label = self.override_var.get().strip().lower()
        if not new_label:
            messagebox.showinfo("Pick a class", "Choose a class from the dropdown first.")
            return
        old_label = self.last_track.final_label
        if new_label == old_label:
            return
        operator = self.operator_var.get().strip() or "unknown"

        self.per_class[old_label] = max(0, self.per_class.get(old_label, 0) - 1)
        self.per_class[new_label] = self.per_class.get(new_label, 0) + 1
        self.last_track.final_label = new_label
        self._relabel_snapshot(self.last_track, new_label)

        self._log_result(new_label, 1.0, weight=self.last_track.weight_g, size_class=self.last_track.size_class,
                          source=f"override:{operator}")
        if self.last_track.tree_item is not None:
            self.tree.item(self.last_track.tree_item, values=(
                self.tree.set(self.last_track.tree_item, "time"), new_label, "manual",
                self.last_track.size_class, f"override:{operator}",
            ))
        self._refresh_counts()
        self.status.set(f"Overridden to '{new_label}' by {operator}.")

    # -- logging / history / snapshots -------------------------------------------
    def _log_result(self, label: str, conf: float, weight: Optional[float] = None,
                     size_class: str = "-", source: str = "ai") -> None:
        new_file = not LOG_PATH.exists()
        try:
            with open(LOG_PATH, "a", newline="") as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(["timestamp", "label", "confidence", "weight_g", "size_class", "source"])
                writer.writerow([
                    datetime.now().isoformat(timespec="seconds"), label, f"{conf:.3f}",
                    f"{weight:.1f}" if weight is not None else "", size_class, source,
                ])
        except OSError:
            pass

        if self.web_sync_var.get():
            payload = {
                "label": label,
                "confidence": conf,
                "weight_g": weight,
                "source": source,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            threading.Thread(target=self._post_inspection, args=(payload,), daemon=True).start()

    # -- web dashboard sync -------------------------------------------------------
    def _post_inspection(self, payload: dict) -> None:
        try:
            resp = requests.post(
                f"{WEB_API_BASE}/inspections",
                json=payload,
                headers={"X-Device-Key": DEVICE_API_KEY},
                timeout=2.0,
            )
            if resp.status_code == 201:
                self.root.after(0, lambda: self.web_sync_status.set("Dashboard: connected"))
                return
            self.root.after(0, lambda: self.web_sync_status.set(f"Dashboard: rejected ({resp.status_code})"))
        except requests.RequestException:
            self._queue_pending(payload)
            self.root.after(0, lambda: self.web_sync_status.set("Dashboard: offline (queued)"))

    def _queue_pending(self, payload: dict) -> None:
        try:
            with open(PENDING_SYNC_PATH, "a") as f:
                f.write(json.dumps(payload) + "\n")
        except OSError:
            pass

    def _flush_pending_sync(self) -> None:
        if self.web_sync_var.get() and PENDING_SYNC_PATH.exists():
            threading.Thread(target=self._flush_pending_sync_worker, daemon=True).start()
        self.root.after(SYNC_RETRY_INTERVAL_MS, self._flush_pending_sync)

    def _flush_pending_sync_worker(self) -> None:
        try:
            lines = PENDING_SYNC_PATH.read_text().splitlines()
        except OSError:
            return
        if not lines:
            return

        still_pending = []
        sent = 0
        for line in lines:
            try:
                payload = json.loads(line)
                resp = requests.post(
                    f"{WEB_API_BASE}/inspections",
                    json=payload,
                    headers={"X-Device-Key": DEVICE_API_KEY},
                    timeout=2.0,
                )
                if resp.status_code == 201:
                    sent += 1
                else:
                    still_pending.append(line)
            except requests.RequestException:
                still_pending.append(line)

        try:
            if still_pending:
                PENDING_SYNC_PATH.write_text("\n".join(still_pending) + "\n")
            else:
                PENDING_SYNC_PATH.unlink(missing_ok=True)
        except OSError:
            pass

        if sent:
            status = f"Dashboard: connected (synced {sent} queued result{'s' if sent != 1 else ''})"
            self.root.after(0, lambda: self.web_sync_status.set(status))

    def _add_history_row(self, label: str, conf: float, size_class: str, source: str) -> str:
        time_str = datetime.now().strftime("%H:%M:%S")
        item = self.tree.insert("", 0, values=(time_str, label, f"{conf:.0%}", size_class, source))
        children = self.tree.get_children()
        if len(children) > HISTORY_MAX_ROWS:
            for extra in children[HISTORY_MAX_ROWS:]:
                self.tree.delete(extra)
        return item

    def _save_snapshot(self, frame: np.ndarray, t: Track) -> None:
        try:
            x1, y1, x2, y2 = t.box
            pad = 6
            crop = frame[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad]
            if crop.size == 0:
                return
            out_dir = SNAPSHOT_DIR / t.final_label
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            out_path = out_dir / f"{ts}.jpg"
            cv2.imwrite(str(out_path), crop)
            t.snapshot_path = out_path
        except Exception:
            pass

    def _relabel_snapshot(self, t: Track, new_label: str) -> None:
        """Moves a track's already-saved training image into the folder for
        its corrected label. Without this, overriding a wrong AI guess fixes
        the on-screen count and the CSV log, but the image sitting in
        dataset/collected/<old_label>/ stays mislabeled -- and since that
        folder IS the training set (see prepare_dataset.py), every override
        the operator makes would otherwise silently poison the next training
        run instead of improving it."""
        if t.snapshot_path is None or not t.snapshot_path.exists():
            return
        try:
            new_dir = SNAPSHOT_DIR / new_label
            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / t.snapshot_path.name
            t.snapshot_path.replace(new_path)
            t.snapshot_path = new_path
        except OSError:
            pass

    def export_report(self) -> None:
        REPORTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"report_{ts}.txt"
        lines = [
            "Egg Inspection Session Report",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"Operator: {self.operator_var.get().strip() or 'unknown'}",
            "",
            f"Total eggs inspected: {self.total}",
        ]
        for label, count in sorted(self.per_class.items()):
            pct = (count / self.total * 100) if self.total else 0.0
            lines.append(f"  {label.title()}: {count} ({pct:.1f}%)")
        lines.append("")
        lines.append(f"Full log: {LOG_PATH.name}")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            self.status.set(f"Report saved to reports/{path.name}")
        except OSError as e:
            messagebox.showerror("Export failed", str(e))

    # -- rendering -------------------------------------------------------------
    def display_frame(self, frame: np.ndarray, detections=None, tracks=None) -> None:
        preview = frame.copy()
        if tracks is not None:
            now = time.monotonic()
            for t in tracks:
                x1, y1, x2, y2 = t.box
                if t.state == "waiting":
                    color = WAITING_COLOR_BGR
                    if t.baseline_brightness is None:
                        text = "Egg detected - measuring..."
                    else:
                        delta = t.last_brightness - t.baseline_brightness
                        text = f"Waiting for candling (light +{delta:.0f})"
                elif t.state == "candling":
                    remaining = max(0.0, CANDLING_SECONDS - (now - t.candling_started))
                    color = CANDLING_COLOR_BGR
                    text = f"Candling... {remaining:.1f}s"
                else:
                    color = color_bgr_for(t.final_label)
                    text = f"{t.final_label} {t.final_conf:.0%}"
                cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
                cv2.putText(preview, text, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        elif detections:
            for x1, y1, x2, y2, label, conf in detections:
                color = color_bgr_for(label)
                text = f"{label} {conf:.0%}"
                cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
                cv2.putText(preview, text, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        image = Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))
        target_w = max(200, self.preview.winfo_width())
        target_h = max(200, self.preview.winfo_height())
        image.thumbnail((target_w, target_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self.preview.image = photo
        self.preview.configure(image=photo, text="")


if __name__ == "__main__":
    root = ctk.CTk()
    EggInspectorYOLO(root)
    root.mainloop()
