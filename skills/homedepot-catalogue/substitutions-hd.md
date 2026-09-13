# Store substitutions

The store-level counterpart to `building-from-reference/reference/substitutions.md`.
That file holds the general translation rules; this one holds only the material
lessons this store forces that are not already covered by `stock-availability.md`.
Add a lesson when a build teaches a general one, but never write a build's SKU,
product name or dimensions into it — a build's own substitutions are rows in its
`spec.json`, re-derivable from that build and nothing else.

## Where stock forces a redesign

- **No ground-contact pressure-treated 2x4 exists** (see `stock-availability.md`
  for the range the store does carry). Every 2x4 PT board is above-ground only.
  The store-level answer is not a substituted board and a hope: design the detail
  so only skids — ground-contact posts laid down — touch the ground, and keep the
  joists and sole plate above grade, where above-ground PT is correct. Write the
  reasoning into the build's substitution row so the redesign is visible.
- **Prefer a redesign over a silent substitution.** When the ideal material is
  unavailable, change the detail so it is not needed rather than buying the nearest
  product and assuming it will do. The ground-contact case above is the model:
  moving the floor detail removed the need for the unavailable board.

## Dimensional consequences of buying stock

- **Grooved-siding groove pitch is the supplier's, not the reference's.** A
  reference that promises a plank pitch cannot be matched exactly with a stock
  panel; the pitch becomes cosmetic. It does not move anything in the drawing, so
  it is a substitution without a layout change — unlike a change in wall thickness,
  which does.
- **A moulded reference part has no stock thickness.** A formed panel or post
  carries a wall thickness the lumber yard does not sell; the stock build-up that
  replaces it is thicker or thinner, and the difference flows into the interior
  clear dimensions. Carry that consequence into the build's substitution row
  instead of recording the reference dimension as met.
