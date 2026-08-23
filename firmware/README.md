# firmware/

The ESP32-S3 weight node.

> **Rewritten 2026-08-07 after the hardware descope.** This directory used to document ESP32-CAM
> *capture* firmware. The ESP32-CAM is out of the build. Image capture now happens on a **USB webcam
> attached to the laptop**, and the ESP32-S3 is repurposed from "the programmer" to **the networked
> sensor**.

## Status — written, never run (2026-08-18)

**The firmware exists.** `EggMinistrator_ESP32.ino`, 535 lines. The paper's claim (Ver6.1.4, §2.2
and Ch4 sensing layer) that the ESP32-S3 *"executes its own firmware"* and transmits weight over
Wi-Fi is met **in code**. It is not yet met on a board.

- 🔴 **Never compiled, never flashed.** The sketch says so itself at line 20: *"NOT COMPILE-TESTED."*
  Nothing in this directory has run on hardware.
- ✅ **The chip is identified, and the pin map is already correct for it.** `board-id/` was run over
  USB on COM3 and the board answered:

  ```
  Chip type:          ESP32-D0WD-V3 (revision v3.1)
  Features:           Wi-Fi, BT, Dual Core + LP Core, 240MHz, Vref calibration in eFuse
  Crystal frequency:  40MHz
  MAC:                1c:69:20:a3:f8:8c
  ```

  **It is a classic ESP32, not an S3.** The can is marked only "ESP32-32X", a reseller marking rather
  than an Espressif part number, which is why it had to be asked rather than read. The sketch's pin
  map was rewritten for this chip: GPIO6-11 (SPI flash), GPIO0/2/12/15 (strapping), GPIO1/3 (UART0)
  and GPIO34-39 (input only) are all avoided, and GPIO16/17 are skipped so the same map works on a
  WROVER. See the commentary at lines 76-101 of the sketch.

  ⚠️ **The file is still named `EggMinistrator_ESP32.ino`, and several repo docs still say
  "ESP32-S3".** Cosmetic and deliberately not renamed this close to the defense. **The paper says
  only "ESP32" throughout and is correct as printed.**
- ⚠️ **`LCD_I2C_ADDRESS` is a guess.** Set to `0x27`, the usual PCF8574 backpack address, but a good
  number of these modules are `0x3F` instead. First thing to change if the screen stays blank.
- 🟡 **The load cell is calibrated, but two factors disagree.** `LOADCELL_CALIBRATION_FACTOR = 698.0`
  as of 2026-08-23, adopted from J's bench sketch (`firmware/tester/tester.ino`) so the station
  matches the board he is actually running. The previous value, **735.25**, was calibrated by J on
  2026-08-16 against the same cell. The two differ by 5.3% — about 3 g on a 60 g egg, which is
  wider than the paper's own ±2 g KPI. 698.0 wins on recency, not on re-measurement; nobody has
  re-run the procedure since the 16th. **Owed: re-calibrate once the egg holder is final, then
  delete the loser.**

## What it does

1. Connects to Wi-Fi.
2. Reads the load cell through the HX711 (`DOUT` / `PD_SCK`).
3. **Triggers on weight, not on a keypress.** Placing the egg is the button press: above
   `EGG_PRESENT_THRESHOLD_G` (20.0 g) the station wakes and shows `Egg detected. Measuring...`; below
   `EGG_REMOVED_THRESHOLD_G` (15.0 g) it resets for the next egg.
4. `POST /api/inspections` with `{ "weight_g": 58.23 }`, which opens an inspection record.
5. `GET /api/inspections/<id>/result`, polled every 500 ms, until the verdict lands.
6. Drives the LCD, LEDs and buzzer from that verdict.

**Inference stays on the computer** (see [`../ai/`](../ai/)) — the node senses and reports, nothing
else. It never sees the image.

> 🔴 **The step between 4 and 5 is not written.** Something on the laptop has to notice the new
> inspection, shoot the webcam, run `ai/inference/classify.py`, and POST the result back against that
> id. No such code exists. `ai/capture.py` is not it — that is the dataset collection tool, where a
> human presses G/D/N and the images go to folders, not to the API. This is the same hole the
> contract records as **FR-01 and FR-11 red, "missing capture code."** The board will post a weight
> and then poll forever.

## What is in here

| File | What it is |
|---|---|
| `EggMinistrator_ESP32.ino` | the node firmware, 535 lines |
| `board-id/board-id.ino` | asks the chip what silicon it actually is, because the can's marking does not say. Run this before flashing anything else |
| `secrets.h.example` | placeholder Wi-Fi credentials and device key. Copy to `secrets.h`, which is gitignored and never committed |
| `simulate_station.py` | plays both hardware roles against the **real** backend, so History fills with real rows when nothing is wired up |
| `stub_server.py` | plays the backend against the **real** board, so the LCD, LEDs and buzzer can be tested before R's routes exist |

## Why it must be Wi-Fi, not USB serial

Reading the HX711 over USB serial into the laptop would work identically and would be marginally
simpler. **Do not do it.** The paper's title claims *"An AI-Powered IoT System"*, and §2.2 describes a
device that operates *"rather than acting as a peripheral attached to a computer."* With capture moved
to the laptop, this node posting over Wi-Fi is the only remaining thing that makes those two claims
true. Over USB it becomes a peripheral and the cover page stops being defensible.

## Flashing

> ⚠️ **Corrected 2026-08-22.** This section still described an ESP32-S3 and told you to **stop if
> the chip was not an S3**. That is backwards now. `board-id/` was already run on 2026-08-18 and the
> board answered **`ESP32-D0WD-V3`, a classic ESP32**, and the sketch's pin map was then rewritten
> **for that silicon**. Following the old step 1 would have stopped the person who was holding the
> right board.

The board is a **classic ESP32**, so it reaches the host through an **onboard USB-to-serial bridge**
(CP2102 or CH340 on most dev boards), not native USB. Install that bridge's driver if the port does
not appear. No FTDI adapter and no GPIO0 jumper are needed — these boards auto-reset into the
bootloader.

1. Copy `secrets.h.example` to `secrets.h` and fill it in — **do not commit real Wi-Fi credentials.**
2. Open the sketch in the **Arduino IDE** with ESP32 board support installed, and select a plain
   **ESP32 Dev Module** board. Do **not** select an S3 variant.
3. Compile and upload. This has never been done, so budget for compile errors on the first pass.

*(Re-run `board-id/` only if the physical board is swapped for a different one. It has already
answered for the board this project owns.)*

*(The old ESP32-CAM flashing procedure — USB-to-serial adapter wired to U0T/U0R/GND/5V with GPIO0
pulled to GND — no longer applies to anything in this project.)*

## Notes

- The load cell **is calibrated** (698.0 as of 2026-08-23, superseding 735.25 — see the status
  section above; the two disagree by more than the ±2 g KPI). Size class is assigned by comparing
  weight to the PNS bands in the paper's Table 11, so a calibration error becomes a grading error
  directly — re-calibrate if the load cell, the HX711 or the egg holder ever changes.
- Weight and image are joined **on the server**, against the same inspection record. The node does not
  see the image.
