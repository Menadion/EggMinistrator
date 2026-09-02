import json

import numpy as np
import pytest

import tray_map as tm


def test_default_map_is_valid_and_six_slots_inside_the_frame():
    data = tm.validate_tray_map(tm.DEFAULT_TRAY_MAP)
    assert data["capture"]["width"] == 3840 and data["capture"]["height"] == 2160
    assert sorted(int(k) for k in data["slots"]) == [1, 2, 3, 4, 5, 6]
    for slot in range(1, 7):
        x, y, w, h = tm.slot_rect(data, slot)
        assert x >= 0 and y >= 0 and x + w <= 3840 and y + h <= 2160
        assert abs(w / h - 1163 / 654) < 0.02      # the dataset's aspect, so a pasted crop is not distorted


def test_slots_do_not_overlap():
    rects = [tm.slot_rect(tm.DEFAULT_TRAY_MAP, s) for s in range(1, 7)]
    for i, (ax, ay, aw, ah) in enumerate(rects):
        for bx, by, bw, bh in rects[i + 1:]:
            assert ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay


def test_labels_follow_the_loading_order():
    assert [tm.slot_label(s) for s in range(1, 7)] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    with pytest.raises(tm.TrayMapError):
        tm.slot_label(7)


def test_crop_slot_returns_exactly_the_rectangle():
    frame = np.zeros((2160, 3840, 3), dtype=np.uint8)
    x, y, w, h = tm.slot_rect(tm.DEFAULT_TRAY_MAP, 4)
    frame[y:y + h, x:x + w] = 77
    crop = tm.crop_slot(frame, tm.DEFAULT_TRAY_MAP, 4)
    assert crop.shape == (h, w, 3) and crop.min() == 77
    assert tm.crop_slot(frame, tm.DEFAULT_TRAY_MAP, 1).max() == 0


def test_crop_slot_refuses_a_frame_of_the_wrong_size():
    with pytest.raises(tm.TrayMapError, match="calibrated"):
        tm.crop_slot(np.zeros((720, 1280, 3), dtype=np.uint8), tm.DEFAULT_TRAY_MAP, 1)


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["slots"].pop("6"), "slots"),
    (lambda d: d["slots"]["1"].update({"x": 3000}), "inside"),
    (lambda d: d["occupancy"].update({"dark_fraction": 0.9}), "fraction"),
    (lambda d: d["occupancy"]["levels"]["2"].update({"dark": 200.0}), "level"),
    (lambda d: d["capture"].pop("width"), "capture"),
])
def test_validate_rejects_broken_maps(mutate, message):
    data = json.loads(json.dumps(tm.DEFAULT_TRAY_MAP))
    mutate(data)
    with pytest.raises(tm.TrayMapError, match=message):
        tm.validate_tray_map(data)


def test_round_trip_through_disk(tmp_path):
    path = tmp_path / "tray_map.json"
    tm.write_tray_map(tm.DEFAULT_TRAY_MAP, path)
    assert tm.load_tray_map(path) == tm.DEFAULT_TRAY_MAP
    with pytest.raises(tm.TrayMapError, match="calibrate_tray"):
        tm.load_tray_map(tmp_path / "missing.json")
