"""The tray's geometry and naming, in one file, read by everything.

    ai/tray_map.json           per-rig, gitignored (like capture_settings.json)
    ai/scripts/calibrate_tray.py   writes it from live measurement
    ai/listen_tray.py          crops with it
    ai/scripts/make_tray_frame.py  builds synthetic frames with it
    ai/tray_occupancy.py       reads its thresholds

WHY ONE FILE. The pan_y -160 bug (afe3496) was two components silently
disagreeing about framing. Here the rectangles, the resolution they are valid
at, the slot -> label mapping and the occupancy thresholds all travel
together, so there is nothing to disagree about.

The rectangles are only valid at capture.width x capture.height. crop_slot
refuses any other frame size rather than silently cropping the wrong pixels.
"""

import json
from pathlib import Path

SLOT_COUNT = 6
# Loading order = slot number. Labels are for humans (TFT, dashboard); the
# number is what is stored. 1=A1 ... 6=C2, row by row.
SLOT_LABELS = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2"}
TRAY_MAP_PATH = Path(__file__).resolve().parent / "tray_map.json"

# The synthetic geometry: a 4K frame, three rows of two, each rectangle in the
# dataset's own 16:9 aspect (1163x654 crops), so a pasted dataset image is not
# distorted and the model sees the framing it was trained on. A real rig
# replaces every number here via calibrate_tray.py.
_W, _H = 1100, 620
_COLS = (560, 2180)
_ROWS = (60, 750, 1440)
DEFAULT_TRAY_MAP = {
    "capture": {"camera": 0, "width": 3840, "height": 2160, "fourcc": "MJPG"},
    "slots": {
        str(slot): {"x": _COLS[(slot - 1) % 2], "y": _ROWS[(slot - 1) // 2], "w": _W, "h": _H}
        for slot in range(1, SLOT_COUNT + 1)
    },
    "occupancy": {
        # Regime boundaries as fractions of the (empty - dark) span per slot:
        #   brightness < dark + 0.25*span  -> dark   (candler off / lens covered)
        #   brightness > dark + 0.85*span  -> empty  (nothing blocking the aperture)
        #   otherwise                       -> egg    (something translucent in the hole)
        # v1's measured numbers (listen_station.py): darkest real egg 49, empty
        # platform 87-215, covered lens 0.9. Rig-dependent; measured by calibrate_tray.py.
        "dark_fraction": 0.25,
        "empty_fraction": 0.85,
        "levels": {str(slot): {"dark": 1.0, "empty": 150.0} for slot in range(1, SLOT_COUNT + 1)},
    },
}


class TrayMapError(ValueError):
    """The tray map is missing, malformed, or does not match the frame."""


def _int_field(container, key, where):
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TrayMapError(f"{where}.{key} must be a non-negative integer, got {value!r}")
    return value


def validate_tray_map(data):
    if not isinstance(data, dict):
        raise TrayMapError("tray map must be a JSON object")
    capture = data.get("capture")
    if not isinstance(capture, dict):
        raise TrayMapError("capture section is missing")
    width = _int_field(capture, "width", "capture")
    height = _int_field(capture, "height", "capture")
    if width == 0 or height == 0:
        raise TrayMapError("capture.width and capture.height must be positive")

    slots = data.get("slots")
    if not isinstance(slots, dict) or sorted(slots) != [str(s) for s in range(1, SLOT_COUNT + 1)]:
        raise TrayMapError(f"slots must have exactly the keys 1..{SLOT_COUNT}")
    for key, rect in slots.items():
        if not isinstance(rect, dict):
            raise TrayMapError(f"slots.{key} must be an object")
        x, y, w, h = (_int_field(rect, name, f"slots.{key}") for name in ("x", "y", "w", "h"))
        if w == 0 or h == 0 or x + w > width or y + h > height:
            raise TrayMapError(f"slots.{key} must lie inside the {width}x{height} frame")

    occupancy = data.get("occupancy")
    if not isinstance(occupancy, dict):
        raise TrayMapError("occupancy section is missing")
    dark_fraction = occupancy.get("dark_fraction")
    empty_fraction = occupancy.get("empty_fraction")
    for name, value in (("dark_fraction", dark_fraction), ("empty_fraction", empty_fraction)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TrayMapError(f"occupancy.{name} must be a number")
    if not 0 < dark_fraction < empty_fraction < 1:
        raise TrayMapError("occupancy fractions must satisfy 0 < dark_fraction < empty_fraction < 1")
    levels = occupancy.get("levels")
    if not isinstance(levels, dict) or sorted(levels) != sorted(slots):
        raise TrayMapError("occupancy.levels must have one entry per slot")
    for key, level in levels.items():
        if not isinstance(level, dict):
            raise TrayMapError(f"occupancy.levels.{key} must be an object")
        dark, empty = level.get("dark"), level.get("empty")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (dark, empty)) or not 0 <= dark < empty <= 255:
            raise TrayMapError(f"occupancy.levels.{key}: need 0 <= dark level < empty level <= 255, got {dark!r}, {empty!r}")
    return data


def load_tray_map(path=TRAY_MAP_PATH):
    path = Path(path)
    if not path.exists():
        raise TrayMapError(
            f"No tray map at {path}. Run ai/scripts/calibrate_tray.py on the rig first "
            "(or pass --default-map to the synthetic tools)."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as error:
        raise TrayMapError(f"{path} is not valid JSON: {error}") from error
    return validate_tray_map(data)


def write_tray_map(data, path=TRAY_MAP_PATH):
    validate_tray_map(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def slot_rect(tray_map, slot):
    rect = tray_map["slots"][str(slot)]
    return rect["x"], rect["y"], rect["w"], rect["h"]


def crop_slot(frame, tray_map, slot):
    """The pixels of one slot. A view into the frame, so crop first and then
    save/classify the same array (v1's audit discipline)."""
    expected = (tray_map["capture"]["height"], tray_map["capture"]["width"])
    if frame.shape[:2] != expected:
        raise TrayMapError(
            f"frame is {frame.shape[1]}x{frame.shape[0]} but the tray map is calibrated for "
            f"{expected[1]}x{expected[0]}; re-run calibrate_tray.py or fix the capture settings"
        )
    x, y, w, h = slot_rect(tray_map, slot)
    return frame[y:y + h, x:x + w]


def slot_label(slot):
    try:
        return SLOT_LABELS[int(slot)]
    except (KeyError, ValueError) as error:
        raise TrayMapError(f"no such slot: {slot!r}") from error
