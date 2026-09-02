import numpy as np


def test_listen_station_borrows_rather_than_copies():
    import station_common
    import listen_station
    for name in ["load_capture_settings", "setting", "load_model_and_labels", "call", "grab_current_frame", "frame_brightness"]:
        assert getattr(listen_station, name) is getattr(station_common, name), f"{name} is a copy, not an import"
    for name in ["BRIGHTNESS_MIN", "INPUT_SIZE", "POLL_SECONDS", "STALE_FRAMES_TO_DISCARD", "CAPTURE_DIR", "MODEL_DIR"]:
        assert getattr(listen_station, name) == getattr(station_common, name)
    assert station_common.BRIGHTNESS_MIN == 15.0
    assert station_common.INPUT_SIZE == (224, 224)


def test_preprocess_frame_is_224_rgb():
    import station_common
    frame = np.zeros((654, 1163, 3), dtype=np.uint8)
    frame[:, :, 0] = 200          # BGR: blue channel high
    out = station_common.preprocess_frame(frame)
    assert out.shape == (224, 224, 3) and out.dtype == np.uint8
    assert out[0, 0, 2] == 200 and out[0, 0, 0] == 0    # swapped to RGB


def test_raw_result_line_is_json_with_every_class():
    import json
    import station_common
    line = station_common.raw_result_line(["defective", "good", "not_an_egg"], np.array([0.1, 0.8, 0.1], dtype=np.float32))
    assert json.loads(line) == {"defective": 0.10000000149011612, "good": 0.800000011920929, "not_an_egg": 0.10000000149011612}


def test_classify_uses_shared_preprocessing(monkeypatch, tmp_path):
    import listen_station

    class FakeModel:
        def predict(self, batch, verbose=0):
            assert batch.shape == (1, 224, 224, 3)
            return np.array([[0.1, 0.8, 0.1]], dtype=np.float32)

    frame = np.zeros((654, 1163, 3), dtype=np.uint8)
    assessment = listen_station.classify(FakeModel(), ["defective", "good", "not_an_egg"], {"name": "m", "version": "v"}, frame, "x.jpg")
    assert assessment["class"] == "good" and assessment["image"] == "x.jpg"
    assert assessment["raw_result"] == listen_station.raw_result_line(["defective", "good", "not_an_egg"], np.array([0.1, 0.8, 0.1], dtype=np.float32))
