import json

import numpy as np

import listen_tray as lt
import tray_map as tm


def _frame_with(slot_values):
    frame = np.zeros((2160, 3840, 3), dtype=np.uint8)
    for slot, value in slot_values.items():
        x, y, w, h = tm.slot_rect(tm.DEFAULT_TRAY_MAP, slot)
        frame[y:y + h, x:x + w] = value
    return frame


def _fake_classify(crops):
    # Slot i's crop was filled with value 80+i by the test, so the class can
    # be read back from the pixels: proves the right crop reached the right slot.
    out = []
    for crop in crops:
        marker = int(crop[0, 0, 0]) - 80
        label = ["good", "defective", "good", "not_an_egg", "good", "good"][marker - 1]
        out.append({"class": label, "confidence": 0.9, "model_name": "m", "model_version": "v", "inference_time_ms": 12,
                    "raw_result": json.dumps({"good": 0.9, "defective": 0.05, "not_an_egg": 0.05})})
    return out


def _fake_save(tmp_path):
    def save(frame, crops_by_slot, cycle_id):
        return f"{tmp_path.as_posix()}/cycle_{cycle_id}.jpg", {s: f"{tmp_path.as_posix()}/cycle_{cycle_id}_slot{s}.jpg" for s in crops_by_slot}
    return save


def test_run_cycle_assesses_a_prefix_tray(tmp_path):
    frame = _frame_with({1: 81, 2: 82, 3: 83, 4: 150, 5: 150, 6: 150})
    outcome, body = lt.run_cycle({"id": 17, "weights": [58.2, 61.0, 55.4]}, frame, tm.DEFAULT_TRAY_MAP, _fake_classify, _fake_save(tmp_path))
    assert outcome == "assess"
    assert body["frame_path"].endswith("cycle_17.jpg")
    assert [e["slot"] for e in body["eggs"]] == [1, 2, 3]
    assert [e["class"] for e in body["eggs"]] == ["good", "defective", "good"]
    assert body["eggs"][1]["image_path"].endswith("cycle_17_slot2.jpg")
    assert set(body["eggs"][0]) == {"slot", "image_path", "class", "confidence", "model_name", "model_version", "inference_time_ms", "raw_result"}


def test_run_cycle_rejects_on_count_and_keeps_the_frame(tmp_path):
    frame = _frame_with({1: 81, 2: 82, 3: 83, 4: 150, 5: 150, 6: 150})
    outcome, body = lt.run_cycle({"id": 18, "weights": [58.2, 61.0]}, frame, tm.DEFAULT_TRAY_MAP, _fake_classify, _fake_save(tmp_path))
    assert outcome == "reject"
    assert body["reason"] == "occupancy_mismatch" and body["occupied_slots"] == [1, 2, 3]
    assert body["frame_path"].endswith("cycle_18.jpg")


def test_run_cycle_rejects_a_gap(tmp_path):
    frame = _frame_with({1: 81, 3: 83, 2: 150, 4: 150, 5: 150, 6: 150})
    outcome, body = lt.run_cycle({"id": 19, "weights": [58.2, 61.0]}, frame, tm.DEFAULT_TRAY_MAP, _fake_classify, _fake_save(tmp_path))
    assert outcome == "reject" and body["reason"] == "not_prefix"


def test_run_cycle_holds_when_everything_is_dark(tmp_path):
    outcome, info = lt.run_cycle({"id": 20, "weights": [58.2]}, _frame_with({}), tm.DEFAULT_TRAY_MAP, _fake_classify, _fake_save(tmp_path))
    assert outcome == "hold" and set(info["regimes"]) == {1, 2, 3, 4, 5, 6}


def test_classify_batch_is_one_predict_call():
    calls = []

    class FakeModel:
        def predict(self, batch, verbose=0):
            calls.append(batch.shape)
            return np.array([[0.1, 0.8, 0.1], [0.7, 0.2, 0.1], [0.1, 0.1, 0.8]], dtype=np.float32)

    classify = lt.classify_batch_with(FakeModel(), ["defective", "good", "not_an_egg"], {"name": "m", "version": "v"})
    crops = [np.zeros((620, 1100, 3), dtype=np.uint8)] * 3
    verdicts = classify(crops)
    assert calls == [(3, 224, 224, 3)]
    assert [v["class"] for v in verdicts] == ["good", "defective", "not_an_egg"]
    assert json.loads(verdicts[0]["raw_result"])["good"] > 0.79
    assert all(v["model_version"] == "v" for v in verdicts)


def test_save_cycle_images_writes_frame_and_crops(tmp_path):
    frame = _frame_with({1: 81})
    crops = {1: tm.crop_slot(frame, tm.DEFAULT_TRAY_MAP, 1)}
    frame_path, crop_paths = lt.save_cycle_images(frame, crops, 21, capture_dir=tmp_path)
    assert frame_path.endswith("/cycle_21.jpg") and crop_paths[1].endswith("/cycle_21_slot1.jpg")
    assert (tmp_path / frame_path.split("/")[-2] / "cycle_21_slot1.jpg").exists()
