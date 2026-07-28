# docs/

Code-supporting visuals and design references. **The repo stays code-based** — `*.pdf` is gitignored,
so the capstone paper and RRL live here locally but are never pushed. Same for the team's internal
working notes (`context.md`, `gaps.md`, `recommendations.md`), which `.gitignore` also blocks.

## What gets committed

`*.png` in this folder is committed (see the `!docs/**/*.png` exception in `.gitignore`):

- `architecture-diagram.png` — the system diagram referenced by the root README. *(Not created yet.)*
- **Enclosure design images** — the sketches the 3D-printed enclosure is modelled from. Dimension
  them; an undimensioned image can't be turned into a printable model without guessing.
- Dashboard / station screenshots the README shows.

## What stays local (gitignored)

- The capstone paper PDF and `rrl.pdf`.
- `context.md` — what the project is and what it commits to. **Read this first** if you're picking
  the project up.
- `gaps.md` — ranked logical gaps in the paper.
- `recommendations.md` — what to fix, in leverage order.
- `schema-review.md` — findings on `database/schema.sql` vs the paper and the dashboard.

Those four are working notes, not deliverables. They're the honest internal read of the document,
which is exactly why they don't belong in a public repo. Share them with teammates directly rather
than committing them.

## Related

The **exported 3D model** for the enclosure (STL / STEP) belongs in
[`../hardware/`](../hardware/), not here — this folder is for images and reference, that one is the
build.
