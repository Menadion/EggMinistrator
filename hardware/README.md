# hardware/

Physical build reference for the inspection station.

Which ESP32 this is, and why it matters to the pin map, is in `firmware/README.md`.

## Files

- **`bill-of-materials.md`** — parts, quantities, costs. 🔴 The enclosure line needs re-costing
  against the version 2 build; everything else is bought and priced.
- `wiring-diagram.png` — load cell → HX711 → ESP32, and the light-sealed enclosure. *(Not created
  yet.* Committed when it is — see the `!hardware/**/*.png` exception in `.gitignore`.)
- Enclosure blueprint — per-batch candling, **woodwork, not a 3D print** (team ruling 2026-08-28).
  *(Not created yet.)*

**The BOM here must match the hardware cost table in the capstone paper (§2.4) — keep them in sync.**
The components that entered scope late and are easy to forget: transillumination LEDs, light-sealing
for the candling chamber, the load cell, and the HX711 amplifier.

## Buy in two waves

1. ✅ **Wave 1 — electronics.** Load cell, HX711, ESP32, candler. All bought and arrived.
2. 🔴 **Wave 2 — the rig.** Enclosure, blackout material, tray and platform, fasteners. **Blocked on
   R's blueprint** — the version 1 rig is being scrapped, so nothing here should be bought against
   the old geometry.

**Still check before building the box:** the webcam's **minimum focus distance**. Many webcams will
not focus at close range, and that distance sets the depth of the chamber. Building the box first
means building it twice.

## Enclosure — version 2, woodwork, built from scratch

🔴 **The enclosure built for the 2026-08-26 defense is being scrapped, not modified.** The panel
forced per-batch candling over a conveyor, and a chamber sized for one egg cannot be widened into
one that lights and weighs a whole tray. R is drawing a **new design**.

Two rulings supersede everything that used to be in this section:

- **It is woodwork, not a 3D print** (team ruling 2026-08-28). The commissioned-print route — STL
  or STEP to an external shop, build-volume limits, opaque filament — is gone with it.
- **It is per-batch** (panel ruling 2026-08-26). One tray, one candling pass, one weighing.

The geometry questions the new design has to answer are listed under "Enclosure — version 2" in
[`bill-of-materials.md`](bill-of-materials.md), together with the weighing method that constrains
them.

Drawings go in this folder — PNG under `hardware/` is committed, see `.gitignore`.
