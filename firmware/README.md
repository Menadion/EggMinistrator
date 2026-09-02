# firmware/

The ESP32 weight node. It senses and reports; image capture happens on a USB webcam attached to the
laptop, and inference runs there too.

## Status — flashed and demonstrated

**The firmware exists and it runs.** `EggMinistrator_ESP32.ino`, 535 lines. The paper's claim
(§2.2 and Ch4 sensing layer) that the ESP32 *"executes its own firmware"* and transmits weight over
Wi-Fi is met on a board, not just in code.

- ✅ **Flashed, and run end to end at the 2026-08-26 defense**, brought up with
  `run-eggministrator.bat` from the repo root. That launcher starts MySQL, the backend, the
  classifier listener and the dashboard in dependency order; see the header comment in the file for
  why the order is not cosmetic.
- ⚠️ **A working pipeline is not a working classifier.** The station senses, posts, classifies and
  reports, but the model it calls is still the placeholder artifact in `ai/models/`. What was
  demonstrated is the path, not the accuracy — the 85% KPI is still unmeasurable until a dataset
  exists.
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

  The repo calls it a plain "ESP32" throughout, and so does the paper. Do not reintroduce "S3" —
  it was never this board.
- ⚠️ **`LCD_I2C_ADDRESS` is a guess.** Set to `0x27`, the usual PCF8574 backpack address, but a good
  number of these modules are `0x3F` instead. First thing to change if the screen stays blank.
- 🟡 **The load cell is calibrated, but two factors disagree.** `LOADCELL_CALIBRATION_FACTOR = 698.0`
  as of 2026-08-23, adopted from J's bench sketch (`firmware/tester/tester.ino`) so the station
  matches the board he is actually running. The previous value, **735.25**, was calibrated by J on
  2026-08-16 against the same cell. The two differ by 5.3% — about 3 g on a 60 g egg. 698.0 wins
  on recency, not on re-measurement; nobody has re-run the procedure since the 16th.
  **Owed: re-calibrate once the egg holder is final, then delete the loser.**

  ✅ **The tolerance is 1 g, settled 2026-08-24.** It was disputed from 2026-08-23: `CONTRACT.md`
  l.79 said **±2 g** while the paper's Table 9 says **"Weight measurement error — Within 1 grams of
  a reference scale."** The paper is what gets graded, so the repo moved to match it and the paper
  was left untouched. **Against 1 g the 3 g calibration gap is three times over, not 1.5×** — so
  the station is currently outside tolerance, and re-calibrating with the final holder fitted is
  the thing that fixes it.

  ⚠️ **Tare is the other half of holding 1 g, and it is not addressed in code.** `tare(20)` runs
  once in `setup()` and there is no re-tare anywhere. So whatever sits on the plate at power-up
  becomes zero for the entire session, and the HX711's zero drifts with temperature over a long
  one. The operational fix, not a firmware change: **power the station up with the holder already
  fitted and the plate empty, and reset it if the session runs long.**

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

**The step between 4 and 5 is `ai/listen_station.py`.** It notices the new inspection, shoots the
webcam, runs the classifier and POSTs the verdict back against that id. `run-eggministrator.bat`
starts it as step 4, passing the device key out of `backend/.env` and the zoom out of
`ai/capture_settings.json` so the listener crops the way the dataset was shot.

Do not confuse it with `ai/capture.py`, which is the dataset collection tool — a human presses G/D/N
and the images go to folders, not to the API. Run the launcher with `--no-listener` to free the
webcam for it.

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

## Owed for v2 — the tray loop (2026-09-02)

The 2026-09-01 blueprint (`docs/pinned.md` §9) puts a 2×3 tray on the load cell and asks for six
weights out of one cell by differential weighing. The fan-out spec
(`docs/superpowers/specs/2026-09-02-software-fanout-design.md`, D2 and l.129) fixes the board's
contract at **one POST at lid-close with the weights in slot order** and says "the board's prompt
flow guarantees the order." Everything below is what that sentence assumes and the fan-out spec
deliberately does not cover. It is firmware scope.

**Capacity, for the record.** Six Jumbo eggs are ~480 g worst case. The 1 kg cell handles that with
the tray on top as long as the tray stays **under ~300 g** (hard ceiling 400 g) — see
`hardware/bill-of-materials.md`. Resolution is not the issue; the tare and the transients are.

- 🔴 **Replace the fixed settle delay with a stability gate.** `settledWeightGrams()` waits 800 ms
  and averages 20 readings. That smooths an egg's bounce but cannot tell whether the load is still
  changing — a hand resting on the tray for the whole window is averaged in and sent. v2 must
  **keep reading until the last ~10 samples agree within ~1 g for ~500 ms**, and only then take the
  step. This is what every kitchen scale does; there is nothing exotic in it.
- 🔴 **Bound every step.** An egg is 40–85 g. A step **over ~100 g** is a hand, two eggs or a
  dropped egg; a **negative step** is an egg lifted off. Neither is a weight — prompt the operator
  to re-seat and wait for the gate again. Do not record it, do not advance the slot.
- 🔴 **Tare against the empty tray, not the bare plate.** `tare(20)` runs once in `setup()`. For v2
  the zero is the empty tray in place, and the loop should re-tare at the start of every cycle
  (tray empty, lid open) so HX711 zero drift over a long session does not walk into the first
  step. This retires the "power up with the holder fitted" workaround in the status section.
- 🔴 **`total_g` is a settled reading too.** At lid-close the board sends the total alongside the
  six steps; the server checks `sum(weights)` against it (±3 g). Take the total through the same
  gate after the lid closes — a hand cannot be inside a closed lid, so a mismatch there means a
  step was wrong, which is exactly what the check is for.
- ⚠️ **Overload is not a firmware problem.** A hard press past ~1.2 kg bends the cell and the
  calibration is gone; no reading shows it. The fix is a mechanical overload stop under the tray
  — logged as an enclosure question in `hardware/bill-of-materials.md`.
- 🔴 **Unloading is a state, and weight is ignored in it.** v1 already does this for one egg:
  after the result, `waitForEggRemoval()` ignores the cell until the reading drops under
  `EGG_REMOVED_THRESHOLD_G` (or 60 s pass), then re-arms. v2 needs the same thing sized for a
  tray. The loop is a state machine, and the cell is only *listened to* in one state:
  **LOADING** (empty tray tared, lid open, count steps) → **LID CLOSED** (settle, take `total_g`,
  POST, poll `/result`; weight ignored) → **SHOW RESULT** (TFT/RGB/buzzer) → **UNLOADING** (lid
  open, weight ignored until the reading returns to the empty-tray zero within ~5 g, bounded by a
  timeout as v1) → **re-tare** → LOADING. Make the exit from UNLOADING **weight-based, not a fixed
  grace period** — inspectors unload at different speeds, and "back to zero" is the only signal
  that means "tray empty". A lid-close during UNLOADING must not mint a cycle; only LOADING with
  at least one step may. (M raised the unloading gap on 2026-09-02 while reviewing the fan-out
  spec, which leaves the whole board loop to this track — §7.)
- Re-calibrate with the final tray fitted (already owed above). The factor describes the whole
  assembly, and the tray is a new assembly.

## Notes

- The load cell **is calibrated** (698.0 as of 2026-08-23, superseding 735.25 — see the status
  section above; the two disagree by three times the 1 g KPI). Size class is assigned by comparing
  weight to the PNS bands in the paper's Table 11, so a calibration error becomes a grading error
  directly — re-calibrate if the load cell, the HX711 or the egg holder ever changes.
- Weight and image are joined **on the server**, against the same inspection record. The node does not
  see the image.
