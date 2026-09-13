# Rulings addendum — wood-build plan

**This file is authoritative over the plan's task text where they disagree.** The
plan (`2026-09-12-wood-build-from-reference.md`) is the historical argument and its
Task 1–10 code blocks are mostly still accurate; everything below was decided while
executing it, and Tasks 11b–11e do not appear in the plan at all. The full narrative
and per-task log live in the SDD ledger
(`~/.pi/agent/.superpowers/sdd/2026-09-12-wood-build-from-reference/progress.md`).

## Tasks the plan does not contain

| task | what it added | commit |
|---|---|---|
| 11b | Agent-matched pricing: `resolve` prices only `matched_by == "agent"` entries; a search hit is a candidate, never a price; `candidates()`, `needs_match()` (30 d), `set_price()`, `put_matched()`; CLI `--candidates` and `--set-price CLASS SKU --why`; workbook provenance cells | `f052ce0` |
| 11c | The matching itself (agent judgment): 19/19 classes matched with written reasons; spec queries rewritten; ground-contact substitution row | cache in `~/freecad/keter_pent97_build` |
| 11d | Consumables as physical amounts (pieces/ml) converted through the matched pack size; named coverage constants; `CONSUMABLE_OVERBUY` printed in the workbook | `c93bf7c` |
| 11e | Framing screws derived from **connections** (3 per board end × 2 ends × parts), not board length; consumables matched on **price per piece** | `a89ee6f` |

## Rulings that override the plan's code

1. **Surfaces are panelised** (`_split_surface`) — nothing may exceed a sheet of its
   own stock class, glazing included. The plan emitted whole-wall parts.
2. **Studs and plates stop at the roof underside** (`wall_top_front()`), not the roof
   top; the sloped bearing plate is cut on site.
3. **No sill plate across a door**; opening ids are wall-qualified
   (`king_left_transom`) because part ids are cutlist keys.
4. **Blocking exists**: one run per wall at the bearing line, `qty = bays`,
   `width = span / bays − 38`. The bay pitch is `span / bays` (= `span / n`), **not**
   `span / len(positions)` — `stud_positions` returns n+1 positions.
5. **Glazing height = band height − 2 rails** (220 mm), not the whole band.
6. **Waste counts kerfs actually cut**: `parts − boards`, not `boards − 1`.
7. **Unpriced sale lengths are skipped**, never ranked in millimetres against
   dollars; a flat per-class price entry applies to every length.
8. **Parts-only BOM when `spec is None`** (consumables are appended only with a spec).
9. **The model has no `WallsOpen`**: `_wall_bounds()` prefers it and otherwise unions
   the `*Cut` panels and `Post` objects; `envelope_from_bounds_list()` is the pure,
   tested seam. Envelope height uses the **model's** roof thickness (80 mm), never
   the wood build-up (120 mm).
10. **The Task 11 real-build test partitions parts** before nesting (both optimisers
    reject foreign stock classes).
11. **`--fetch` refreshes only missing or stale classes**, and a cache from another
    store is a hard `PriceError` → CLI exit 2.
12. **A null `store`/`province` is treated as unset** so the cache adopts the spec's.
13. **`set_price` requires a store** (from the spec); the CLI passes it to both the
    call and `HD_DEFAULT_STORE`. Never query national store 9999 and label it 7011.
14. **Deviations precede the itemised cost tables**; summary cards may sit above them
    (the spec's reading order). My reviewer prompt's "before any money" was wrong.
15. **Unknown-wall openings are rejected** by the validator.

## Corrections this project learned the hard way (in the skills now)

- `freecadcmd` sets `__name__` to the module name, so `if __name__ == "__main__"`
  never fires; a helper named after a stdlib module makes it exit 0 with no output.
- A cutter **tangent** to a face removes nothing — and so does one sitting inside a
  pre-existing opening. Check `cutter.common(part).Volume` (or `audit.bite()`)
  before building the cut.
- Audit **DAG roots**, not every object with a shape; overlap of exactly 0 is
  unachievable (OCCT round-off is 3e-6–7e-6 mm³).
- FreeCAD preset camera names cannot be trusted: probe with a one-sided marker.
  Set the camera in one call, capture in the next; captures can land late.
- A `TechDraw` page in a document breaks every later MCP screenshot call.

## What is still open

- Scoped re-review of the `4bcc8b6` fix (controller verified it by inspection:
  `set_price` demands a store, the CLI passes the spec store, unlisted classes warn).
- Deferred minors are listed per task in the ledger; the notable ones are malformed
  cache/compare JSON exiting 1 instead of a clean message, `resolve` stamping
  `fetched` on every offline run (churns the committed cache), and `cart.csv`
  writing server-controlled descriptions raw (spreadsheet formula injection).
- The cart (`$3,126.25` all-in at store 7011) is complete and attributable but not
  verified against a human's reading of each product; the workbook labels provenance
  so that review is possible.
