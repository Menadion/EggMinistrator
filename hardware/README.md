# hardware/

Physical build reference for the inspection station.

Which ESP32 this is, and why it matters to the pin map, is in `firmware/README.md`.

## Files

- **`bill-of-materials.md`** — parts, quantities, costs. 🔴 The enclosure line needs re-costing
  against the version 2 build; everything else is bought and priced.
- `wiring-diagram.png` — load cell → HX711 → ESP32, and the light-sealed enclosure. *(Not created
  yet.* Committed when it is — see the `!hardware/**/*.png` exception in `.gitignore`.)
- Enclosure blueprint — per-batch candling, **cintra, cut in-house** (team, 2026-09-02; the
  woodworker route was deferred, which is what retired the 2026-08-28 "woodwork" ruling); not a
  3D print either way. 🔴 **Still not created.** M's
  hand-drawn original of 2026-09-01 has never been photographed, and `docs/pinned.md` §9 remains
  its only written record — in a folder this repo ignores, so the team cannot read it either.
  ⚠️ **Authorship unverified; M believes R drew it, so ask R for the drawing.** R has a FreeCAD visualisation of it (`prototype.FCStd`, reviewed
  2026-09-02) which he describes as a rough measurement, **not a spec** — do not cut against it.
- [`measurements-needed.md`](measurements-needed.md) — 🔴 **open, requested 2026-09-02,
  cut down the same day.** Three numbers the build-first method cannot produce: the smallest egg's
  width, the load cell's **rated platform size**, and the webcam's **minimum focus distance**. The
  per-component measuring list was dropped — the team builds the internals first and measures the
  enclosure around them, so parts are not pre-measured for cutouts.

**The BOM here must match the hardware cost table in the capstone paper (§2.4) — keep them in sync.**
The components that entered scope late and are easy to forget: transillumination LEDs, light-sealing
for the candling chamber, the load cell, and the HX711 amplifier.

## Buy in two waves

1. ✅ **Wave 1 — electronics.** Load cell, HX711, ESP32, candler. All bought and arrived.
2. 🔴 **Wave 2 — the rig.** Enclosure, blackout material, tray and platform, fasteners, **lid hinge
   and lid-close switch**. **Blocked on the internals** (team method, 2026-09-02) — the enclosure is
   measured off the assembled internals rather than cut to a drawing, so the box is sized last.
   Three inputs still gate it, and they are in [`measurements-needed.md`](measurements-needed.md):
   egg width gates the **tray**, which is built early; the load cell's rated platform size gates
   whether that tray weighs **correctly**; and the webcam's focus distance gates the chamber
   **height**, which the hinge then locks in. The version 1 rig is being scrapped, so nothing here
   should be bought against the old geometry.

**Still check before building the box:** the webcam's **minimum focus distance**. Many webcams will
not focus at close range, and that distance sets the depth of the chamber. Building the box first
means building it twice.

## Enclosure — version 2, cintra, built from scratch

🔴 **The enclosure built for the 2026-08-26 defense is being scrapped, not modified.** The panel
forced per-batch candling over a conveyor, and a chamber sized for one egg cannot be widened into
one that lights and weighs a whole tray. The **new design was hand-drawn on 2026-09-01**, and R
has since visualised it in FreeCAD, which is not the same thing as speccing it.

⚠️ **Who drew it is unverified.** §9's wording, *"hand-drawn on paper and described verbally by M"*, does not say who held the pen. M believes **R drew it and M relayed it verbally**, but says so with a hedge, and an earlier pass through these files asserted the opposite. **Do not restate either version as settled** — it is resolved only when the drawing itself surfaces. Practical consequence: **ask R for the drawing.**

Rulings that supersede everything that used to be in this section:

- **It is cintra, cut in-house by R, J and D** (team, 2026-09-02). The **woodworker was
  deferred**, which is what retired the 2026-08-28 "woodwork" ruling — wood lost with the
  outsourced build it assumed, not on its merits. Every commissioned route is now gone: no external
  woodworker, and no STL or STEP to a print shop either.
- **It is per-batch** (panel ruling 2026-08-26). One tray, one candling pass, one weighing.
- **Eggs lie horizontal** (team, 2026-09-02) and **the lid is hinged** (team, 2026-09-02). The
  hinge fixes the camera's arc, so it sets camera-to-tray distance and has to close repeatably.

The geometry questions the new design has to answer are listed under "Enclosure — version 2" in
[`bill-of-materials.md`](bill-of-materials.md), together with the weighing method that constrains
them.

Drawings go in this folder — PNG under `hardware/` is committed, see `.gitignore`.
