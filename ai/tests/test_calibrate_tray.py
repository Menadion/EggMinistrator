import numpy as np
import pytest

import calibrate_tray as ct
import tray_map as tm


def test_measure_levels_averages_over_frames_per_slot():
    rects = {s: tm.slot_rect(tm.DEFAULT_TRAY_MAP, s) for s in range(1, 7)}
    a = np.zeros((2160, 3840, 3), dtype=np.uint8)
    b = np.zeros((2160, 3840, 3), dtype=np.uint8)
    x, y, w, h = rects[3]
    a[y:y + h, x:x + w] = 100
    b[y:y + h, x:x + w] = 140
    levels = ct.measure_levels([a, b], rects)
    assert abs(levels[3] - 120.0) < 0.01 and levels[1] == 0.0


def test_build_tray_map_is_valid_and_carries_the_measurements():
    rects = {s: tm.slot_rect(tm.DEFAULT_TRAY_MAP, s) for s in range(1, 7)}
    dark = {s: 1.2 for s in range(1, 7)}
    empty = {s: 140.0 + s for s in range(1, 7)}
    data = ct.build_tray_map({"camera": 1, "width": 3840, "height": 2160, "fourcc": "MJPG"}, rects, dark, empty)
    tm.validate_tray_map(data)
    assert data["capture"]["camera"] == 1 and data["capture"]["fourcc"] == "MJPG"
    assert data["occupancy"]["levels"]["4"] == {"dark": 1.2, "empty": 144.0}
    assert data["slots"]["6"] == {"x": 2180, "y": 1440, "w": 1100, "h": 620}


def test_build_tray_map_refuses_a_dark_level_above_the_empty_level():
    rects = {s: tm.slot_rect(tm.DEFAULT_TRAY_MAP, s) for s in range(1, 7)}
    with pytest.raises(tm.TrayMapError):
        ct.build_tray_map({"camera": 0, "width": 3840, "height": 2160, "fourcc": "MJPG"}, rects, {s: 200.0 for s in range(1, 7)}, {s: 150.0 for s in range(1, 7)})


def test_nudge_keeps_aspect_and_stays_inside():
    rect = (560, 60, 1100, 620)
    assert ct.nudge(rect, 10, -100, 0, 3840, 2160) == (570, 0, 1100, 620)      # clamped at the top
    grown = ct.nudge(rect, 0, 0, 100, 3840, 2160)
    assert grown[2] == 1200 and abs(grown[3] / grown[2] - 620 / 1100) < 0.01
    assert ct.nudge((3000, 1800, 1100, 620), 0, 0, 0, 3840, 2160) == (2740, 1540, 1100, 620)   # pushed back inside
