# Bill of Materials

Parts for one EggMinistrator inspection station (prototype, single unit).

⚠️ **The load cell and HX711 are not optional.** The paper's title is locked and reads *"...Using
Candling Computer Vision and **Load Cell Weight Measurement**..."*, so the component it names has to
exist in the build.

Capture is a **USB webcam attached to the laptop**; the ESP32 is the networked weight node, not the
camera. The eggs are **white and tinted**, not brown — the selection notes below assume both.

**These figures must stay in sync with the paper** — §2.4 Table 2, Table 6 and §3.6 Table 15 all
carry them: subtotal ₱3,120.00, contingency ₱312.00, total ₱3,432.00.

🔴 **They are about to stop matching.** Item 6, the enclosure, is the largest single line and its
figure is an acrylic single-egg estimate. The build is now tray-sized woodwork, so re-costing it
moves all three tables and the ROI that derives from them.

---

## Parts to buy

| # | Component | Spec / selection notes | Qty | Unit ₱ | Total ₱ |
|---|---|---|---|---|---|
| 1 | 1 kg single point load cell | ✅ **Bought, arrived 2026-08-14; calibrated 2026-08-16.** Briefly descoped 2026-08-19, restored 2026-08-20 — see the header. Range suited to a single egg (~50–100 g). ⚠️ **Do not oversize** — a 5 kg cell wastes resolution on a 60 g object. ✅ Checked against Ver9.1 on 2026-08-24: the paper's budget table now reads *"1 kg Single Point Load Cell"* and the string "5 kg" does not appear anywhere in its 69 pages. The earlier note that the paper still specified 5 kg was stale | 1 | 350.00 | 350.00 |
| 2 | HX711 load cell amplifier | ✅ **Bought, arrived 2026-08-14.** Reads the load cell, standard pairing. ⚠️ Two-wire bit-banged interface (DOUT/PD_SCK) — **it cannot connect to a laptop.** The ESP32 clocks it, which is half of why the board is in the build | 1 | 90.00 | 90.00 |
| 3 | Egg candler, USB rechargeable | The transillumination source. **Must be fixed in position and run on continuous USB power** — that is what makes the paper's "illumination remains constant between inspections" claim true | 1 | 180.00 ⚠️ | 180.00 |
| 4 | Egg holder / platform | Holds the egg over the light **and transfers its weight to the load cell**. Two jobs at once, which makes this the trickiest geometry in the build. **The photo rig used for dataset collection does not need the second job**, so it can be mocked up far more crudely than the final holder | 1 | 250.00 | 250.00 |
| 5 | Jumper wires, breadboard, connectors | Consumables. The HX711 needs wiring to the ESP32 | 1 set | 250.00 | 250.00 |
| 6 | Enclosure — **woodwork**, tray-sized | The light-sealed chamber. Candling fails if stray ambient light reaches the sensor. 🔴 **This row is out of date.** The figure is an acrylic single-egg estimate; the build is now wood and has to hold a whole tray. Re-cost it from R's blueprint | 1 | 2,000.00 🔴 | 2,000.00 |

⚠️ = rough estimate, not from a listing. **Items 3 and 6 are unverified.** Item 3's Shopee listing has
not been checked; item 6's ₱2,000 is a guess. **Item 6 is the largest single line in the parts bill**,
so if any number here deserves a real listing, it is that one. Note that changing it moves Table 2,
Table 6 and Table 15 in the paper, so verify before re-typing anything.

## Already owned — listed at ₱0, with a note

| Item | Note |
|---|---|
| USB webcam | The capture device |
| Laptop / desktop | Inference runs here. Also the local server and the operator display |
| ESP32 development board | **The station node.** Reads the load cell through the HX711 and posts over Wi-Fi. ✅ **Identified 2026-08-20 as an ESP32-D0WD-V3 rev v3.1** (classic ESP32, *not* an S3) by running `firmware/board-id/` — the can is marked only "ESP32-32X". The dev board carries a USB-to-UART bridge and enumerates on COM3, so it still programs over USB with no separate programmer |
| 16x2 I²C LCD | **On the board.** The "on-station display" half of FR-15. Wired to the classic ESP32 I2C default pair, SDA 21 / SCL 22. Already in Ver9.1's Table 2 at ₱0 |
| RGB status indicator module | **On the board**, GPIO 25/26/27. The "visual indicator" half of FR-15: green good, red defective, **orange not-an-egg** (red full plus green at 80, copied from J's bench sketch). ⚠️ Table 2 calls this *"Status Indicator LEDs, 3 piece"* — it is **one module**, and the row is owed a wording fix. ₱0 either way, so no total moves |
| Passive buzzer | 🔴 **DESCOPED 2026-08-24** by the team, to get the hardware finished in time. Costs nothing in requirements terms: Ver9.1's FR-15 asks for a visual indicator and an on-station display, **not** an audible signal. The firmware keeps `beep()` behind `HAS_BUZZER false` so fitting one later is a one-line change |
| Presence sensor | ⚠️ **Spare, not currently in the design.** J picked one out on 2026-08-19 when it was going to replace the load cell. The load cell is back, and a weight threshold can detect placement on its own, so this part has no job unless triggering on weight alone proves unreliable in testing. **Keep it, do not design around it.** Part and pin were never recorded |
| Python, OpenCV, TensorFlow | Free and open source |
| Node, React, Vite | Free and open source. Replaces the earlier XAMPP/PHP entry per Decision E |
| MySQL | Free and open source |

Worth stating explicitly in the paper: **software cost is effectively zero.** That is a genuine
strength of the stack choice, not a gap in the table.

---

## Totals

| | ₱ |
|---|---|
| Subtotal | 3,120.00 |
| Contingency (10%) | 312.00 |
| **Hardware total** | **₱3,432.00** |

✅ **These match the paper as printed.** They were briefly changed to ₱2,948.00 on 2026-08-19 during
the descope and are now restored.

---

## Why the ESP32 stays in the build

Two reasons, and the second one is the one that matters.

**1. The HX711 needs a microcontroller.** It has no USB and cannot talk to a laptop directly.
Nothing else in the parts list can clock it.

**2. It is the entire IoT claim.** The paper's title says *"An AI-Powered IoT System"* and §2.2 plus
the Ch4 sensing layer describe a networked device that *"executes its own firmware rather than
operating as a peripheral attached to a computer."* With the camera on the laptop, the ESP32
reporting **over Wi-Fi** is the only thing keeping that true.

*This is also why the sensing hardware must hang off the board rather than off the laptop. A
USB-wired equivalent would be functionally identical, simpler, and would break the cover page. The
distinction is not technical, it is the difference between an IoT system and a peripheral, and the
title claims the former.*

## Enclosure — version 2, built from scratch

🔴 **The enclosure built for the 2026-08-26 defense is being scrapped, not modified.** The panel
forced per-batch candling over a conveyor, and a chamber built to hold one egg at a time cannot be
widened into one that lights and weighs a whole tray. R's blueprint is a **new design**, and it is
**woodwork**, not a 3D print (team ruling 2026-08-28). Nothing below is a modification list — it is
the set of questions the new design has to answer:

- Where the candler sits relative to the tray and the webcam (transillumination = light *behind* the
  eggs, camera opposite), and whether one source lights a whole tray evenly.
- How the tray holds the batch over the light **while resting on a single load cell**. **This is the
  hard one.** The weighing method is settled: one cell under the tray, eggs placed **one at a time**,
  and the number kept is the **step** between readings, not the running total — a total divided by
  the batch size is a mean and a light egg hides inside it. So the tray has to load in place rather
  than arrive full.
- How the chamber seals against ambient light while still letting an operator load and unload a tray
  quickly.
- Webcam-to-tray distance, set by the webcam's minimum focus distance. **Check this before
  building** — many webcams will not focus at close range, and it sets the depth of the chamber.
- ⚠️ **Camera distance and zoom must be fixed by the build, not by software.** A zoom change has
  already poisoned one dataset (`afe3496`), and a locked framing is also what a known-width platform
  needs if the mm-per-pixel size cross-check is ever fitted.

`wiring-diagram.png` is referenced by `hardware/README.md` and does not exist yet. It is a small
drawing: load cell → HX711 → ESP32, and nothing else.

## Keep in sync

- Capstone paper §2.4 **Table 2** — Hardware Components Cost Breakdown.
- §3.6 **Table 15** Budget Summary — the Hardware row and the contingency line both feed the total.
- `firmware/README.md` — describes the ESP32 weight node.
- The paper-gaps working note (kept local, not in the repo).
