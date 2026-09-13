---
name: building-from-reference
description: Use when asked to rebuild an existing structure or product in wood, to produce a cutlist, bill of materials or priced shopping list for a build, or to turn a photo, drawing, product page or CAD model into buildable lumber and sheet-goods parts.
---

# Building from a reference

A reference is not a build. A moulded panel shed, a photo of a bench, or a drawing
of a cabinet contains no studs, plates, headers or fasteners — those must be
derived. Never translate a reference's parts straight into wood, and never price
anything from memory.

## Workflow

1. **Intake** — get numbers, not impressions: envelope, opening sizes and
   positions, roof pitch, and what each part is made of. A data sheet or an
   existing CAD model beats a photo; if the only source is an image, say which
   dimensions you are guessing.
2. **Name the invariants** — which dimensions are fixed (usually the exterior
   envelope and the clear door opening) and which give (wall build-up, floor
   structure, roof build-up). State it out loud; every later conflict resolves
   against it.
3. **Translate** — for every reference material write the wood equivalent and its
   dimensional consequence. Anything Home Depot does not stock becomes a
   substitution row. Changing the diagram is expected; hiding it is not.
4. **Write the spec** — one JSON file: envelope, wall build-up, openings, roof,
   floor, substitutions, price search terms. With a CAD model,
   `scripts/woodbuild/spec_from_freecad.py` derives it; a pure-python path exists
   for photos and drawings.
5. **Run the engine** — `python3 scripts/woodbuild.py --spec S --prices P --out DIR`.
   It derives framing, panelises surfaces, nests sheets, cuts boards, builds the BOM
   and writes `budget.html` + `cutlist.csv` + `cart.csv` + `sku-qty.txt`.
6. **Verify** — every part placed, no sheet overfilled, sheet count plausible, the
   door opening still the reference's size. `spec.py` refuses to run when the
   clerestory band no longer fits under the roof build-up.
7. **Match products, then price** — see below. Read the deviations table *before*
   the totals, and report anything unpriced with its reason.

## Pricing: matching is your judgment, not a search

A programmatic description search will pick the wrong product (it has bought a
$60 anchor bolt for "2x4" and a ceiling tile for "steel roofing"). And a SKU written
into a spec rots as products are replaced. So:

```bash
# 1. what still needs a match, with candidates to read
python3 scripts/woodbuild.py --spec S --prices P --out DIR --candidates
# 2. judge, then record your decision and your reasoning
python3 scripts/woodbuild.py --spec S --prices P --out DIR \
  --set-price 2x4 1001802962 --why "2x4x8 ft SPF standard stud" --today 2026-08-01
```
The cache stores the SKU, name, url, price, `matched_on` and `why` — the durable
artifact is the decision and its justification. `resolve()` prices only entries the
agent matched; a search hit is never a price. Prefer the **best value pack** for
consumables (price per piece, not the first correct product: a 50-count box of
screws cost 5x a bulk box for the same job). Never invent a price or a pack size —
leave a class unpriced with a reason instead. Re-match anything older than 30 days
rather than trusting it.

## Hard rules

- **No invented prices, and no auto-accepted ones.** Unmatched stays `unpriced`.
- **No invented quantities.** Quantities come from nesting and cutting-stock, never
  from area ÷ sheet size.
- **Framing is derived, never copied** — see `framing-rules.md`.
- **Fixed dimensions stay fixed** unless the person you are building for agrees;
  thicker walls mean a smaller interior, and that must be stated in m²/m³.
- **Consumables come from connections and joints**, not from material length, and
  their coverage assumptions belong in the workbook.

## Reference

- `framing-rules.md` — spacings, headers, rafters, blocking, panelisation, datums
- `stock-catalogue.md` — stock classes, sizes, kerf, and what Home Depot actually stocks
- `substitutions.md` — known material translations and their consequences
