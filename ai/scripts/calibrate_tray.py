"""Write ai/tray_map.json from the rig itself, instead of anyone guessing it.

WHAT IT MEASURES
    1. The capture settings that actually work on this rig: camera index,
       resolution and fourcc. "4K is tricky" (pinned.md) is solved here once --
       if the driver will not give 3840x2160 in the asked format, this says so
       before any rectangle is drawn.
    2. Six crop rectangles, nudged by hand over a live preview until each one
       frames one hole of the tray the way the dataset framed one egg.
    3. Two brightness levels per slot: EMPTY (tray in place, candler on, no
       eggs) and DARK (candler off). tray_occupancy.py reads regimes off
       these. BRIGHTNESS_MIN's standing comment applies: thresholds are
       rig-dependent and must be measured, not guessed.

KEYS
    1-6        select a slot
    arrows     move the selected rectangle
    + / -      grow / shrink it (aspect kept at the dataset's 16:9)
    e          measure EMPTY levels now (tray in, lit, no eggs)
    d          measure DARK levels now (candler off)
    s          save ai/tray_map.json (needs both measurements)
    q / Esc    quit

RUNNING IT
    py ai/scripts/calibrate_tray.py --camera 1
    py ai/scripts/calibrate_tray.py --camera 1 --fourcc YUY2 --width 1920 --height 1080
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from station_common import open_camera  # noqa: E402
from tray_map import DEFAULT_TRAY_MAP, SLOT_COUNT, TRAY_MAP_PATH, slot_label, validate_tray_map, write_tray_map  # noqa: E402
from listen_tray import configure_camera  # noqa: E402

ASPECT = 620 / 1100          # h / w, the dataset's own framing
PREVIEW_WIDTH = 960
MOVE_STEP = 10
GROW_STEP = 20
WINDOW = "calibrate tray"
COLOUR = (0, 255, 0)
SELECTED = (0, 200, 255)


def measure_levels(frames, rects):
    """Per-slot mean brightness, averaged over the frames."""
    levels = {}
    for slot, (x, y, w, h) in rects.items():
        levels[slot] = float(np.mean([frame[y:y + h, x:x + w].mean() for frame in frames]))
    return levels


def nudge(rect, dx, dy, dw, frame_w, frame_h):
    """Move by (dx, dy), grow width by dw keeping the aspect, and keep the whole
    rectangle inside the frame."""
    x, y, w, h = rect
    w = max(100, w + dw)
    h = int(round(w * ASPECT))
    w = min(w, frame_w)
    h = min(h, frame_h)
    x = min(max(0, x + dx), frame_w - w)
    y = min(max(0, y + dy), frame_h - h)
    return int(x), int(y), int(w), int(h)


def build_tray_map(capture, rects, dark, empty, dark_fraction=0.25, empty_fraction=0.85):
    data = {
        "capture": {"camera": int(capture["camera"]), "width": int(capture["width"]), "height": int(capture["height"]), "fourcc": capture.get("fourcc") or "MJPG"},
        "slots": {str(s): {"x": rects[s][0], "y": rects[s][1], "w": rects[s][2], "h": rects[s][3]} for s in range(1, SLOT_COUNT + 1)},
        "occupancy": {
            "dark_fraction": dark_fraction,
            "empty_fraction": empty_fraction,
            "levels": {str(s): {"dark": round(float(dark[s]), 2), "empty": round(float(empty[s]), 2)} for s in range(1, SLOT_COUNT + 1)},
        },
    }
    return validate_tray_map(data)


def grab_frames(camera, count):
    frames = []
    for _ in range(count):
        ok, frame = camera.read()
        if ok:
            frames.append(frame)
        time.sleep(0.05)
    if not frames:
        raise SystemExit("Lost the camera feed.")
    return frames


def draw_preview(frame, rects, selected, scale, status):
    preview = cv2.resize(frame, None, fx=scale, fy=scale)
    for slot, (x, y, w, h) in rects.items():
        colour = SELECTED if slot == selected else COLOUR
        p1 = (int(x * scale), int(y * scale))
        p2 = (int((x + w) * scale), int((y + h) * scale))
        cv2.rectangle(preview, p1, p2, colour, 2)
        cv2.putText(preview, f"{slot} {slot_label(slot)}", (p1[0] + 6, p1[1] + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)
    cv2.putText(preview, status, (8, preview.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return preview


def main():
    parser = argparse.ArgumentParser(description="Measure the tray rig and write ai/tray_map.json.")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--fourcc", default="MJPG")
    parser.add_argument("--frames", type=int, default=10, help="frames averaged per measurement")
    parser.add_argument("--out", default=str(TRAY_MAP_PATH))
    args = parser.parse_args()

    capture = {"camera": args.camera, "width": args.width, "height": args.height, "fourcc": args.fourcc}
    camera = open_camera(args.camera)
    if camera is None:
        raise SystemExit(f"Could not open camera {args.camera}.")
    configure_camera(camera, capture)   # exits with the honest message if the driver refuses the size
    print(f"Camera {args.camera}: {args.width}x{args.height} {args.fourcc} confirmed.")

    # Start from the synthetic geometry scaled to this resolution.
    sx, sy = args.width / 3840, args.height / 2160
    rects = {s: nudge((int(DEFAULT_TRAY_MAP["slots"][str(s)]["x"] * sx), int(DEFAULT_TRAY_MAP["slots"][str(s)]["y"] * sy),
                       int(DEFAULT_TRAY_MAP["slots"][str(s)]["w"] * sx), 0), 0, 0, 0, args.width, args.height)
             for s in range(1, SLOT_COUNT + 1)}
    scale = PREVIEW_WIDTH / args.width
    selected = 1
    dark = empty = None
    status = "select 1-6, arrows move, +/- size, e=empty levels, d=dark levels, s=save, q=quit"

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise SystemExit("Lost the camera feed.")
            cv2.imshow(WINDOW, draw_preview(frame, rects, selected, scale, status))
            key = cv2.waitKeyEx(30)
            if key in (ord("q"), 27):
                break
            if ord("1") <= key <= ord("6"):
                selected = key - ord("0")
            elif key in (2424832, 65361):      # left
                rects[selected] = nudge(rects[selected], -MOVE_STEP, 0, 0, args.width, args.height)
            elif key in (2555904, 65363):      # right
                rects[selected] = nudge(rects[selected], MOVE_STEP, 0, 0, args.width, args.height)
            elif key in (2490368, 65362):      # up
                rects[selected] = nudge(rects[selected], 0, -MOVE_STEP, 0, args.width, args.height)
            elif key in (2621440, 65364):      # down
                rects[selected] = nudge(rects[selected], 0, MOVE_STEP, 0, args.width, args.height)
            elif key in (ord("+"), ord("=")):
                rects[selected] = nudge(rects[selected], 0, 0, GROW_STEP, args.width, args.height)
            elif key in (ord("-"), ord("_")):
                rects[selected] = nudge(rects[selected], 0, 0, -GROW_STEP, args.width, args.height)
            elif key == ord("e"):
                empty = measure_levels(grab_frames(camera, args.frames), rects)
                status = "EMPTY levels: " + "  ".join(f"{s}:{v:.0f}" for s, v in empty.items())
                print(status)
            elif key == ord("d"):
                dark = measure_levels(grab_frames(camera, args.frames), rects)
                status = "DARK levels: " + "  ".join(f"{s}:{v:.0f}" for s, v in dark.items())
                print(status)
            elif key == ord("s"):
                if dark is None or empty is None:
                    status = "measure both e (empty, lit) and d (dark) before saving"
                    continue
                try:
                    path = write_tray_map(build_tray_map(capture, rects, dark, empty), args.out)
                except Exception as error:   # TrayMapError or OSError -- show it, keep the window open
                    status = f"not saved: {error}"
                    continue
                status = f"saved {path}"
                print(status)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
