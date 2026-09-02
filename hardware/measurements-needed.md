# Measurements needed before the v2 enclosure can be drawn

**Status: open, requested 2026-09-02.** Owner of the measuring: **J**. Requested by M.

Nothing in the v2 build can be dimensioned until these land. R's `prototype.FCStd` is a
visualisation, not a spec — he calls it a rough measurement himself — and the numbers in it are
placeholders, so **do not measure "to match the CAD."** Measure the real objects.

**Measure once.** Two items below are ones the repo already records as build-before-measure traps,
where getting it wrong means building the box twice: the load cell's **rated platform size** and the
webcam's **minimum focus distance**. Neither is obvious and both are easy to skip.

Use a caliper where one is available, a steel rule otherwise. **All values in millimetres**, one
decimal place. Where a range is asked for, measure several and record the smallest and largest
actually seen, not an average.

---

## 1. Eggs

The tray's hole diameter is derived from these, and it is the single most optics-critical number in
the build: **each hole must be slightly smaller than the egg** so the egg seals its own aperture.
A hole that is too large floods the camera with stray light from below and turns the candler into a
lightbox. So the hole is sized against the **smallest** egg that will ever be run, not the average.

| # | What | Value | Notes |
|---|---|---|---|
| 1.1 | Egg length (long axis), smallest seen | | Sample at least 10 eggs |
| 1.2 | Egg length, largest seen | | |
| 1.3 | Egg width (short axis), **smallest seen** | | 🔴 The hole is sized off this one |
| 1.4 | Egg width, largest seen | | Sets minimum hole pitch |
| 1.5 | How many eggs sampled | | |
| 1.6 | Which PNS size bands were present | | Pewee / Small / Medium / Large / XL / Jumbo |
| 1.7 | White, tinted, or both | | The BOM assumes both |

⚠️ Eggs lie **horizontal** in v2 (team, 2026-09-02). So the hole seals against the egg's **side**,
and the relevant dimension is the width (1.3), not the length.

---

## 2. Load cell — including the one everybody skips

The cell is bought and calibrated (1 kg single point, arrived 2026-08-14).

| # | What | Value | Notes |
|---|---|---|---|
| 2.1 | Body length × width × height | | |
| 2.2 | **Rated platform size** | | 🔴 From the datasheet or the listing, not the ruler |
| 2.3 | Mounting hole spacing, fixed end | | Centre to centre |
| 2.4 | Mounting hole spacing, load end | | |
| 2.5 | Screw thread size | | e.g. M4, M5 |
| 2.6 | Overall height when mounted | | Spacers included |

🔴 **2.2 is the trap.** A single-point cell only compensates for off-centre load *inside its rated
platform size*. Build a tray larger than that and an egg in a corner reads differently from the same
egg in the middle — which silently destroys differential weighing, because the whole method depends
on the step between readings meaning the same thing at every position. If the datasheet is gone,
find the listing; do not guess.

Also needed for the **mechanical overload stop** (`bill-of-materials.md`): the intended ~1 mm gap
under the tray needs 2.1 and 2.6 to place the stop block.

---

## 3. Tray

The BOM currently states ~160 × 110 mm. **Confirm whether that is measured or estimated** — R drew
129 × 79, and the two do not agree.

| # | What | Value | Notes |
|---|---|---|---|
| 3.1 | Is ~160 × 110 mm measured or a guess? | | |
| 3.2 | Cintra sheet thickness available locally | | 3 mm / 5 mm / other |
| 3.3 | Cintra weight per sheet or per m² | | For the <300 g budget check |

Hole diameter and pitch are **derived** from section 1, not measured — leave them to the drawing.

Budget reminder: tray under **300 g**, hard ceiling 400 g. The risk is not the eggs (six Jumbo is
~480 g) but an operator's hand pressing down while seating one.

---

## 4. Components that have to fit inside

Measure the **actual boards**, not the chips on them, and include anything that sticks out —
USB sockets, pin headers, and the bend radius of a plugged-in cable.

| # | Part | L × W × H | Notes |
|---|---|---|---|
| 4.1 | ESP32 dev board | | 🔴 It is an **ESP32-D0WD-V3 devkit**, ~28 × 52 mm, *not* the bare 18 × 26 mm module R drew |
| 4.2 | ESP32 USB socket clearance | | How much room a plugged cable needs behind it |
| 4.3 | HX711 amplifier board | | |
| 4.4 | TFT screen — module outline | | Whole board, not the glass |
| 4.5 | TFT — active display area | | The visible part |
| 4.6 | TFT — mounting hole positions | | If it has them |
| 4.7 | Webcam body | | |
| 4.8 | Webcam — mount / clip shape | | How it will actually be fixed in the lid |
| 4.9 | USB candler (BOM item 3) | | Emitting face size matters most |
| 4.10 | LED strip width and pitch | | If strips win over the candler |
| 4.11 | Breadboard | | |
| 4.12 | RGB indicator module | | |
| 4.13 | Hinge | | Leaf length, pin-to-edge offset, open angle |

⚠️ **4.4 vs 4.5 is a real distinction** and R's file conflates them — it shows a 25 × 19 mm TFT,
which is roughly a display *area*, while a 1.8" module is around 34 × 56 mm overall. The cutout has
to be the area; the space behind has to be the module.

---

## 5. Webcam minimum focus distance — measure this before anyone cuts

| # | What | Value | Notes |
|---|---|---|---|
| 5.1 | Closest distance the webcam still holds focus | | On a tray-sized subject, not a page of text |
| 5.2 | Does the whole 2×3 tray fit in frame at that distance? | | If not, the chamber gets deeper |
| 5.3 | Distance at which the full tray *does* fill the frame | | This is the real chamber depth driver |

🔴 **This number sets the depth of the chamber**, and `hardware/README.md` already warns that
building the box first means building it twice. The hinge makes it worse, not better: a hinged lid
fixes the camera's arc, so the distance is baked into the geometry and cannot be nudged later.

**How to measure 5.1 and 5.3 without any special kit:** lay a real tray of six eggs on the bench,
hold the webcam above it with a tape measure alongside, and lower it until the preview goes soft.
Record the height where focus is lost and the height where the six eggs just fill the frame. Do it
with the same resolution setting the build will use.

⚠️ Do it at the **capture resolution**, not the preview default. `ai/capture.py` defaults to 720p
and its comment at line 228 records that high-resolution drivers *"digitally crop at their maximum
mode instead of scaling"* — so framing changes with resolution, and the number measured at 720p may
not hold at 4K.

---

## 6. Optional, but cheap and worth doing at the same time — J owns capture

Not a measurement. A five-minute test that answers an open risk in `docs/pinned.md` §9.

v1's 92 training images were shot **upright, lit from below, camera at the side** — the camera saw
scattered glow off the shell at 90° to the light. v2 puts the camera **overhead**, looking straight
back down the light path at 180°. The silhouette survives the change; the *lighting mode* may not.

**The test:** put an egg horizontal on the v1 candler, hold the webcam directly above it, and shoot
a few frames — one visibly cracked egg and one good one. Compare against the existing
`ai/dataset_raw` images. If the crack still reads, the dataset transfers. If the centre blows out or
the crack washes away, we have found that before building rather than after.

---

## When these land

Send them back however is easiest — a photo of this sheet filled in by hand is fine. They feed:

- the enclosure drawing and cut list (blocked on all of the above),
- BOM item 6, which is the largest single line and is being re-costed for cintra anyway,
- and Wave 2 purchasing, which should not be bought against the old geometry.
