"""What the listener can see that the server cannot: which holes have an egg.

Three regimes per slot, from mean brightness against two calibrated levels:

    dark    the candler is off, or the lens is covered, for this hole
    egg     something translucent is blocking the aperture
    empty   the lit hole with nothing in it

The v1 brightness gate (listen_station.py, Session 12) is the same idea with
one rectangle. Six rectangles add a second question -- WHICH holes are
occupied -- and that is what the count and prefix rules answer:

    occupancy_mismatch   the board said k weights, the camera sees n != k eggs
    not_prefix           k eggs, but not in slots 1..k (loaded out of order)

Both are refusals (spec D3). All-dark is neither: the listener holds and
retries, because a dead lamp must stall a loaded tray, never void it.

Pure functions on top of tray_map.crop_slot, so all of this is testable with
synthetic frames and no camera.
"""

from tray_map import SLOT_COUNT, crop_slot

DARK, EGG, EMPTY = "dark", "egg", "empty"


def slot_regime(brightness, dark_level, empty_level, dark_fraction, empty_fraction):
    span = empty_level - dark_level
    if brightness < dark_level + dark_fraction * span:
        return DARK
    if brightness > dark_level + empty_fraction * span:
        return EMPTY
    return EGG


def classify_slots(frame, tray_map):
    occupancy = tray_map["occupancy"]
    out = {}
    for slot in range(1, SLOT_COUNT + 1):
        brightness = float(crop_slot(frame, tray_map, slot).mean())
        level = occupancy["levels"][str(slot)]
        out[slot] = {
            "brightness": brightness,
            "regime": slot_regime(brightness, level["dark"], level["empty"], occupancy["dark_fraction"], occupancy["empty_fraction"]),
        }
    return out


def all_dark(regimes):
    return all(info["regime"] == DARK for info in regimes.values())


def occupied_slots(regimes):
    return sorted(slot for slot, info in regimes.items() if info["regime"] == EGG)


def check_occupancy(regimes, weight_count):
    """None when the picture agrees with the weights; else (reason, detail)
    ready for POST /api/cycles/:id/reject."""
    occupied = occupied_slots(regimes)
    if len(occupied) != weight_count:
        return "occupancy_mismatch", f"{weight_count} weights, {len(occupied)} occupied slots {occupied}"
    if occupied != list(range(1, weight_count + 1)):
        return "not_prefix", f"occupied slots {occupied}, expected 1..{weight_count}"
    return None
