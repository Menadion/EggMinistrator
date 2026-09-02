# Three numbers the build-first method can't produce

**Status: open, requested 2026-09-02, cut down 2026-09-02.** Measuring: **J**. Requested by M.

**The team's method is agreed and it is the right one.** Build the internals, then measure the
enclosure around them, rather than pre-cutting a pocket for every part. R's `prototype.FCStd` is the
argument for it: he reserved space for a bare ESP32 module when the team owns a **devkit**, roughly
twice the footprint. Predetermined cutouts fail exactly that way, and building first makes that
class of error impossible.

**So the per-component measuring list is dropped.** J pushed back on it and he was right. No
calipers on circuit boards, no pre-measuring the TFT, breadboard, HX711, hinge or webcam body — the
enclosure gets measured off the assembled internals.

What follows is only what building first **cannot** tell you. Three numbers. None of them need a
caliper on a board, and each one fails silently or expensively if skipped.

---

## 1. Egg width — the smallest one you will ever run

⚠️ **Needed before the tray is built, not after.** The tray is an internal, so it gets built early,
and this number decides its holes.

**Ask:** measure the **short axis** (the width, not the length) of at least 10 eggs. Record the
**smallest** you find. Note whether they were white, tinted, or both, and which PNS size bands were
in the sample.

**Why:** each tray hole has to be slightly *smaller* than the egg, so the egg seals its own aperture.
Any larger and light escapes around the egg instead of passing through it, floods the camera from
below, and the candler becomes a lightbox. Since the smallest egg has to still seal, the hole is
sized against the smallest, not the average.

Eggs lie **horizontal** in v2, so the hole seals against the egg's **side** — width is the dimension
that matters, not length.

---

## 2. The load cell's rated platform size

**Ask:** find this on the datasheet or the original listing. **It is not something to measure with a
ruler** — it is a spec of the part, not a dimension of it. The cell is the 1 kg single point bought
2026-08-14.

**Why this one cannot wait for the build:** a single-point load cell only cancels out off-centre
loading *inside its rated platform size*. Build the tray larger than that and an egg in a corner
weighs differently from the same egg in the middle.

That breaks differential weighing specifically, because the whole method depends on the **step
between readings** meaning the same thing at every position. It will not look broken. The tray will
sit properly, the numbers will look plausible, and the per-egg weights will be wrong — which then
feeds size grading, because size is derived from weight. **This is the one that cannot be caught by
assembling it and having a look.**

If the datasheet is gone, the listing will have it. Do not estimate it.

---

## 3. The webcam's minimum focus distance

**Ask:** lay a real tray of six eggs on the bench. Hold the webcam above it with a tape measure
alongside and lower it until the preview goes soft. Record two heights:

- the height where focus is **lost**,
- the height where the **six eggs just fill the frame**.

Do it at the **capture resolution the build will use**, not the preview default. `ai/capture.py`
defaults to 720p and its comment at line 228 records that high-resolution drivers *"digitally crop
at their maximum mode instead of scaling"* — so framing shifts with resolution, and a number taken
at 720p may not hold at 4K.

**Why building first doesn't answer this:** camera height is not a property of the internals. It is
the **depth of the chamber**. Assemble everything, wrap a box around it at whatever height things
happen to land, and the camera may simply not focus on the tray — and then the box gets built twice,
which is the failure `hardware/README.md` already warns about. The hinged lid makes it permanent
once cut, because the hinge fixes the camera's arc.

---

## Optional, five minutes, and J already owns capture

Not a measurement — a test that closes an open risk in `docs/pinned.md` §9.

v1's 92 training images were shot **upright, lit from below, camera at the side** — 90° to the light
path, so the camera saw scattered glow off the shell. v2 puts the camera **overhead**, looking
straight back down the light path at 180°. The *silhouette* survives that change, which is why
horizontal was the right call. The *lighting mode* may not.

**The test:** put an egg horizontal on the v1 candler, hold the webcam directly above it, shoot a
few frames — one visibly cracked egg, one good one. Compare against `ai/dataset_raw`. If the crack
still reads, the dataset transfers. If the centre blows out or the crack washes away, we have found
that now rather than after the enclosure is built.

---

## What these feed

- **1** blocks the tray, which is built early under the build-first method.
- **2** blocks the tray being *correct*, and silently rather than visibly.
- **3** blocks the enclosure height, and the hinge locks it in.

Everything else about the enclosure now comes off the assembled internals, as the team decided.
A photo of this filled in by hand is fine.
