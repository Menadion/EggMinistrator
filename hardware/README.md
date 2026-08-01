# hardware/

Physical build reference for the inspection station.

## Files

- **`bill-of-materials.md`** — parts, quantities, costs. ✅ Written; prices not yet filled.
  Split into two purchase waves on purpose (see below).
- `wiring-diagram.png` — ESP32-CAM, transillumination LEDs, load cell + HX711 amplifier, and the
  light-sealed enclosure. *(Not created yet.* Committed when it is — see the `!hardware/**/*.png`
  exception in `.gitignore`.)
- Enclosure model — the 3D print deliverable. See below. *(Not created yet.)*

> The BOM here must match the hardware cost table in the capstone paper (§2.4) — keep them in sync.
> Note the components that entered scope late and are easy to forget: transillumination LEDs,
> light-sealing for the candling chamber, the load cell, and the HX711 amplifier.

## Buy in two waves

The ESP32-CAM candling through a **brown** shell is the project's one unvalidated assumption.

1. **Wave 1 — electronics.** Camera, programmer, LED, load cell, HX711, power. Rig them on a table,
   no enclosure. Photograph real cracked and fertile eggs.
2. **Wave 2 — the rig.** Enclosure, blackout material, egg platform, fasteners.

Camera-to-egg distance is unknown until Wave 1 runs, and if the ESP32-CAM fails and gets swapped for
a USB camera the enclosure geometry changes with it. **Building the box first means building it
twice.**

## Enclosure — commissioned 3D print

Decided by the team: the enclosure is **3D printed by an external shop**, not fabricated in-house.

What a print shop needs from us:

- **An STL** (most shops), or **STEP** if they accept it — STEP is parametric and survives edits
  better, STL is the safe default. **A design image is not printable** — someone has to build the
  actual 3D model from it.
- **Dimensions.** The image must be dimensioned or the modelling step is guesswork.
- **Build volume check.** Typical hobby/commercial FDM beds are around 220 × 220 × 250 mm. A candling
  chamber sized for an operator to load eggs quickly may exceed that — **ask the shop for their max
  build volume before finalising the design.** If it doesn't fit, the model has to be split into
  parts with joints, which is a design decision, not a slicing one.
- **Material and wall thickness.** The chamber must block ambient light — thin walls in translucent
  PLA leak. Ask about opaque filament or plan an internal blackout liner.

Geometry still undecided as of 2026-07-27, and none of it is a CAD problem — it's a design problem:

- Where the LED sits relative to egg and camera (light *behind* the egg, camera opposite).
- How the platform holds the egg over the light **and** transfers weight to the load cell.
- How the chamber seals against ambient light while still allowing fast loading and unloading.
- Camera-to-egg distance — blocked on Wave 1 validation.

Design images go in this folder alongside the model (PNG under `hardware/` is committed; see
`.gitignore`). The exported model file belongs here too.
