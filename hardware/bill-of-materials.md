# Bill of Materials

Parts for one EggMinistrator inspection station (prototype, single unit).

> ✅ **The 2026-08-19 weight descope was REVERSED on 2026-08-20. The load cell and HX711 are back in
> the build.** Disregard any note elsewhere in the repo that still says they are out.
>
> **Why it reversed.** The adviser declined the title change. The title reads *"...Using Candling
> Computer Vision and **Load Cell Weight Measurement**..."* and it is locked, so the component it
> names has to exist. Two further rulings the same morning made restoring it cheap: the defense
> requires **physical hardware** and a simulator will not be accepted, so the team is at the bench
> either way; and scope changes **do not need to be written into the paper**, so neither the descope
> nor its reversal has to be explained to anyone.
>
> **Nothing was lost.** Both parts arrived 2026-08-14 and are on the shelf, and no size-grading code
> was ever deleted. This file is back to matching the paper's Table 2 exactly.

> **Rebuilt 2026-08-07 after the hardware descope.** The ESP32-CAM build is gone. Capture now runs on
> a **USB webcam attached to the laptop**; the **ESP32-S3** the team already owns is repurposed from
> "programmer" to the **networked station node**. Decided for time constraints ahead of the defense.
>
> ⚠️ Two things this file used to say that are **no longer true**: the ESP32-CAM is not the capture
> device, and the eggs are **white and tinted**, not brown (corrected 2026-08-03 — brown was never
> sourced). Selection notes below are updated accordingly.

**These figures must stay in sync with the paper.** ✅ **As of 2026-08-20 they do.** Ver7.1.3 §2.4
Table 2 prints subtotal ₱3,120.00, contingency ₱312.00, total ₱3,432.00, and so does this file. Keep
it that way: Table 2, Table 6 and §3.6 Table 15 all carry these numbers.

---

## Parts to buy

| # | Component | Spec / selection notes | Qty | Unit ₱ | Total ₱ |
|---|---|---|---|---|---|
| 1 | 1 kg single point load cell | ✅ **Bought, arrived 2026-08-14; calibrated 2026-08-16.** Briefly descoped 2026-08-19, restored 2026-08-20 — see the header. Range suited to a single egg (~50–100 g). ⚠️ **Do not oversize** — a 5 kg cell wastes resolution on a 60 g object. ✅ Checked against Ver9.1 on 2026-08-24: the paper's budget table now reads *"1 kg Single Point Load Cell"* and the string "5 kg" does not appear anywhere in its 69 pages. The earlier note that the paper still specified 5 kg was stale | 1 | 350.00 | 350.00 |
| 2 | HX711 load cell amplifier | ✅ **Bought, arrived 2026-08-14.** Reads the load cell, standard pairing. ⚠️ Two-wire bit-banged interface (DOUT/PD_SCK) — **it cannot connect to a laptop.** The ESP32-S3 clocks it, which is half of why the board is in the build | 1 | 90.00 | 90.00 |
| 3 | Egg candler, USB rechargeable | The transillumination source. **Must be fixed in position and run on continuous USB power** — that is what makes the paper's "illumination remains constant between inspections" claim true | 1 | 180.00 ⚠️ | 180.00 |
| 4 | Egg holder / platform | Holds the egg over the light **and transfers its weight to the load cell**. Two jobs at once, which makes this the trickiest geometry in the build. **The photo rig used for dataset collection does not need the second job**, so it can be mocked up far more crudely than the final holder | 1 | 250.00 | 250.00 |
| 5 | Jumper wires, breadboard, connectors | Consumables. The HX711 needs wiring to the ESP32-S3 | 1 set | 250.00 | 250.00 |
| 6 | Acrylic / project enclosure | The light-sealed chamber. Candling fails if stray ambient light reaches the sensor | 1 | 2,000.00 ⚠️ | 2,000.00 |

⚠️ = rough estimate, not from a listing. **Items 3 and 6 are unverified.** Item 3's Shopee listing has
not been checked; item 6's ₱2,000 is a guess. **Item 6 is the largest single line in the parts bill**,
so if any number here deserves a real listing, it is that one. Note that changing it moves Table 2,
Table 6 and Table 15 in the paper, so verify before re-typing anything.

## Already owned — listed at ₱0, with a note

| Item | Note |
|---|---|
| USB webcam | The capture device. Replaces the ESP32-CAM |
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

## Why the ESP32-S3 stays in the build

Two reasons, and the second one is the one that matters.

**1. The HX711 needs a microcontroller.** It has no USB and cannot talk to a laptop directly.
Nothing else in the parts list can clock it.

**2. It is the entire IoT claim.** The paper's title says *"An AI-Powered IoT System"* and §2.2 plus
the Ch4 sensing layer describe a networked device that *"executes its own firmware rather than
operating as a peripheral attached to a computer."* With the camera on the laptop, the ESP32-S3
reporting **over Wi-Fi** is the only thing keeping that true.

*This is also why the sensing hardware must hang off the board rather than off the laptop. A
USB-wired equivalent would be functionally identical, simpler, and would break the cover page. The
distinction is not technical, it is the difference between an IoT system and a peripheral, and the
title claims the former.*

## Design not yet started

No enclosure design or drawing exists. Geometry still to resolve, **simpler than the ESP32-CAM
version** because the camera is a webcam on a cable and can be positioned freely:

- Where the candler sits relative to the egg and the webcam (transillumination = light *behind* the
  egg, camera opposite).
- How the egg platform holds the egg over the light while resting on the load cell. **This is the
  hard one** and it is now on the critical path, because the defense requires working hardware.
- How the chamber seals against ambient light while still allowing an operator to place and remove
  eggs quickly.
- Webcam-to-egg distance, set by the webcam's minimum focus distance. **Check this before building** —
  many webcams will not focus at close range, and it sets the depth of the chamber.

`wiring-diagram.png` is referenced by `hardware/README.md` and does not exist yet. It is a small
drawing: load cell → HX711 → ESP32-S3, and nothing else.

## Keep in sync

- Capstone paper Ver7.1.3 §2.4 **Table 2** — Hardware Components Cost Breakdown.
- §3.6 **Table 15** Budget Summary — the Hardware row and the contingency line both feed the total.
- `firmware/README.md` — describes the ESP32-S3 weight node.
- The paper-gaps working note (kept local, not in the repo).
