# Rebuilding a reference structure in Home Depot wood — design

- **Date:** 2026-09-12
- **Status:** approved for planning (brainstorming complete)
- **Scope owner:** Eric
- **Reference instance:** Keter Signature Walnut Pent 97 (Home Depot Canada SKU 1001865367, model 260435) — 9 × 7 ft resin shed, already modelled in `~/freecad/keter_signature_pent97.py`
- **Spec path:** `~/.pi/agent/docs/superpowers/specs/2026-09-12-wood-build-from-reference-design.md`

## Goal

A reusable capability that takes an existing structure — a product page, a photograph, a drawing, or an existing CAD model — and produces a **buildable wood version sourced from Home Depot Canada stock**, with:

1. a derived framing schedule (real studs, plates, headers, rafters, blocking),
2. a cutlist where every part carries finished size, stock class, grain direction and the sheet/board it comes off,
3. optimised buy quantities (2D sheet nesting + 1D cutting-stock, kerf-aware, yield % and offcut inventory),
4. a priced shopping cart from live Home Depot Canada data, subtotalled by category with tax,
5. an explicit **deviations table** for everything the reference has and Home Depot does not sell.

Delivered as a `budget.html` workbook plus `cutlist.csv`, `cart.csv`, `sku-qty.txt`, and encoded as three skills so future builds repeat the process.

## Non-goals

- No automated checkout or cart submission — Home Depot Canada has no stable multi-item cart URL; the output is a paste-ready SKU × qty list.
- No stamped engineering. Framing rules are conventional rules of thumb, not a sealed design; permit/span verification remains the builder's responsibility.
- No 3D re-modelling of the wood version in this iteration (the FreeCAD model stays the *reference*; the cutlist is derived through the build spec, not a new CAD tree).
- No per-sheet SVG cut diagrams (considered, deferred, optimiser is unaffected when added).

## Decisions (locked during brainstorming)

| # | Question | Decision |
|---|---|---|
| 1 | What are we costing? | **(A)** wood replica build with cutlist — not the resin kit |
| 2 | Construction system | **(i)** stick-framed replica (studs, sheathing, cladding, rafters) |
| 3 | Dimensional fidelity | **(a)** exterior envelope held exact (2788.9 × 2179.3 × 2258.1 mm); wall build-up grows inward; door opening 1386.8 × 1811 preserved; interior loss documented |
| 4 | Plank-groove method | **(1)** pre-grooved exterior siding (LP SmartSide / T1-11), installed rotated so the grooves run horizontally; only circular saw + drill required |
| 5 | Cart scope | **(A)** one cart, subtotalled by category (lumber, sheets, roof, glazing, vents, hardware, fasteners, base, finish) |
| 6 | Framing derivation | **(A)** framing derived from the envelope; the model supplies the enclosure surfaces and all critical dimensions |
| 7 | Optimiser rigour | **(A)** real 2D sheet nest + 1D cutting-stock with yields and offcuts; no diagrams |
| 8 | Pricing basis | **(b)** store `7011` = **ETOBICOKE SOUTH**, 193 North Queen Street, Etobicoke ON M9C 1A7 ⇒ Ontario **HST 13 %** |
| 9 | Deliverable format | **(A)** HTML budget workbook + `cutlist.csv` / `cart.csv` / `sku-qty.txt` |
| 10 | Skill packaging | **(2)** three focused skills, **pi-only path** `~/.pi/agent/skills/` (inside the `pi-config` git repo, so they sync across machines) |
| 11 | Pipeline architecture | **(A)** Python `woodbuild` package driven by a declarative build spec; cache-first pricing |

## Reference → wood translation (this build)

Exterior envelope is fixed, so the ~71 mm of extra wall thickness per side is taken out of the interior.

| reference | wood build | consequence |
|---|---|---|
| 40 mm resin double-wall panel | 11 mm grooved siding + 11 mm OSB + 89 mm 2×4 stud = **111 mm** | interior clear 2708.9 × 2099.3 → **2566.9 × 1957.3 mm** (lost 71 mm/side): floor area 5.64 → **5.02 m²**, volume 11.34 → **≈ 10.2 m³** (−10 %) |
| 45 × 45 mm moulded corner post | 3-stud 2×4 corner, 89 × 140 mm | post footprint grows; cladding corners need a trim detail |
| horizontal plank grooves @ 145 mm pitch | grooved sheet siding laid horizontally | groove pitch becomes the manufacturer's, not 145 mm |
| clerestory band, 5 panes, 300 mm | 300 mm framed window band, king studs at the 4 mullion lines, 5 glazed bays preserved | none dimensional |
| side transom 595 × 220 | same, in 6 mm polycarbonate | none dimensional |
| triangular louvre vent 620 × 300 | rectangular rough opening for a 12 × 18 in metal louvre | **shape change**, triangular filler panel needed |
| resin floor at base level + 60 mm plinth | PT 2×4 joists @ 406 mm on 4×4 PT skids + 18 mm T&G plywood deck, **entirely below the envelope datum** | **datum is the deck top**, not grade: 196 mm of base structure sits below the shed's zero plane, so the pad must be excavated/level with it or built up (deviation, and the only way to keep the 1811 mm door opening) |
| resin/steel sandwich roof, 80 mm build-up | 2×4 rafters @ 304.8 mm o.c. + mid purlin + 11 mm OSB deck + corrugated steel ≈ **120 mm build-up** | 2×6 rafters do not fit — see *Dimensional conflicts* below |
| moulded resin door leaves | 38 × 89 framed leaf + 18 mm exterior plywood skin, 3 hinges, hasp + cylinder | leaf thickness grows; hinges must suit an outward-swinging shed door |
| 150 kg/m² snow rating (product data) | 2×4 rafters @ 304.8 mm o.c. with a mid purlin (see below) | roof build-up 120 mm instead of 80 mm, costing 40 mm of clerestory clearance |
| level ground only | compacted gravel / paver base + skids | **new requirement** the reference does not have |

### Dimensional conflicts and their resolutions

Holding the exterior envelope exact (2788.9 × 2179.3 × 2258.1) collides with two things a stick-framed build needs. Both are resolved in favour of the reference's critical dimensions — the door opening and the 300 mm clerestory band — and the deviations are recorded in the workbook:

1. **Door opening vs floor structure.** The reference door opening is 1811 mm measured from the shed's own floor. A wood floor (89 skid + 89 joist + 18 deck = 196 mm) would eat it. **Resolution:** the envelope datum is the *finished deck top*, and all 196 mm of floor structure sits below it. Door opening stays 1811 mm above the deck, so the enclosure still takes the same machine. The base becomes an excavation/levelled pad rather than level ground.
2. **Roof build-up vs clerestory band.** Available band height = envelope height − roof build-up − door head. With 2×6 rafters (140 mm) + deck + steel = 171 mm build-up the roof underside at the front wall lands at 2087.1 mm, which interferes by 24 mm even with the band starting at the door head (1811.02 + 300 = 2111.0), and by 91 mm if the model's 67 mm sill strip is kept (band top 2178.1 > 2087.1). **Resolution:** switch to 2×4 rafters @ 304.8 mm o.c. with a mid purlin (effective span 1.09 m, adequate at 300 mm o.c. for the product's 150 kg/m² snow figure), giving a 120 mm roof build-up. Roof underside at the front wall = 2258.06 − 120 = 2138.1 mm; band occupies 1838.1 → 2138.1, clearing the 1811.02 mm door head by 27 mm. The 300 mm band, its 5-pane split and the door opening are all preserved; the cost is that the sill strip above the doors shrinks from 67 mm to 27 mm (cosmetic deviation). Interior volume at the chosen roof: 5.02 m² × mean underside height 2038.1 mm ≈ 10.24 m³.

Both resolutions are computed from the spec's own numbers by `spec.py`, which fails the build if a subsequent change to any of heights, roof build-up, band height or door head makes either check fail ("band does not fit under the roof build-up").

## Architecture

```
~/.pi/agent/skills/
  building-from-reference/
    SKILL.md                     # reference → spec → cutlist → cart workflow
    framing-rules.md             # heavy reference: spacings, header/rafter rules
    stock-catalogue.md           # heavy reference: HD sheet/board sizes, kerf
    substitutions.md             # heavy reference: known material translations
    scripts/
      woodbuild/
        spec.py        # BuildSpec dataclass, JSON load/save, validation
        stock.py       # stock classes: sheet sizes, board lengths, kerf, grain flags
        frame.py       # BuildSpec → parts (plates, studs, openings, rafters, blocking)
        optimise.py    # 2D sheet nest + 1D cutting-stock → buy plan, yield, offcuts
        bom.py         # buy plan → BOM lines incl. consumables
        pricing.py     # prices.json cache; --fetch drives MCP stdio; --compare
        report.py      # workbook HTML + CSV/plain exports
        spec_from_freecad.py   # FreeCAD document → BuildSpec (runs under freecadcmd)
      woodbuild.py     # CLI: spec in → workbook out
  freecad-render-views/
    SKILL.md
    scripts/freecad_views.py
  freecad-model-hygiene/
    SKILL.md
    scripts/audit.py

~/freecad/keter_pent97_build/
  keter_pent97.spec.json       # this build's spec (envelope, openings, framing rules)
  prices.json                  # price cache: SKU → price, store, timestamp, source
  out/budget.html, cutlist.csv, cart.csv, sku-qty.txt
```

Engine lives in the skill (versioned, synced); project data lives beside the model. `woodbuild` is **stdlib-only** so it runs under FreeCAD's bundled interpreter and plain `python3`.

### Data flow

```
reference  ──agent reasoning──►  spec.json  ──┐
existing FreeCAD doc ──spec_from_freecad.py──┘
                                              ▼
   frame.py ──► parts ──► optimise.py ──► buy plan ──► bom.py ──► SKUs
                                                                    ▼
                                        pricing.py (prices.json) ──► prices
                                                                    ▼
                                          report.py ──► budget.html + CSVs
```

## Build spec

Single seam between reasoning and computation. Indicative shape:

```jsonc
{
  "build": "keter-pent-97-wood",
  "source": { "kind": "product", "sku": "1001865367", "model": "260435",
              "url": "…", "cad": "~/freecad/KeterPent97.FCStd" },
  "envelope": { "width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                "roof_fall": 200.0, "tall_side": "front" },
  "wall": { "stud": "2x4", "spacing": 406.4, "sheathing": "osb_7_16",
            "siding": "smartside_grooved", "layers_out_to_in": ["siding_11","osb_11","stud_89"],
            "top_plates": 2, "sole_plate": "pt_2x4", "bearing_plate": true },
  "openings": [
    { "wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
      "sill": 0.0, "header": "2x8_doubled" },
    { "wall": "front", "kind": "window_band", "sill": 1878.06, "height": 300.0,
      "mullions": 4, "panes": [3.5, 1.5, 4.5, 4.5, 1.5], "glazing": "polycarbonate_6" },
    { "wall": "left|right", "kind": "transom", "y0": 105.0, "y1": 700.0,
      "sill_from_wall_top": 30.0, "height": 220.0 },
    { "wall": "left|right", "kind": "louvre", "shape": "rect", "width": 457.0,
      "height": 305.0, "near": "back_top" }
  ],
  "roof": { "rafter": "2x4", "spacing": 304.8, "purlin": "mid_span",
            "deck": "osb_7_16", "covering": "corrugated_steel",
            "overhang": { "front": 60, "back": 40, "side": 45 } },
  "floor": { "joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
             "skids": "pt_4x4", "below_datum": true },
  "doors": { "leaves": 2, "frame": "2x4", "skin": "plywood_ext_18",
             "hardware": ["hinge_x3_each", "hasp", "cylinder_lock"] },
  "base": { "kind": "gravel_or_pavers", "skids": 3 },
  "substitutions": [
    { "ref": "45mm moulded corner post", "build": "3-stud 2x4 corner (89x140)",
      "consequence": "corner trim detail required", "changes_diagram": true }
  ],
  "options": { "waste_factor": 0.0, "kerf": 3.0, "retain_offcut_min": 300.0 }
}
```

`spec.py` validation rejects: openings wider than their wall, openings overlapping, sill+height exceeding wall top, build-up thicker than the envelope, unknown stock classes, header/rafter spans exceeding the configured limits, **band not fitting between the door head and the roof build-up**, and **floor structure not below the datum when `below_datum` is set**.

## Framing rules (`frame.py`)

- plates: PT sole plate; **one top plate plus one bearing plate** directly under the rafters (2 in total).
- studs: 2×4 @ 406.4 mm o.c., first and last stud flush to the wall ends, layout measured from one datum so stud positions are reproducible.
- corners: 3-stud assembly (89 × 140 mm).
- openings: 2 king studs + jack studs each side, doubled header sized by span rule, cripple studs above heads down from the top plate. Side-wall openings are listed per wall (one `openings` entry per wall); the `left|right` shorthand in the example above is documentation, not spec input.
- band opening: continuous sill + head plates with king studs at every mullion line, preserving the 5-pane split.
- rafters: 2×4 @ 304.8 mm o.c. following the 200 mm fall, with a mid-span purlin, birdsmouth at the wall bearing (chosen in *Dimensional conflicts* above).
- blocking: at panel joints, at the roof bearing line, and wherever hardware lands (hinges, hasp, louvre).
- every part carries: id, wall/assembly, finished size, qty, stock class, `grain_locked`, and the joint/fastener it consumes.

Consumables are **derived**: fasteners per connection type counted from the part list, sheathing fasteners from panel perimeter + field spacing (150/300 mm), adhesive and sealant from linear metres of joint with a stated coverage per cartridge.

## Optimiser (`optimise.py`)

- **2D**: shelf packing, decreasing height, rotation allowed except `grain_locked` parts. Post-conditions asserted: every part placed exactly once, no overlaps, per-sheet area respected, kerf 3 mm respected between parts.
- **1D**: for each part list evaluate all stock lengths (8/10/12/16 ft) using first-fit-decreasing and choose the mix that **minimises total cost**, ties broken by least waste.
- outputs: buy quantity per SKU, per-sheet yield %, offcut inventory (any offcut ≥ `retain_offcut_min`), and the part → sheet/board mapping used by the cutlist.
- failure behaviour: an unplaceable part raises with the part id and size — never silently overbuying.

## Pricing (`pricing.py`)

Cache-first so budgets are reproducible and price drift is reviewable in git.

**Matching an item to a product is an agent judgment, not a script.** A programmatic description search almost always fails once the catalogue has more than a handful of similar products — the first real run proved it (the `2x4` class matched a $60.48 anchor bolt and accounted for ~$2,540 of the subtotal; `steel_roof` matched a ceiling tile; `hasp` matched a child-safety magnet). And any SKU written into a spec rots: Home Depot drops and replaces products of the same type constantly. So:

- the agent searches, **reads the candidate products**, and picks the one that is actually the material the cutlist calls for;
- the chosen SKU, its product name, its URL, its price and the reason it was chosen are recorded in the cache — the durable record is the *decision and its provenance*, not the SKU alone;
- a script may only ever price a line the agent has already matched. An unmatched line stays `unpriced` with its reason. A search hit is a *candidate for the agent to judge*, never a price;
- the cache carries a match date, so a later run can be told a match is stale and re-match it (re-matching is cheap; a wrong SKU bought is not);
- the workbook marks every line's provenance — agent-matched, or unmatched/unpriced — so an unattended run can never look like a finished budget.

```jsonc
{ "store": "7011", "storeName": "ETOBICOKE SOUTH", "province": "ON", "currency": "CAD",
  "fetched": "2026-09-12T18:20:00Z",
  "items":    { "1001160874": { "desc": "…", "price": 60.48, "uom": "each",
                                "source": "hd_product", "url": "…", "inStock": true,
                                "fetched": "…" } },
  "unpriced": { "1001163117": { "reason": "null price at store 7011",
                                "tried": ["hd_product"] } } }
```

- default run is **offline** from cache.
- `--fetch` refreshes only missing or older-than-7-days classes over MCP stdio. It uses `hd_product` when the agent has already matched a SKU, and `hd_search` only to *gather candidates* for the agent to judge — a search result is never written to the cache as a price by a script.
- **No invented prices, and no auto-accepted ones.** A price comes from an agent-matched SKU, or the class is `unpriced` with its reason; the workbook carries an "excludes N unpriced lines" caveat and its provenance column. A description-matched line is explicitly labelled a candidate, not a cost.
- `--compare old-prices.json` prints a price-delta table.
- live behaviour verified during brainstorming: `hd_search` on store 7011 returned real SKUs with CAD prices and stock, and some SKUs returned `"price": null`, confirming the need for the `unpriced` path.

## Workbook (`report.py`)

Reading order: header (build, store, cache timestamp, currency, generator version) → summary cards (subtotal, HST 13 %, total, line count, unpriced count, sheet yield, offcut value) → **deviations table** → framing schedule → sheet-goods schedule with per-sheet yield bars and part placement → cutlist (part, qty, finished size, stock, grain lock, source sheet/board) → BOM grouped by category with SKU, description, qty, unit price, line total, link → methodology, assumptions, provenance.

The summary cards are a headline, not an itemised cost: **the deviations table precedes every itemised cost table** so constraints are read before the money that pays for them. Styling reuses the dark theme of `~/freecad/views/index.html`.

Exports: `cutlist.csv`, `cart.csv`, `sku-qty.txt` (paste-ready `SKU qty` lines).

## Skills

Each skill ships only after baseline testing (superpowers:writing-skills is TDD for documentation: observe the failure without the skill, write the skill, re-observe).

1. **`building-from-reference`** — *Use when asked to rebuild an existing structure or product in wood, to produce a cutlist, bill of materials or priced shopping list for a build, or to turn a photo, drawing, product page or CAD model into buildable lumber and sheet-goods parts.* Contains the intake → spec → run → verify workflow, framing defaults, price discipline, substitution handling. Baseline task: "make a cutlist and Home Depot shopping cart for this shed" — expect area-math quantities, invented or missing prices, no framing schedule, no deviations.
2. **`freecad-render-views`** — *Use when rendering or screenshotting FreeCAD views, exporting per-side or exploded image sets, or when a FreeCAD render comes out blank, stale, of the wrong document, or refuses to change.* Carries: render through each document's own `ActiveView`; `viewPosition`/`viewUp` are read-only in FreeCAD 1.1 so only presets work; preset→face mapping (`viewRear` = door side, `viewFront` = back, `viewLeft`/`viewRight` = side panels); `saveImage` wedges the GUI thread after ~5 captures per call (batch ≤ 3, reopen the document for a fresh camera); orthographic camera for elevations; TechDraw page objects have no `.Shape` and break the MCP screenshot path; exploded views separate parts along their own normals; `Flat Lines` display mode makes exploded joins readable. Baseline task: "produce front/left/right/exploded PNGs of `KeterPent97.FCStd`" — expect wrong-document captures and wedged calls.
3. **`freecad-model-hygiene`** — *Use when building parametric FreeCAD models, boolean cuts, or anything with multiple touching parts — especially when faces look doubled, joins are unreadable, or a cut silently removes nothing.* Carries: the disjoint-parts design rule; the tangency bug (a cutter exactly tangent to a face removes nothing — extend it 1 mm past the surface); a horizontal panel top under a sloped roof interpenetrates; post heights must use the roof underside at the post's far edge; verification via pairwise `common()` volume audit plus parts-volume vs fused-union comparison; build in the GUI or the saved file opens with everything hidden; `parts` dict → object names. Baseline task: "add a triangular louvre vent to a side wall of this model" — expect a tangent cut that removes nothing.

## Verification

- **Engine**: unit tests, pure Python, no FreeCAD required. Optimiser: exactly-filling case, kerf-boundary case, grain-lock rejection, a 1D case where 2 × 12 ft beats 3 × 8 ft on cost, unplaceable-part failure. Framing: invariants — every part's stock exists, stud count = f(length, spacing), both sides of every opening framed, header depth within the span rule. Pricing: fake MCP transport, `null` price → `unpriced`, staleness, `--compare`. Report: golden-file test on a tiny spec.
- **Cross-check**: enclosure parts must re-derive from the model's envelope on every run; if the CAD changes, the run fails with "envelope mismatch" instead of cutting stale sizes.
- **End-to-end**: the real shed build must produce a workbook whose enclosure parts match the model's envelope, whose sheet placements all fit, and whose cart totals a plausible number for a 9 × 7 ft shed.
- **Skills**: baseline/green/refactor runs per skill, plus a discovery check that a fresh agent selects the right skill for each task.

## Order of work

1. Baseline test runs for the three skills (RED).
2. `woodbuild` engine: `spec`, `stock`, `optimise` (+ tests), `frame` (+ tests), `bom`, `pricing` (+ tests), `report` (+ golden test).
3. Shed build spec, `spec_from_freecad.py`, first real workbook run.
4. `building-from-reference` skill written and verified (GREEN), then `freecad-render-views`, then `freecad-model-hygiene`.
5. Commit engine, skills, spec and the shed build data to `pi-config`.

## Risks and open items

- **Not engineered.** Header/rafter sizing uses conventional span rules and the product's 150 kg/m² snow figure; a real build in a snow region should be checked against local code or an engineer. The mid-span purlin is what keeps 2×4 rafters defensible at this span.
- **Two documented collisions.** The floor datum and the roof build-up each forced a deviation (see *Dimensional conflicts*); both are computed and enforced by `spec.py`, not left to judgement at build time.
- **Price drift and stock.** Cache timestamps make staleness visible but a cart is only as good as its last fetch; some SKUs price `null` per store.
- **Description-matched SKUs.** `hd_search` fallback can select a near-miss product; the workbook records which tool answered each line so it is auditable.
- **Metric/imperial mixing.** Envelope is metric (from the product sheet), stock is imperial; the spec stores metric with stock classes carrying imperial names, and the cutlist prints both.
- **FreeCAD version coupling.** The render skill documents FreeCAD 1.1.1 behaviour specifically; re-verify if FreeCAD updates.
- **Siding groove pitch** will differ from the reference's 145 mm — cosmetic deviation, accepted.
