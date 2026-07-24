# firmware/

The ESP32-CAM capture firmware.

- `esp32cam/` — the capture sketch: connects to Wi-Fi, captures an image on trigger, sends it to
  the processing computer.

## Flashing

- Open the sketch in the **Arduino IDE** (ESP32 board support installed).
- Set your Wi-Fi SSID/password and the computer's address in a local config — **don't commit real
  Wi-Fi credentials**.
- Compile/verify, then upload.

> The ESP32-CAM handles capture only. All AI inference runs on the computer (see `ai/`).
