import numpy as np

import tray_map as tm
import tray_occupancy as occ


def test_slot_regime_boundaries():
    # dark 1, empty 151 -> span 150: dark below 38.5, empty above 128.5
    assert occ.slot_regime(0.9, 1.0, 151.0, 0.25, 0.85) == occ.DARK
    assert occ.slot_regime(38.0, 1.0, 151.0, 0.25, 0.85) == occ.DARK
    assert occ.slot_regime(49.4, 1.0, 151.0, 0.25, 0.85) == occ.EGG     # v1's darkest real egg
    assert occ.slot_regime(100.0, 1.0, 151.0, 0.25, 0.85) == occ.EGG
    assert occ.slot_regime(129.0, 1.0, 151.0, 0.25, 0.85) == occ.EMPTY
    assert occ.slot_regime(215.0, 1.0, 151.0, 0.25, 0.85) == occ.EMPTY  # brighter than calibrated is still empty


def _frame_with(slot_values):
    frame = np.zeros((2160, 3840, 3), dtype=np.uint8)
    for slot, value in slot_values.items():
        x, y, w, h = tm.slot_rect(tm.DEFAULT_TRAY_MAP, slot)
        frame[y:y + h, x:x + w] = value
    return frame


def test_classify_slots_reads_each_rectangle():
    frame = _frame_with({1: 80, 2: 80, 3: 150, 4: 0, 5: 80, 6: 150})
    regimes = occ.classify_slots(frame, tm.DEFAULT_TRAY_MAP)
    assert [regimes[s]["regime"] for s in range(1, 7)] == [occ.EGG, occ.EGG, occ.EMPTY, occ.DARK, occ.EGG, occ.EMPTY]
    assert abs(regimes[1]["brightness"] - 80.0) < 0.01


def test_all_dark_only_when_every_slot_is_dark():
    assert occ.all_dark(occ.classify_slots(_frame_with({}), tm.DEFAULT_TRAY_MAP)) is True
    assert occ.all_dark(occ.classify_slots(_frame_with({6: 150}), tm.DEFAULT_TRAY_MAP)) is False


def test_occupied_slots_and_prefix_rules():
    regimes = occ.classify_slots(_frame_with({1: 80, 2: 80, 3: 80, 4: 150, 5: 150, 6: 150}), tm.DEFAULT_TRAY_MAP)
    assert occ.occupied_slots(regimes) == [1, 2, 3]
    assert occ.check_occupancy(regimes, 3) is None
    assert occ.check_occupancy(regimes, 2) == ("occupancy_mismatch", "2 weights, 3 occupied slots [1, 2, 3]")
    gap = occ.classify_slots(_frame_with({1: 80, 3: 80, 2: 150, 4: 150, 5: 150, 6: 150}), tm.DEFAULT_TRAY_MAP)
    assert occ.check_occupancy(gap, 2) == ("not_prefix", "occupied slots [1, 3], expected 1..2")


def test_a_dark_slot_among_lit_ones_counts_as_not_occupied():
    # One dead LED under slot 4 with an egg on it reads dark, not egg. That is
    # an occupancy mismatch (refuse the tray), not a candler hold -- only
    # ALL-dark means the lamp is off.
    regimes = occ.classify_slots(_frame_with({1: 80, 2: 80, 3: 80, 4: 0, 5: 150, 6: 150}), tm.DEFAULT_TRAY_MAP)
    assert occ.all_dark(regimes) is False
    assert occ.check_occupancy(regimes, 4) == ("occupancy_mismatch", "4 weights, 3 occupied slots [1, 2, 3]")
