# firmware/

The ESP32-CAM capture firmware.

- `esp32cam/` — the capture sketch: connects to Wi-Fi, captures an image on trigger, sends it to
  the processing computer.

## You need a programmer — the board has no USB port

⚠️ **The ESP32-CAM cannot be flashed on its own.** It has no USB connector and no onboard
USB-to-serial chip. You need one of:

- a **USB-to-serial adapter** (FTDI or CP2102), wired to U0T/U0R/GND/5V, with **GPIO0 pulled to GND**
  to enter flash mode, or
- an **ESP32-CAM-MB baseboard**, which the module clips into and which handles the above for you.

Cheap part, total blocker without it. It's on `hardware/bill-of-materials.md`.

## Flashing

1. Open the sketch in the **Arduino IDE** (ESP32 board support installed).
2. Set your Wi-Fi SSID/password and the computer's address in a local config — **don't commit real
   Wi-Fi credentials**.
3. Connect the programmer, pull GPIO0 to GND, reset the board.
4. Compile/verify, then upload.
5. Release GPIO0 and reset to run normally.

## Notes

- Power it from a **solid 5V supply**. The ESP32-CAM browns out on marginal power, usually showing up
  as reboots the moment the camera initialises.
- The capture is a **single candling (backlit) frame** per egg — one image, not two. The illumination
  is transillumination from behind the egg; the firmware just triggers and sends.

> The ESP32-CAM handles capture only. All AI inference runs on the computer (see [`../ai/`](../ai/)).
>
> This module is the project's **one unvalidated hardware bet** — it has to resolve internal features
> through a brown shell at low sensor sensitivity. Test that before the enclosure is built around it.
