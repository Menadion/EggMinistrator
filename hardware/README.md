# hardware/

Physical build reference for the inspection station.

> ⚠️ **The board is a classic ESP32, not an S3** (identified 2026-08-18 via `firmware/board-id/`:
> `ESP32-D0WD-V3`). This file used to say ESP32-S3 throughout. The paper says only "ESP32" and is
> correct as printed; some repo filenames still say S3 and are cosmetic. See `firmware/README.md`.

## Files

- **`bill-of-materials.md`** — parts, quantities, costs. ✅ Written; prices not yet filled.
  Split into two purchase waves on purpose (see below).
- `wiring-diagram.png` — load cell → HX711 → ESP32, and the light-sealed enclosure. *(Not created
  yet.* Committed when it is — see the `!hardware/**/*.png` exception in `.gitignore`.) **Much
  smaller than it used to be** — the webcam is a USB cable and the candler has its own power.
- Enclosure model — the 3D print deliverable. See below. *(Not created yet.)*

> The BOM here must match the hardware cost table in the capstone paper (§2.4) — keep them in sync.
> Note the components that entered scope late and are easy to forget: transillumination LEDs,
> light-sealing for the candling chamber, the load cell, and the HX711 amplifier.

## Buy in two waves

> **Updated 2026-08-07 — the descope removed the reason for this split.** The two-wave rule existed
> because the ESP32-CAM might have failed to candle through a shell, and swapping it for a USB camera
> would have changed the enclosure geometry. **Capture is now a USB webcam from the start**, so that
> risk is gone. The sequencing below is still sensible, just no longer load-bearing.

1. **Wave 1 — electronics.** Load cell, HX711, ESP32, candler. Rig them on a table, no enclosure.
   Photograph real cracked eggs and confirm the candler penetrates a **white or tinted** shell.
2. **Wave 2 — the rig.** Enclosure, blackout material, egg platform, fasteners.

**Still check before building the box:** the webcam's **minimum focus distance**. Many webcams will
not focus at close range, and that distance sets the depth of the chamber. Building the box first
means building it twice.

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

- Where the candler sits relative to egg and camera (light *behind* the egg, camera opposite). It has
  to be **fixed in position and continuously USB-powered** — the paper's "illumination remains
  constant between inspections" claim depends on it.
- How the platform holds the egg over the light **and** transfers weight to the load cell.
- How the chamber seals against ambient light while still allowing fast loading and unloading.
- Webcam-to-egg distance — set by the webcam's minimum focus distance. Measure it.

Design images go in this folder alongside the model (PNG under `hardware/` is committed; see
`.gitignore`). The exported model file belongs here too.
