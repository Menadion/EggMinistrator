# firmware/

The ESP32-S3 weight node.

> **Rewritten 2026-08-07 after the hardware descope.** This directory used to document ESP32-CAM
> *capture* firmware. The ESP32-CAM is out of the build. Image capture now happens on a **USB webcam
> attached to the laptop**, and the ESP32-S3 is repurposed from "the programmer" to **the networked
> sensor**.

## ⚠️ Not written yet

**There is no firmware in this directory.** The paper (Ver6.1.4, §2.2 and Ch4 sensing layer) states
that the ESP32-S3 *"executes its own firmware"* and transmits weight over Wi-Fi. That is a commitment
made on 2026-08-07 and it is not yet met. Until it is written, the paper describes something that
does not exist.

It is small — an HX711 library read plus an HTTP POST, realistically under a hundred lines — but it is
not zero.

## What it has to do

1. Connect to Wi-Fi.
2. Read the load cell through the HX711 (`DOUT` / `PD_SCK`, bit-banged — use a library, e.g. HX711 for
   Arduino).
3. On trigger, POST the weight reading to the local server as an HTTP request.

That is the whole job. **Inference stays on the computer** (see [`../ai/`](../ai/)) — the node is
responsible for sensing and reporting, nothing else.

## Why it must be Wi-Fi, not USB serial

Reading the HX711 over USB serial into the laptop would work identically and would be marginally
simpler. **Do not do it.** The paper's title claims *"An AI-Powered IoT System"*, and §2.2 describes a
device that operates *"rather than acting as a peripheral attached to a computer."* With capture moved
to the laptop, this node posting over Wi-Fi is the only remaining thing that makes those two claims
true. Over USB it becomes a peripheral and the cover page stops being defensible.

## Flashing

The ESP32-S3 has **native USB** — no FTDI adapter, no CP2102, no GPIO0 jumper. Plug it in.

1. Open the sketch in the **Arduino IDE** (ESP32 board support installed), select an ESP32-S3 board.
2. Set the Wi-Fi SSID/password and the server address in a local config — **do not commit real Wi-Fi
   credentials.**
3. Compile and upload.

*(The old ESP32-CAM flashing procedure — USB-to-serial adapter wired to U0T/U0R/GND/5V with GPIO0
pulled to GND — no longer applies to anything in this project.)*

## Notes

- The load cell needs **calibration** against a known mass before readings mean anything. Size class is
  assigned by comparing weight to the PNS bands in the paper's Table 11, so a calibration error becomes
  a grading error directly.
- Weight and image are joined **on the server**, against the same inspection record. The node does not
  see the image.
