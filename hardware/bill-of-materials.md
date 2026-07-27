# Bill of Materials

Parts for one EggMinistrator inspection station (prototype, single unit).

**Status: prices and quantities NOT yet filled.** Get real local quotes — this table has to match the
hardware cost table in the capstone paper (§2.4, p.13, currently an empty caption), and guessed
figures in a submitted budget are the thing a panel checks first.

> **Buy in two waves.** The ESP32-CAM candling through a *brown* shell is the project's one
> unvalidated assumption. Buy the electronics first, rig them on a table, and photograph real cracked
> and fertile eggs. Only size and order the enclosure once you know which camera survived — if the
> ESP32-CAM fails and you swap to a USB camera, the enclosure geometry changes with it. Building the
> box first means building it twice.

---

## Wave 1 — electronics (buy now, validate before Wave 2)

| # | Component | Spec / selection notes | Qty | Unit ₱ | Total ₱ |
|---|---|---|---|---|---|
| 1 | ESP32-CAM module | ~2MP OV2640. The capture device. **Risk item** — must resolve internal features through a brown shell | | | |
| 2 | **USB-to-serial programmer** (FTDI / CP2102) **or** ESP32-CAM-MB baseboard | ⚠️ **Required, easy to forget.** The ESP32-CAM has **no USB port** — without this the firmware cannot be flashed at all | | | |
| 3 | Transillumination LED source | Must penetrate a **brown** eggshell. Brightness and beam concentration are the whole ballgame — a generic strip will not do. High-power white LED or dedicated candling lamp | | | |
| 4 | LED driver / current-limiting resistors | Depends on the LED chosen in #3 | | | |
| 5 | Load cell | Range suited to a single egg (~50–100 g). **Do not oversize** — a 5 kg cell wastes resolution on a 60 g object | | | |
| 6 | HX711 load cell amplifier | Reads the load cell, standard pairing | | | |
| 7 | 5V regulated power supply | ESP32-CAM is brownout-prone on weak supplies — do not power it from a marginal source | | | |
| 8 | Jumper wires, perfboard / breadboard | Consumables | | | |

## Wave 2 — the rig (order after Wave 1 validates)

| # | Component | Spec / selection notes | Qty | Unit ₱ | Total ₱ |
|---|---|---|---|---|---|
| 9 | Enclosure / light-sealed chamber | Houses camera, egg, and light. **The outsourcing candidate** — wood, acrylic, 3D print, or PVC | | | |
| 10 | Blackout material | Foam, felt, or black acrylic. Candling fails if stray ambient light reaches the sensor | | | |
| 11 | Egg platform | Holds the egg over the light source **and** transfers its weight to the load cell. Both jobs, one part — the trickiest piece of geometry in the build | | | |
| 12 | Fasteners, mounts, brackets | | | | |

## Already owned — list at ₱0, with a note

| Item | Note |
|---|---|
| Laptop / desktop | Inference runs here, not on the ESP32 |
| Python, OpenCV, TensorFlow | Free and open source |
| XAMPP, MySQL, PHP | Free and open source |

Worth stating explicitly in the paper: **software cost is effectively zero.** That is a genuine
strength of the stack choice, not a gap in the table.

---

## Totals

| | ₱ |
|---|---|
| Wave 1 subtotal | |
| Wave 2 subtotal | |
| **Hardware subtotal** | |
| **Contingency (%)** | ⚠️ The paper's 10% contingency currently covers **labor only**. Hardware is the flagged procurement risk and carries brand-new component classes — it needs its own buffer |
| **Hardware total** | |

---

## Design not yet started

No enclosure design or drawing exists yet as of 2026-07-27. Geometry that has to be resolved before
fabrication:

- Where the light sits relative to the egg and the camera (transillumination = light *behind* the egg,
  camera opposite).
- How the egg platform holds the egg over the light while resting on the load cell.
- How the chamber seals against ambient light while still allowing an operator to place and remove
  eggs quickly.
- Camera-to-egg distance, set by whatever focal behavior the module actually has.

`wiring-diagram.png` is referenced by `hardware/README.md` and does not exist yet either.

## Keep in sync

- Capstone paper §2.4 (p.13) — "Table X. Hardware Components Cost Breakdown," currently empty.
- §3.6 Budget Summary (p.32) — currently an empty heading.
- `docs/gaps.md` gap 3 (blank cost tables) and gap 17 (contingency covers labor only).
