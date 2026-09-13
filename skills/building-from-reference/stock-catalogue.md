# Stock catalogue

The classes `woodbuild/stock.py` defines, and what Home Depot Canada actually
carries. Sizes are millimetres; the names are imperial because that is what the
store sells and what a builder asks for at the saw.

## Sheet goods

| class | size | thick | grain | category |
|---|---|---|---|---|
| `osb_7_16` | 1219 × 2438 | 11 | – | sheets |
| `plywood_tg_18` | 1219 × 2438 | 18 | deck | sheets |
| `plywood_ext_18` | 1219 × 2438 | 18 | face | sheets |
| `smartside_grooved` | 1219 × 2438 | 11 | groove | sheets |
| `polycarbonate_6` | 610 × 1220 | 6 | – | glazing |

## Boards

| class | section | sale lengths | category |
|---|---|---|---|
| `2x4` | 38 × 89 | 8 / 10 / 12 / 16 ft | lumber |
| `2x6` | 38 × 140 | 8 / 10 / 12 / 16 ft | lumber |
| `2x8` | 38 × 184 | 8 / 10 / 12 / 16 ft | lumber |
| `pt_2x4` | 38 × 89 | 8 / 10 / 12 / 16 ft | lumber |
| `pt_4x4` | 89 × 89 | 8 / 10 / 12 ft | base |

## Consumables

Screws, nails, adhesive, sealant, hinges, hasp, louvre, steel roofing and pad
material are not stock classes: `bom.consumables()` invents their keys and emits
**physical amounts** (pieces, ml). Their prices are keyed the same way in the spec's
`pricing.search` map.

## Optimiser constants

- **Kerf 3.0 mm** between adjacent parts and at board cut ends.
- **Offcuts ≥ 300 mm** are reported as reusable; smaller remainders are waste.
- Sheet nesting is shelf packing, decreasing height, with **grain-locked parts never
  rotated** (they are reported unplaced rather than rotated). Board choice minimises
  cost, then waste, then the number of boards, then the stock length — where waste
  counts kerfs *actually cut* (`parts − boards`, not `boards − 1`).

## Adding a class

Add geometry to `SHEETS` or `BOARDS` **and** a category to `CATEGORIES`, then a test
in `tests/test_stock.py` (`test_every_class_has_a_category` will catch a miss).
A class with no category or no size fails at import time, not at build time.

## What the store does not have (learned the hard way)

- **No ground-contact rated 2x4 pressure-treated lumber.** The ground-contact range
  is 4x4 / 4x6 / 5x5 / 6x6 posts only; every 2x4 PT board is "Above Ground Use
  Only". Design so that only skids need ground contact — joists on skids and a sole
  plate on a deck are above grade, which makes above-ground PT correct there. See
  `substitutions.md`.
- **Bulk packs only pay off at the right size.** Structural screws exist as 50-count
  (~$0.48/pc), 850-count (~$0.13/pc) and 2000-count; the per-piece price varies ~4x
  for the same screw.
- **Price availability is per SKU, not per product line.** Sibling roof panels from
  the same manufacturer can differ: one has a store price, another returns `null`.
  An unpriced line is the honest outcome.
- **Search terms decide everything.** `2x4x8 SPF stud` returns Power-Stud *anchor
  bolts*; `corrugated steel roof panel` returns ceiling tiles. Lead with the
  material and the dimension, drop adjectives ("corrugated", "heavy duty"), and try
  a trade name — the Canadian pressure-treated brand is **MicroPro Sienna**.
