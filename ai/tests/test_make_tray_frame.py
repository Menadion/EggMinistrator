import json
import random
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

import tray_map as tm
import make_tray_frame as mtf


def _fake_dataset(root):
    for cls, colour in (("good", (0, 0, 200)), ("defective", (0, 200, 0)), ("not_an_egg", (200, 0, 0))):
        folder = root / cls
        folder.mkdir(parents=True)
        for i in range(3):
            image = np.full((654, 1163, 3), colour, dtype=np.uint8)
            image[:, :, :] = np.array(colour, dtype=np.uint8) + i   # distinct per file
            cv2.imwrite(str(folder / f"{cls}_{i}.png"), image)
    return root


def test_pick_sources_draws_only_the_asked_classes(tmp_path):
    root = _fake_dataset(tmp_path / "ds")
    picks = mtf.pick_sources(root, ["good", "defective"], 6, random.Random(1))
    assert len(picks) == 6
    assert {cls for cls, _ in picks} <= {"good", "defective"}
    assert all(path.exists() for _, path in picks)


def test_build_frame_pastes_each_source_into_its_rectangle_and_leaves_gaps_black(tmp_path):
    root = _fake_dataset(tmp_path / "ds")
    good = root / "good" / "good_0.png"
    frame = mtf.build_frame(tm.DEFAULT_TRAY_MAP, {1: good, 2: None, 3: good, 4: None, 5: None, 6: None})
    assert frame.shape == (2160, 3840, 3)
    x, y, w, h = tm.slot_rect(tm.DEFAULT_TRAY_MAP, 1)
    expected = cv2.resize(cv2.imread(str(good)), (w, h))
    assert np.array_equal(tm.crop_slot(frame, tm.DEFAULT_TRAY_MAP, 1), expected)
    empty_level = tm.DEFAULT_TRAY_MAP["occupancy"]["levels"]["2"]["empty"]
    assert abs(tm.crop_slot(frame, tm.DEFAULT_TRAY_MAP, 2).mean() - empty_level) < 0.5
    assert frame[0, 0].max() == 0 and frame[2159, 3839].max() == 0     # between the holes the tray blocks the light


def test_cli_writes_a_frame_and_matching_ground_truth(tmp_path):
    root = _fake_dataset(tmp_path / "ds")
    out = tmp_path / "out"
    script = Path(mtf.__file__)
    completed = subprocess.run([sys.executable, str(script), "--eggs", "4", "--source", str(root), "--seed", "5", "--out", str(out), "--default-map", "--name", "t"],
                               capture_output=True, text=True, cwd=script.parents[2])
    assert completed.returncode == 0, completed.stderr
    truth = json.loads((out / "t.json").read_text())
    assert truth["eggs"] == 4 and truth["tray_map"] == "default"
    assert [truth["slots"][str(s)] is not None for s in range(1, 7)] == [True, True, True, True, False, False]
    frame = cv2.imread(str(out / "t.jpg"))
    assert frame.shape == (2160, 3840, 3)
    assert truth["slots"]["1"]["class"] in {"good", "defective"}
