import json
import urllib.error
import urllib.request

KEY = "replace-me"   # stub_server.DEVICE_KEY


def call(base, method, path, payload=None, key=KEY):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + path, data=data, method=method)
    request.add_header("X-Device-Key", key)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def egg(slot, cls="good"):
    return {"slot": slot, "image_path": f"ai/captures/x/cycle_1_slot{slot}.jpg", "class": cls, "confidence": 0.9,
            "model_name": "candling-classifier", "model_version": "0.3.0+test", "inference_time_ms": 40,
            "raw_result": json.dumps({"good": 0.9, "defective": 0.05, "not_an_egg": 0.05})}


def test_v1_routes_still_answer(stub):
    status, body = call(stub, "POST", "/api/inspections", {"weight_g": 58.2})
    assert status == 201 and body["id"] == 1
    status, body = call(stub, "GET", "/api/inspections/pending")
    assert status == 200 and body["id"] == 1


def test_cycle_happy_path(stub):
    assert call(stub, "GET", "/api/cycles/pending")[0] == 404
    status, minted = call(stub, "POST", "/api/cycles", {"station_name": "Bench", "weights": [58.2, 61.0], "total_g": 119.2})
    assert status == 201 and minted["status"] == "pending"
    cycle_id = minted["id"]
    status, pending = call(stub, "GET", "/api/cycles/pending")
    assert status == 200 and pending["id"] == cycle_id and pending["weights"] == [58.2, 61.0]
    assert call(stub, "GET", f"/api/cycles/{cycle_id}/result")[1] == {"status": "pending"}
    status, saved = call(stub, "POST", f"/api/cycles/{cycle_id}/assessment", {"frame_path": "ai/captures/x/cycle_1.jpg", "eggs": [egg(1), egg(2, "defective")]})
    assert status == 201 and [e["slot"] for e in saved["inspections"]] == [1, 2]
    status, result = call(stub, "GET", f"/api/cycles/{cycle_id}/result")
    assert result["status"] == "done" and result["any_defective"] is True
    assert result["eggs"][1] == {"slot": 2, "label": "defective", "disposition": "rejected", "size": "Large"}
    assert call(stub, "GET", "/api/cycles/pending")[0] == 404


def test_cycle_sum_mismatch_and_reject(stub):
    status, bad = call(stub, "POST", "/api/cycles", {"weights": [58.2, 61.0], "total_g": 140})
    assert status == 201 and bad["status"] == "rejected"
    assert call(stub, "GET", f"/api/cycles/{bad['id']}/result")[1] == {"status": "rejected", "reason": "weights_sum_mismatch"}
    status, ok = call(stub, "POST", "/api/cycles", {"weights": [58.2], "total_g": 58.2})
    status, rejected = call(stub, "POST", f"/api/cycles/{ok['id']}/reject", {"reason": "not_prefix", "detail": "slot 1 empty", "occupied_slots": [2]})
    assert status == 200 and rejected["reason"] == "not_prefix"
    assert call(stub, "GET", f"/api/cycles/{ok['id']}/result")[1] == {"status": "rejected", "reason": "not_prefix"}
    assert call(stub, "POST", f"/api/cycles/{ok['id']}/assessment", {"frame_path": "x", "eggs": [egg(1)]})[0] == 409
    assert call(stub, "POST", "/api/cycles", {"weights": [], "total_g": 0})[0] == 400
    assert call(stub, "GET", "/api/cycles/pending", key="wrong")[0] == 401
