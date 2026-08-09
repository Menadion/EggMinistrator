# Bill of Materials

Parts for one EggMinistrator inspection station (prototype, single unit).

> **Rebuilt 2026-08-07 after the hardware descope.** The ESP32-CAM build is gone. Capture now runs on
> a **USB webcam attached to the laptop**; the **ESP32-S3** the team already owns is repurposed from
> "programmer" to the **networked weight node**, reading the HX711 and posting over Wi-Fi. Decided for
> time constraints ahead of the defense.
>
> ⚠️ Two things this file used to say that are **no longer true**: the ESP32-CAM is not the capture
> device, and the eggs are **white and tinted**, not brown (corrected 2026-08-03 — brown was never
> sourced). Selection notes below are updated accordingly.

**These figures must stay in sync with the paper.** Ver6.1.4 §2.4 Table 2 currently states:
subtotal **₱3,120.00**, contingency (10%) **₱312.00**, total **₱3,432.00**. Anything changed here has
to move there too, and through Table 6 and Table 15.

---

## Parts to buy

| # | Component | Spec / selection notes | Qty | Unit ₱ | Total ₱ |
|---|---|---|---|---|---|
| 1 | 1 kg single point load cell | Range suited to a single egg (~50–100 g). **Do not oversize** — a 5 kg cell wastes resolution on a 60 g object | 1 | 350.00 | 350.00 |
| 2 | HX711 load cell amplifier | Reads the load cell, standard pairing. ⚠️ Two-wire bit-banged interface (DOUT/PD_SCK) — **it cannot connect to a laptop.** The ESP32-S3 clocks it | 1 | 90.00 | 90.00 |
| 3 | Egg candler, USB rechargeable | The transillumination source. **Must be fixed in position and run on continuous USB power** — that is what makes the paper's "illumination remains constant between inspections" claim true | 1 | 180.00 ⚠️ | 180.00 |
| 4 | Egg holder / platform | Holds the egg over the light **and** transfers its weight to the load cell. Both jobs, one part — the trickiest geometry in the build | 1 | 250.00 | 250.00 |
| 5 | Jumper wires, breadboard, connectors | Consumables. Still needed for the HX711 wiring | 1 set | 250.00 | 250.00 |
| 6 | Acrylic / project enclosure | The light-sealed chamber. Candling fails if stray ambient light reaches the sensor | 1 | 2,000.00 ⚠️ | 2,000.00 |

⚠️ = rough estimate, not from a listing. **Items 3 and 6 are unverified.** Item 3's Shopee listing has
not been checked; item 6's ₱2,000 is a guess.

## Already owned — listed at ₱0, with a note

| Item | Note |
|---|---|
| USB webcam | The capture device. Replaces the ESP32-CAM |
| Laptop / desktop | Inference runs here. Also the local server and the operator display |
| ESP32-S3 development board | **The weight node.** Reads the HX711, posts weight over Wi-Fi. Has native USB, so no separate programmer is needed |
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
| **Hardware total** | **3,432.00** |

---

## Why the ESP32-S3 stays in the build

It would be easy to read the descope as "no microcontroller" and drop it. **Do not.** Two reasons:

1. **The HX711 needs one.** It has no USB. Nothing else in the parts list can clock it.
2. **It is the entire IoT claim.** The paper's title says *"An AI-Powered IoT System"* and §2.2 plus
   the Ch4 sensing layer describe a networked device that *"executes its own firmware rather than
   operating as a peripheral attached to a computer."* With the camera moved to the laptop, the
   ESP32-S3 posting weight over **Wi-Fi** is the only thing keeping that true. Wiring it over USB
   serial instead would be functionally equivalent and would break the cover page.

## Design not yet started

No enclosure design or drawing exists. Geometry still to resolve, **now simpler than the ESP32-CAM
version** because the camera is a webcam on a cable and can be positioned freely:

- Where the candler sits relative to the egg and the webcam (transillumination = light *behind* the
  egg, camera opposite).
- How the egg platform holds the egg over the light while resting on the load cell.
- How the chamber seals against ambient light while still allowing an operator to place and remove
  eggs quickly.
- Webcam-to-egg distance, set by the webcam's minimum focus distance. **Check this before building** —
  many webcams will not focus at close range, and it sets the depth of the chamber.

`wiring-diagram.png` is referenced by `hardware/README.md` and does not exist yet. It is now a much
smaller drawing: load cell → HX711 → ESP32-S3, and nothing else.

## Keep in sync

- Capstone paper Ver6.1.4 §2.4 **Table 2** — Hardware Components Cost Breakdown.
- §3.6 **Table 15** Budget Summary — the Hardware row and the contingency line both feed the total.
- `firmware/README.md` — describes the ESP32-S3 weight node.
- The paper-gaps working note (kept local, not in the repo).
