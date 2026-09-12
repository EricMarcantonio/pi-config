# Rebuild-from-reference: wood cutlist, optimised cart and skills — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stdlib-only Python engine plus three pi skills that turn a reference structure (product page, photo, drawing or FreeCAD model) into a buildable wood version sourced from Home Depot Canada — derived framing, cutlist, kerf-aware optimised buy quantities, a priced cart subtotalled by category with HST, and a deviations table.

**Architecture:** A declarative `spec.json` is the only seam. `frame.py` derives parts from the spec, `optimise.py` packs parts onto sheets and boards, `bom.py` turns the buy plan into SKU lines, `pricing.py` fills prices from a committed cache (optionally refreshing over MCP stdio), `report.py` emits `budget.html` + CSVs. The engine lives inside the `building-from-reference` skill so it versions with `pi-config`; the shed's spec and outputs live in `~/freecad/keter_pent97_build/`.

**Tech Stack:** Python 3.9+ standard library only (`dataclasses`, `json`, `subprocess`, `unittest`, `html`, `csv`, `argparse`, `math`). FreeCAD's bundled interpreter must be able to import the engine. No third-party packages.

**Spec:** `~/.pi/agent/docs/superpowers/specs/2026-09-12-wood-build-from-reference-design.md`

## Global Constraints

- **Engine is stdlib-only.** `import FreeCAD` is permitted **only** in `spec_from_freecad.py`; every other module must import cleanly under plain `python3`.
- **Tests use stdlib `unittest`.** Run with `python3 -m unittest discover -s <tests dir> -v`. No pytest, no fixtures, no external data files.
- **Units:** all internal dimensions in millimetres (float). Stock classes carry imperial names; the cutlist prints both. `2×4 = 38 × 89`, `2×6 = 38 × 140`, `2×8 = 38 × 184`, `4×4 = 89 × 89`, `4×8 sheet = 1219 × 2438`, `4×9 sheet = 1219 × 2743`, `1 ft = 304.8`.
- **Kerf = 3.0 mm**, applied between adjacent parts and at board cut ends. `retain_offcut_min = 300.0 mm`.
- **Money:** CAD floats, rounded to 2 dp at display only. Store `7011` (ETOBICOKE SOUTH), province `ON`, **HST 13 %**.
- **No invented prices.** A missing price renders as `unpriced` with a reason; never estimated, never zero.
- **Determinism:** every emitted file sorts its collections by a stable key so re-runs produce clean git diffs.
- **Locked build decisions (from the spec):** stick-framed replica; exterior envelope exact (2788.92 × 2179.32 × 2258.06); door opening exact (1386.84 × 1811.02); pre-grooved siding laid horizontally; 111 mm wall build-up; floor structure **below** the envelope datum; 2×4 rafters @ 304.8 with a mid purlin (120 mm roof build-up); one cart subtotalled by category.
- **Skill frontmatter:** `name` and `description` only; description starts with `Use when`, third person, no workflow summary; `SKILL.md` < 500 words with heavy reference in sibling `.md` files.
- **Every task ends with a commit** into the `pi-config` repo: `cd ~/.pi/agent && git add <paths> && git commit -m "<msg>"`.

## File Structure

```
~/.pi/agent/skills/building-from-reference/
  SKILL.md                       # workflow: reference → spec → run → verify → deviations
  framing-rules.md               # heavy reference: spacing, header/rafter rules, plate layout
  stock-catalogue.md             # heavy reference: stock classes, sizes, kerf, categories
  substitutions.md               # heavy reference: known material translations + consequences
  scripts/
    woodbuild.py                 # CLI entry point
    woodbuild/
      __init__.py                # version + public re-exports
      spec.py                    # BuildSpec, validation (incl. band-fits, floor-below-datum)
      stock.py                   # stock catalogue, kerf, unit helpers
      frame.py                   # envelope → parts (studs, plates, openings, rafters, blocking)
      optimise.py                # Part/Placement, 2D shelf packing, 1D cutting-stock
      bom.py                     # buy plan → SKU lines + derived consumables
      pricing.py                 # price cache, MCP stdio client, cache diff
      report.py                  # budget.html + cutlist.csv + cart.csv + sku-qty.txt
      spec_from_freecad.py       # FreeCAD doc → spec (only module importing FreeCAD)
    tests/
      test_stock.py test_spec.py test_optimise_sheets.py test_optimise_boards.py
      test_frame.py test_bom.py test_pricing.py test_report.py test_cli.py
      test_spec_from_freecad.py
~/.pi/agent/skills/freecad-render-views/
  SKILL.md
  scripts/freecad_views.py       # render_views() encoding the FreeCAD 1.1 workarounds
~/.pi/agent/skills/freecad-model-hygiene/
  SKILL.md
  scripts/audit.py               # check_disjoint(), pairwise_overlap()
~/freecad/keter_pent97_build/
  keter_pent97.spec.json         # this build's spec
  prices.json                    # committed price cache (class → sku/price/source/time)
  out/{budget.html,cutlist.csv,cart.csv,sku-qty.txt}
```

---

### Task 1: Package skeleton and stock catalogue

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/__init__.py`
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/stock.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_stock.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `KERF: float`; `FT: float`; `SHEETS: dict[str, dict]`; `BOARDS: dict[str, dict]`; `CATEGORIES: dict[str, str]` (stock class → BOM category); `is_sheet(cls) -> bool`; `sheet_size(cls) -> tuple[float, float]`; `thickness(cls) -> float`; `board_dims(cls) -> tuple[float, float]`; `board_lengths_mm(cls) -> list[float]`; `grain(cls) -> str | None`; `category(cls) -> str`; `unit_label(cls) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stock.py
import unittest
from woodbuild import stock


class TestStock(unittest.TestCase):
    def test_sheet_size_and_thickness(self):
        self.assertEqual(stock.sheet_size("osb_7_16"), (1219.0, 2438.0))
        self.assertEqual(stock.thickness("osb_7_16"), 11.0)
        self.assertTrue(stock.is_sheet("osb_7_16"))

    def test_small_sheet_for_glazing(self):
        self.assertEqual(stock.sheet_size("polycarbonate_6"), (610.0, 1220.0))

    def test_board_dims_and_lengths(self):
        self.assertEqual(stock.board_dims("2x4"), (38.0, 89.0))
        self.assertEqual(stock.board_lengths_mm("2x4"),
                         [2438.4, 3048.0, 3657.6, 4876.8])
        self.assertFalse(stock.is_sheet("2x4"))

    def test_grain_flags(self):
        self.assertEqual(stock.grain("smartside_grooved"), "groove")
        self.assertIsNone(stock.grain("osb_7_16"))

    def test_categories_and_labels(self):
        self.assertEqual(stock.category("2x4"), "lumber")
        self.assertEqual(stock.category("smartside_grooved"), "sheets")
        self.assertEqual(stock.category("polycarbonate_6"), "glazing")
        self.assertEqual(stock.unit_label("2x4"), "each")
        self.assertEqual(stock.unit_label("osb_7_16"), "sheet")

    def test_unknown_class_raises(self):
        with self.assertRaises(KeyError):
            stock.sheet_size("nope")

    def test_every_class_has_a_category(self):
        for cls in list(stock.SHEETS) + list(stock.BOARDS):
            self.assertIn(stock.category(cls), set(stock.CATEGORIES.values()))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_stock -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/__init__.py
"""woodbuild - reference structure -> wood cutlist, optimised buy plan, priced cart."""
__version__ = "0.1.0"
```

```python
# woodbuild/stock.py
"""Home Depot Canada stock catalogue: sheet goods, dimensional lumber, kerf.

All sizes in mm. Imperial names are kept because that is what the store sells
and what a builder asks for at the saw.
"""

KERF = 3.0
FT = 304.8
RETAIN_OFFCUT_MIN = 300.0

# stock class -> geometry. "grain" marks parts that may not be rotated when nested.
SHEETS = {
    "osb_7_16":         dict(size=(1219.0, 2438.0), thick=11.0, grain=None,
                             label='7/16" OSB sheathing', unit="sheet"),
    "plywood_tg_18":    dict(size=(1219.0, 2438.0), thick=18.0, grain="deck",
                             label='3/4" T&G plywood subfloor', unit="sheet"),
    "plywood_ext_18":   dict(size=(1219.0, 2438.0), thick=18.0, grain="face",
                             label='3/4" exterior plywood', unit="sheet"),
    "smartside_grooved": dict(size=(1219.0, 2438.0), thick=11.0, grain="groove",
                             label="LP SmartSide grooved panel siding", unit="sheet"),
    "polycarbonate_6":  dict(size=(610.0, 1220.0), thick=6.0, grain=None,
                             label="6 mm polycarbonate sheet", unit="sheet"),
}

# stock class -> (thickness, width) of the board's cross-section, plus sale lengths
BOARDS = {
    "pt_2x4": dict(dims=(38.0, 89.0), lengths_ft=(8, 10, 12, 16),
                   label='2x4x8-16 PT ground contact', unit="each"),
    "2x4":    dict(dims=(38.0, 89.0), lengths_ft=(8, 10, 12, 16), label="2x4 SPF", unit="each"),
    "2x6":    dict(dims=(38.0, 140.0), lengths_ft=(8, 10, 12, 16), label="2x6 SPF", unit="each"),
    "2x8":    dict(dims=(38.0, 184.0), lengths_ft=(8, 10, 12, 16), label="2x8 SPF", unit="each"),
    "pt_4x4": dict(dims=(89.0, 89.0), lengths_ft=(8, 10, 12), label="4x4 PT skid", unit="each"),
}

CATEGORIES = {
    "osb_7_16": "sheets", "plywood_tg_18": "sheets", "plywood_ext_18": "sheets",
    "smartside_grooved": "sheets", "polycarbonate_6": "glazing",
    "pt_2x4": "lumber", "2x4": "lumber", "2x6": "lumber", "2x8": "lumber",
    "pt_4x4": "base",
}


def _rec(cls):
    if cls in SHEETS:
        return SHEETS[cls]
    if cls in BOARDS:
        return BOARDS[cls]
    raise KeyError("unknown stock class: %s" % cls)


def is_sheet(cls):
    return cls in SHEETS


def sheet_size(cls):
    return tuple(_rec(cls)["size"])


def thickness(cls):
    return float(_rec(cls)["thick"] if cls in SHEETS else _rec(cls)["dims"][0])


def board_dims(cls):
    """(thickness, width) of a board's cross-section."""
    if cls not in BOARDS:
        raise KeyError("not a board stock class: %s" % cls)
    return BOARDS[cls]["dims"]


def board_lengths_mm(cls):
    return [round(ft * FT, 1) for ft in BOARDS[cls]["lengths_ft"]]


def grain(cls):
    return _rec(cls).get("grain")


def category(cls):
    return CATEGORIES[cls]


def unit_label(cls):
    return _rec(cls)["unit"]


def label(cls):
    return _rec(cls)["label"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_stock -v`
Expected: PASS (7 tests). Create `tests/__init__.py` (empty) if the import path needs it.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild skills/building-from-reference/scripts/tests
git commit -m "woodbuild: stock catalogue (sheets, boards, kerf, categories)"
```

---

### Task 2: Build spec loading and validation

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/spec.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_spec.py`

**Interfaces:**
- Consumes: `stock.thickness`, `stock.is_sheet`, `stock.BOARDS`, `stock.SHEETS`.
- Produces: `class SpecError(Exception)`; `@dataclass BuildSpec` with `.data: dict`, classmethod `load(path) -> BuildSpec`, `.save(path) -> None`, `.validate() -> None` (raises `SpecError` with **all** problems joined by `"; "`), and read-only helpers `envelope`, `wall_build_up()`, `roof_build_up()`, `wall_top_front()`, `band_top()`, `band_sill()`, `door_head()`, `openings()`, `substitutions()`, `search_terms()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec.py
import json
import os
import tempfile
import unittest

from woodbuild.spec import BuildSpec, SpecError

GOOD = {
    "build": "unit-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["siding_11", "osb_11", "stud_89"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span",
             "deck": "osb_7_16", "covering": "corrugated_steel", "build_up": 120.0},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None},
    ],
    "substitutions": [{"ref": "45mm post", "build": "3-stud corner",
                       "consequence": "corner trim needed", "changes_diagram": True}],
    "pricing": {"store": "7011", "search": {"2x4": "2x4x8 SPF stud",
                                            "osb_7_16": "7/16 OSB sheathing"}},
    "options": {"kerf": 3.0, "retain_offcut_min": 300.0},
}


def write(obj):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh)
    return path


class TestSpec(unittest.TestCase):
    def setUp(self):
        self.path = write(GOOD)

    def test_load_and_round_trip(self):
        spec = BuildSpec.load(self.path)
        spec.validate()
        out = self.path + ".out"
        spec.save(out)
        again = BuildSpec.load(out)
        self.assertEqual(again.envelope["width"], 2788.92)
        os.unlink(out)

    def test_wall_build_up_from_layers(self):
        spec = BuildSpec.load(self.path)
        self.assertEqual(spec.wall_build_up(), 111.0)   # siding 11 + osb 11 + stud 89

    def test_wall_build_up_uses_stock_class_thickness(self):
        data = json.loads(json.dumps(GOOD))
        data["wall"]["layers_out_to_in"] = ["smartside_grooved", "osb_7_16", "2x4"]
        spec = BuildSpec.load(write(data))
        self.assertEqual(spec.wall_build_up(), 11.0 + 11.0 + 38.0)

    def test_band_must_fit_under_roof_build_up(self):
        data = json.loads(json.dumps(GOOD))
        data["roof"]["build_up"] = 171.0            # 2x6 rafters: the collision from the spec
        spec = BuildSpec.load(write(data))
        with self.assertRaises(SpecError) as ctx:
            spec.validate()
        self.assertIn("band does not fit", str(ctx.exception))

    def test_wall_build_up_must_fit_inside_envelope(self):
        data = json.loads(json.dumps(GOOD))
        # 30 x 111 mm = 3330 mm of layers on a 2788.92 mm wall: breach the envelope
        data["wall"]["layers_out_to_in"] = ["smartside_grooved", "osb_7_16", "2x4"] * 30
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("build-up", str(ctx.exception))

    def test_opening_must_fit_between_the_corners(self):
        data = json.loads(json.dumps(GOOD))
        data["openings"][0]["width"] = 9999.0
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("wider than", str(ctx.exception))

    def test_band_wider_than_the_corner_span_is_rejected(self):
        # the model's band spans between 45 mm moulded posts (2698.92 mm); wood corners
        # are 89 mm each, so the band must shrink to 2610.92 mm
        data = json.loads(json.dumps(GOOD))
        band = [o for o in data["openings"] if o["kind"] == "band"][0]
        band["width"] = 2698.92
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("wider than", str(ctx.exception))

    def test_door_head_reported(self):
        spec = BuildSpec.load(self.path)
        self.assertAlmostEqual(spec.door_head(), 1811.02)

    def test_unknown_stock_class_rejected(self):
        data = json.loads(json.dumps(GOOD))
        data["roof"]["deck"] = "unobtainium"
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("unknown stock class", str(ctx.exception))

    def test_floor_below_datum_required_when_flagged(self):
        data = json.loads(json.dumps(GOOD))
        data["floor"]["below_datum"] = False
        with self.assertRaises(SpecError) as ctx:
            BuildSpec.load(write(data)).validate()
        self.assertIn("datum", str(ctx.exception))

    def test_search_terms_pass_through(self):
        spec = BuildSpec.load(self.path)
        self.assertEqual(spec.search_terms()["2x4"], "2x4x8 SPF stud")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_spec -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.spec'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/spec.py
"""The build spec: the only seam between reasoning and computation.

A spec describes an envelope, a wall build-up, openings, roof and floor
structure, known substitutions and price search terms. Everything downstream
(frame, optimise, bom, report) reads the spec and nothing else.
"""

import json
from dataclasses import dataclass

from . import stock


class SpecError(Exception):
    """Raised when a spec cannot produce a closed, buildable envelope."""


@dataclass
class BuildSpec:
    data: dict

    # ---- io -----------------------------------------------------------
    @classmethod
    def load(cls, path):
        with open(path) as fh:
            return cls(json.load(fh))

    def save(self, path):
        with open(path, "w") as fh:
            json.dump(self.data, fh, indent=2, sort_keys=False)
            fh.write("\n")

    # ---- accessors ----------------------------------------------------
    @property
    def envelope(self):
        return self.data["envelope"]

    def openings(self, wall=None):
        items = self.data.get("openings", [])
        return [o for o in items if wall is None or o["wall"] == wall]

    def substitutions(self):
        return self.data.get("substitutions", [])

    def search_terms(self):
        return self.data.get("pricing", {}).get("search", {})

    def option(self, key, default=None):
        return self.data.get("options", {}).get(key, default)

    # ---- derived dimensions -------------------------------------------
    def wall_build_up(self):
        total = 0.0
        for layer in self.data["wall"]["layers_out_to_in"]:
            if layer in stock.SHEETS or layer in stock.BOARDS:
                total += stock.thickness(layer)
            elif layer.startswith(("siding_", "osb_", "stud_")):
                total += float(layer.split("_")[-1])
            else:
                raise SpecError("unknown wall layer: %s" % layer)
        return total

    def roof_build_up(self):
        return float(self.data["roof"]["build_up"])

    def wall_top_front(self):
        """Top of the wall panels on the tall side (roof underside at the front)."""
        return self.envelope["height_tall"] - self.roof_build_up()

    def band_top(self):
        band = [o for o in self.openings("front") if o["kind"] == "band"]
        if not band:
            return None
        return float(band[0]["sill"]) + float(band[0]["height"])

    def band_sill(self):
        band = [o for o in self.openings("front") if o["kind"] == "band"]
        return None if not band else float(band[0]["sill"])

    def door_head(self):
        doors = [o for o in self.openings("front") if o["kind"] == "door"]
        if not doors:
            return 0.0
        return float(doors[0]["sill"]) + float(doors[0]["height"])

    # ---- validation ---------------------------------------------------
    def _check_stock_classes(self, problems):
        fields = [("wall.stud", self.data["wall"].get("stud")),
                  ("roof.rafter", self.data["roof"].get("rafter")),
                  ("roof.deck", self.data["roof"].get("deck")),
                  ("floor.joist", self.data["floor"].get("joist")),
                  ("floor.deck", self.data["floor"].get("deck")),
                  ("floor.skids", self.data["floor"].get("skids"))]
        for name, cls in fields:
            if cls is None:
                continue
            if cls not in stock.SHEETS and cls not in stock.BOARDS:
                problems.append("%s: unknown stock class %s" % (name, cls))
        for o in self.openings():
            if o.get("header") and o["header"] not in stock.BOARDS:
                problems.append("opening header: unknown stock class %s" % o["header"])

    def validate(self):
        problems = []
        self._check_stock_classes(problems)

        env = self.envelope
        try:
            build_up = self.wall_build_up()
        except SpecError as exc:
            problems.append(str(exc))
            build_up = 0.0
        if 2 * build_up >= env["width"]:
            problems.append("wall build-up %.1f mm does not fit inside width %.1f mm"
                            % (build_up, env["width"]))
        if 2 * build_up >= env["depth"]:
            problems.append("wall build-up %.1f mm does not fit inside depth %.1f mm"
                            % (build_up, env["depth"]))

        for wall, span in (("front", env["width"]), ("back", env["width"]),
                           ("left", env["depth"]), ("right", env["depth"])):
            # an opening spans between the corner assemblies, not the interior clear
            limit = span - 2 * float(self.data["wall"].get("corner_width", 89.0))
            for o in self.openings(wall):
                if float(o["width"]) > limit:
                    problems.append("%s %s opening %.1f mm is wider than the %s wall "
                                    "allows between corners (%.1f mm)"
                                    % (wall, o["kind"], float(o["width"]), wall, limit))
                if float(o["sill"]) + float(o["height"]) > self.wall_top_front():
                    problems.append("%s %s opening tops out above the wall top"
                                    % (wall, o["kind"]))
                if o["kind"] == "door" and wall in ("left", "right"):
                    problems.append("doors belong on the front or back wall")

        if self.data["floor"].get("below_datum") and float(self.data["floor"]["build_up"]) <= 0:
            problems.append("floor build-up must be positive to sit below the datum")
        if not self.data["floor"].get("below_datum"):
            problems.append("floor structure must sit below the datum "
                            "(floor.below_datum is false)")

        # band must clear the door head and fit under the roof build-up
        if self.band_top() is not None:
            if self.band_top() > self.wall_top_front():
                problems.append("band does not fit under the roof build-up: band top "
                                "%.1f mm exceeds wall top %.1f mm"
                                % (self.band_top(), self.wall_top_front()))
            if self.band_sill() < self.door_head():
                problems.append("band does not fit: band sill %.1f mm is below the door "
                                "head %.1f mm" % (self.band_sill(), self.door_head()))

        if problems:
            raise SpecError("; ".join(problems))
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_spec -v`
Expected: PASS (11 tests). `test_band_must_fit_under_roof_build_up` must fail the spec exactly as the design document describes (171 mm build-up with a band topping at 2138.04 mm against a wall top of 2087.06 mm), and `test_band_wider_than_the_corner_span_is_rejected` is the deviation the wood build forces on the band width.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/spec.py skills/building-from-reference/scripts/tests/test_spec.py
git commit -m "woodbuild: build spec with envelope/band/floor validation"
```

---

### Task 3: 2D sheet nesting

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/optimise.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_optimise_sheets.py`

**Interfaces:**
- Consumes: `stock.KERF`, `stock.sheet_size`, `stock.grain`, `stock.is_sheet`.
- Produces: `@dataclass Part(id, w, h, qty=1, stock="", grain_locked=False, assembly="", note="")`; `@dataclass Placement(part_id, x, y, w, h, rotated)`; `@dataclass SheetPlan(stock, sheets: list[list[Placement]], sheet_area, used_area)` with `.count` and `.yield_pct()`; `class NestError(Exception)`; `pack_sheets(parts, kerf=stock.KERF) -> tuple[list[SheetPlan], list[Part]]` (plans, unplaced); `parts_area(parts) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_optimise_sheets.py
import unittest

from woodbuild.optimise import NestError, Part, Placement, pack_sheets, parts_area
from woodbuild import stock


def P(pid, w, h, qty=1, cls="osb_7_16", grain_locked=False):
    return Part(id=pid, w=w, h=h, qty=qty, stock=cls, grain_locked=grain_locked)


class TestSheetNesting(unittest.TestCase):
    def test_two_halves_fill_one_sheet(self):
        # 1200 + 3 mm kerf + 1200 = 2403 <= 2438, so both panels share one sheet
        plans, unplaced = pack_sheets([P("a", 1219.0, 1200.0), P("b", 1219.0, 1200.0)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 1)
        self.assertEqual(len(plans[0].sheets[0]), 2)

    def test_kerf_decides_whether_the_second_row_fits(self):
        # 1218 + kerf + 1218 = 2439 > 2438: the kerf pushes the second row onto a new sheet
        plans, unplaced = pack_sheets([P("x", 1219.0, 1218.0, qty=2)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 2)

    def test_two_panels_share_a_shelf_across_the_width(self):
        # 608 + 3 mm kerf + 608 = 1219 exactly, so both fit across the sheet
        plans, unplaced = pack_sheets([P("w", 608.0, 1000.0, qty=2)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 1)
        self.assertEqual(len(plans[0].sheets[0]), 2)

    def test_grain_locked_parts_never_rotate_even_when_it_would_fit(self):
        # 2438 x 300 only fits a 1219 x 2438 sheet rotated, and grain locking forbids it
        plans, unplaced = pack_sheets([P("g", 2438.0, 300.0, grain_locked=True)])
        self.assertEqual(plans, [])
        self.assertEqual([p.id for p in unplaced], ["g"])

    def test_free_parts_may_rotate_to_fit(self):
        plans, unplaced = pack_sheets([P("r", 2438.0, 300.0)])
        self.assertEqual(unplaced, [])
        self.assertTrue(plans[0].sheets[0][0].rotated)
        self.assertAlmostEqual(plans[0].sheets[0][0].w, 300.0)

    def test_part_larger_than_sheet_is_reported_unplaced(self):
        plans, unplaced = pack_sheets([P("huge", 3000.0, 3000.0)])
        self.assertEqual(plans, [])
        self.assertEqual([p.id for p in unplaced], ["huge"])

    def test_no_overlaps_and_inside_sheet_bounds(self):
        parts = [P("a", 600.0, 400.0, qty=4), P("b", 1219.0, 500.0, qty=2)]
        plans, unplaced = pack_sheets(parts)
        self.assertEqual(unplaced, [])
        w_sheet, h_sheet = stock.sheet_size("osb_7_16")
        for plan in plans:
            for sheet in plan.sheets:
                for pl in sheet:
                    self.assertLessEqual(pl.x + pl.w, w_sheet + 1e-6)
                    self.assertLessEqual(pl.y + pl.h, h_sheet + 1e-6)
                for i, a in enumerate(sheet):
                    for b in sheet[i + 1:]:
                        xo = max(a.x, b.x) < min(a.x + a.w, b.x + b.w)
                        yo = max(a.y, b.y) < min(a.y + a.h, b.y + b.h)
                        self.assertFalse(xo and yo, "overlap %s/%s" % (a.part_id, b.part_id))

    def test_yield_and_area(self):
        # two 1219 x 1200 panels on one 1219 x 2438 sheet: 98.4 % of the sheet is used
        plans, _ = pack_sheets([P("a", 1219.0, 1200.0, qty=2)])
        self.assertAlmostEqual(plans[0].yield_pct(), 98.4, places=1)
        self.assertAlmostEqual(parts_area([P("a", 100.0, 200.0, qty=3)]), 60000.0)

    def test_glazing_uses_its_own_sheet_class(self):
        # a 700 x 220 pane must turn to fit a 610 x 1220 sheet
        plans, unplaced = pack_sheets([P("pane", 700.0, 220.0, cls="polycarbonate_6")])
        self.assertEqual(unplaced, [])
        self.assertEqual(plans[0].stock, "polycarbonate_6")
        self.assertTrue(plans[0].sheets[0][0].rotated)
        self.assertAlmostEqual(plans[0].sheets[0][0].w, 220.0)

    def test_sheet_offcuts_keep_large_remainders(self):
        # one 600 x 600 panel leaves a 1838 mm tall strip above it on a 1219 x 2438 sheet
        plans, _ = pack_sheets([P("s", 600.0, 600.0)])
        offcuts = plans[0].offcuts()
        self.assertTrue(any(h >= 300.0 for _, h in offcuts))

    def test_non_sheet_stock_is_rejected(self):
        with self.assertRaises(NestError):
            pack_sheets([P("b", 1000.0, 89.0, cls="2x4")])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_optimise_sheets -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.optimise'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/optimise.py
"""Kerf-aware nesting: 2D shelf packing for sheet goods, 1D cutting-stock for boards."""

import math
from dataclasses import dataclass, field

from . import stock


class NestError(Exception):
    """Raised when a part cannot be placed on any available sheet."""


@dataclass
class Part:
    id: str
    w: float
    h: float
    qty: int = 1
    stock: str = ""
    grain_locked: bool = False
    assembly: str = ""
    note: str = ""

    def area(self):
        return self.w * self.h * self.qty

    def expanded(self):
        """One Part per physical copy, ids suffixed #n when qty > 1."""
        if self.qty == 1:
            return [self]
        out = []
        for n in range(1, self.qty + 1):
            out.append(Part(id="%s#%d" % (self.id, n), w=self.w, h=self.h, qty=1,
                            stock=self.stock, grain_locked=self.grain_locked,
                            assembly=self.assembly, note=self.note))
        return out


@dataclass
class Placement:
    part_id: str
    x: float
    y: float
    w: float
    h: float
    rotated: bool = False


@dataclass
class SheetPlan:
    stock: str
    sheets: list = field(default_factory=list)   # list[list[Placement]]

    @property
    def count(self):
        return len(self.sheets)

    @property
    def sheet_area(self):
        w, h = stock.sheet_size(self.stock)
        return w * h * self.count

    @property
    def used_area(self):
        return sum(p.w * p.h for s in self.sheets for p in s)

    def yield_pct(self):
        return 100.0 * self.used_area / self.sheet_area if self.sheet_area else 0.0

    def offcuts(self):
        """Remaining rectangles >= RETAIN_OFFCUT_MIN, one per shelf remainder."""
        out = []
        w_sheet, h_sheet = stock.sheet_size(self.stock)
        for sheet in self.sheets:
            shelf_y = 0.0
            for p in sorted(sheet, key=lambda q: q.y):
                if p.y > shelf_y:
                    h = p.y - shelf_y
                    if h >= stock.RETAIN_OFFCUT_MIN:
                        out.append((w_sheet, h))
                shelf_y = max(shelf_y, p.y + p.h)
            if h_sheet - shelf_y >= stock.RETAIN_OFFCUT_MIN:
                out.append((w_sheet, h_sheet - shelf_y))
        return out


def parts_area(parts):
    return sum(p.area() for p in parts)


def _fits(part, sheet_w, sheet_h, kerf, rotated):
    w, h = (part.h, part.w) if rotated else (part.w, part.h)
    if w > sheet_w + 1e-9 or h > sheet_h + 1e-9:
        return None
    return w, h


def _orientations(part, sheet_w, sheet_h):
    opts = []
    straight = _fits(part, sheet_w, sheet_h, stock.KERF, False)
    if straight:
        opts.append((False, straight))
    if not part.grain_locked:
        rot = _fits(part, sheet_w, sheet_h, stock.KERF, True)
        if rot and (abs(rot[0] - part.w) > 1e-9):
            opts.append((True, rot))
    # prefer the orientation that leaves the shelf shorter, i.e. wide-and-short
    opts.sort(key=lambda o: (o[1][1], -o[1][0]))
    return opts


def pack_sheets(parts, kerf=stock.KERF):
    """Shelf packing, decreasing height. Returns (plans, unplaced_parts)."""
    todo = []
    for p in parts:
        if not p.qty:
            continue
        if not stock.is_sheet(p.stock):
            raise NestError("not a sheet stock class: %s (%s)" % (p.stock, p.id))
        todo.extend(p.expanded())

    by_class = {}
    for p in todo:
        by_class.setdefault(p.stock, []).append(p)

    plans, unplaced = [], []
    for cls in sorted(by_class):
        sheet_w, sheet_h = stock.sheet_size(cls)
        queue = sorted(by_class[cls], key=lambda p: (-max(p.w, p.h), p.id))
        plan = SheetPlan(stock=cls)
        sheet, shelf_y = [], 0.0
        shelf_h, cursor_x = 0.0, 0.0

        def new_sheet():
            nonlocal sheet, shelf_y, shelf_h, cursor_x
            if sheet:
                plan.sheets.append(sheet)
            sheet, shelf_y, shelf_h, cursor_x = [], 0.0, 0.0, 0.0

        for part in queue:
            opts = _orientations(part, sheet_w, sheet_h)
            if not opts:
                unplaced.append(part)
                continue
            placed = False
            while not placed:
                for rotated, (w, h) in opts:
                    if cursor_x + w <= sheet_w + 1e-9 and shelf_y + h <= sheet_h + 1e-9:
                        sheet.append(Placement(part.id, cursor_x, shelf_y, w, h, rotated))
                        cursor_x += w + kerf
                        shelf_h = max(shelf_h, h)
                        placed = True
                        break
                if placed:
                    break
                if shelf_y + shelf_h + kerf + min(o[1][1] for o in opts) <= sheet_h + 1e-9:
                    shelf_y += shelf_h + kerf      # open a new shelf on the same sheet
                    shelf_h, cursor_x = 0.0, 0.0
                else:
                    if not sheet:                  # nothing on this sheet: cannot fit at all
                        unplaced.append(part)
                        placed = True
                        break
                    new_sheet()
        if sheet:
            plan.sheets.append(sheet)
        if plan.sheets:
            plans.append(plan)
    return plans, unplaced
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_optimise_sheets -v`
Expected: PASS (9 tests) — three of them pin the kerf arithmetic (2403 fits, 2439 does not, 608+608+kerf exactly fills the width).

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/optimise.py skills/building-from-reference/scripts/tests/test_optimise_sheets.py
git commit -m "woodbuild: kerf-aware 2D sheet nesting with grain locking"
```

---

### Task 4: 1D cutting-stock for boards

**Files:**
- Modify: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/optimise.py` (append)
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_optimise_boards.py`

**Interfaces:**
- Consumes: `Part`, `stock.board_lengths_mm`, `stock.KERF`.
- Produces: `@dataclass BoardPlan(stock, length_mm, count, cuts: list[list[tuple[str, float]]])` with `.yield_pct()`, `.offcuts()`; `cut_boards(parts, prices=None, kerf=stock.KERF) -> tuple[list[BoardPlan], list[Part]]`.
  (A `board_cost()` helper was considered and dropped: no consumer needs it — `bom.py` prices plans from their counts.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_optimise_boards.py
import unittest

from woodbuild.optimise import BoardPlan, Part, cut_boards
from woodbuild import stock


def B(pid, length, qty=1, cls="2x4"):
    return Part(id=pid, w=length, h=stock.board_dims(cls)[1], qty=qty, stock=cls)


class TestBoardCutting(unittest.TestCase):
    def test_single_part_picks_the_shortest_board_that_fits(self):
        plans, unplaced = cut_boards([B("plate", 2440.0)])
        self.assertEqual(unplaced, [])
        self.assertEqual(sum(p.count for p in plans), 1)
        # 8 ft is 2438.4 mm, just short of 2440, so the 10 ft board wins
        self.assertEqual(plans[0].length_mm, 3048.0)

    def test_exact_fit_two_parts_on_one_board(self):
        plans, unplaced = cut_boards([B("half", 1216.0, qty=2)])
        self.assertEqual(unplaced, [])
        self.assertEqual(len(plans[0].cuts), 1)           # both halves on one 8 ft board
        self.assertEqual(plans[0].length_mm, 2438.4)

    def test_kerf_blocks_the_second_part(self):
        # prices force the 8 ft board, where 1226 + kerf + 1226 does not fit
        prices = {"2x4": {2438.4: 1.0, 3048.0: 4.0, 3657.6: 5.0, 4876.8: 6.0}}
        plans, _ = cut_boards([B("half", 1226.0, qty=2)], prices=prices)
        self.assertEqual(plans[0].length_mm, 2438.4)
        self.assertEqual(len(plans[0].cuts), 2)

    def test_cheapest_mix_beats_the_naive_per_part_choice(self):
        # 12 parts of 3000 mm: every board takes one part, so the cheapest per-board
        # length wins even though it is the longest stock
        prices = {"2x4": {2438.4: 1.0, 3048.0: 9.0, 4876.8: 6.20}}
        plans, unplaced = cut_boards([B("stud", 3000.0, qty=12)], prices=prices)
        self.assertEqual(unplaced, [])
        total_cost = sum(p.count * prices["2x4"][p.length_mm] for p in plans)
        self.assertAlmostEqual(total_cost, 12 * 6.20, places=2)
        self.assertEqual(plans[0].length_mm, 4876.8)
        self.assertEqual(plans[0].count, 12)

    def test_long_part_uses_longest_board(self):
        plans, unplaced = cut_boards([B("rafter", 2500.0)])
        self.assertEqual(unplaced, [])
        self.assertEqual(plans[0].length_mm, 3048.0)      # 10 ft

    def test_part_longer_than_any_board_is_unplaced(self):
        plans, unplaced = cut_boards([B("absurd", 6000.0)])
        self.assertEqual(plans, [])
        self.assertEqual([p.id for p in unplaced], ["absurd"])

    def test_offcuts_reported_and_yield(self):
        plans, _ = cut_boards([B("s", 2400.0)])
        self.assertAlmostEqual(plans[0].yield_pct(), 100.0 * 2400.0 / 2438.4, places=3)
        self.assertEqual(plans[0].offcuts(), [])          # 38 mm remainder is not retained

    def test_without_prices_it_minimises_purchased_length(self):
        # two 2400 mm parts fit on one 16 ft board (4803 mm) but not on one 10 ft board
        plans, _ = cut_boards([B("s", 2400.0, qty=2)])
        self.assertEqual(plans[0].length_mm, 4876.8)
        self.assertEqual(plans[0].count, 1)

    def test_partial_length_table_excludes_the_unpriced_length(self):
        # prices cover 8 and 12 ft but not 10 or 16 ft. Ranking the unpriced 16 ft
        # board by millimetres against dollars would silently exclude it; 12 ft wins.
        prices = {"2x4": {2438.4: 1.0, 3657.6: 5.0}}
        plans, unplaced = cut_boards([B("s", 3000.0, qty=2)], prices=prices)
        self.assertEqual(unplaced, [])
        self.assertEqual(plans[0].length_mm, 3657.6)
        self.assertEqual(plans[0].count, 2)

    def test_flat_per_class_price_applies_to_every_length(self):
        # the real price cache holds one price per class, not a length table
        plans, _ = cut_boards([B("s", 2400.0, qty=2)],
                              prices={"2x4": {"price": 9.99, "sku": "1"}})
        self.assertEqual(plans[0].length_mm, 4876.8)      # fewest boards wins the tie

    def test_board_offcuts_keep_large_remainders(self):
        plans, _ = cut_boards([B("s", 1000.0)])
        self.assertEqual(plans[0].length_mm, 2438.4)
        self.assertEqual(plans[0].offcuts(), [1438.4])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_optimise_boards -v`
Expected: FAIL — `ImportError: cannot import name 'cut_boards'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to woodbuild/optimise.py

@dataclass
class BoardPlan:
    stock: str
    length_mm: float
    count: int
    cuts: list = field(default_factory=list)   # list[list[(part_id, used_mm)]]

    @property
    def purchased_mm(self):
        return self.length_mm * self.count

    @property
    def used_mm(self):
        return sum(u for c in self.cuts for _, u in c)

    def yield_pct(self):
        return 100.0 * self.used_mm / self.purchased_mm if self.purchased_mm else 0.0

    def offcuts(self):
        """Remainders >= RETAIN_OFFCUT_MIN, board by board.

        A board holding k parts is cut k-1 times, so the kerf is accounted per
        board rather than pooled across the plan.
        """
        out = []
        for row in self.cuts:
            used = sum(x for _, x in row)
            rem = self.length_mm - used - stock.KERF * max(0, len(row) - 1)
            if rem >= stock.RETAIN_OFFCUT_MIN:
                out.append(round(rem, 1))
        return out


def _price_for_length(prices, cls, length_mm):
    """(price, is_length_table) for one sale length.

    `prices[cls]` is either a flat per-board price entry (`{"price": 4.25, ...}`,
    which is what the real price cache holds) or a length -> price table (tests).
    A length table that omits a length means that length is not priced: the
    caller skips the candidate rather than ranking millimetres against dollars.
    """
    entry = (prices or {}).get(cls)
    if isinstance(entry, dict):
        if length_mm in entry:
            return float(entry[length_mm]), True
        if "price" in entry:
            value = entry["price"]
            return (float(value) if value is not None else None), False
        numeric = [v for k, v in entry.items() if isinstance(k, (int, float))]
        return None, bool(numeric)
    if isinstance(entry, (int, float)):
        return float(entry), False
    return None, False


def _ffd(lengths, stock_len, kerf):
    """First-fit-decreasing into boards of stock_len. Returns list of boards."""
    boards = []
    for ln in sorted(lengths, reverse=True):
        for board in boards:
            used = sum(x for _, x in board) + kerf * len(board)
            if used + ln <= stock_len + 1e-9:
                board.append((None, ln))
                break
        else:
            if ln > stock_len + 1e-9:
                return None
            boards.append([(None, ln)])
    return boards


def cut_boards(parts, prices=None, kerf=stock.KERF):
    """Cheapest mix of sale lengths. `prices` maps stock class -> {length_mm: price}."""
    todo, unplaced = [], []
    for p in parts:
        if not p.qty:
            continue
        if p.stock not in stock.BOARDS:
            # boards are the only 1D stock; sheets are handled by pack_sheets
            raise NestError("not a board stock class: %s (%s)" % (p.stock, p.id))
        for _ in range(p.qty):
            todo.append(p)

    by_class = {}
    for p in todo:
        by_class.setdefault(p.stock, []).append(p)

    plans = []
    for cls in sorted(by_class):
        group = by_class[cls]
        lengths = [p.w for p in group]
        candidates = []
        for stock_len in stock.board_lengths_mm(cls):
            boards = _ffd(lengths, stock_len, kerf)
            if boards is None:
                continue
            price, length_table = _price_for_length(prices, cls, stock_len)
            if length_table and price is None:
                continue                                  # unpriced length in a partial table
            if price is not None:
                cost = len(boards) * price
            else:
                cost = len(boards) * stock_len            # no prices: rank by purchased length
            # kerfs actually cut: a board holding k parts is cut k-1 times
            waste = (len(boards) * stock_len - sum(lengths)
                     - kerf * (len(lengths) - len(boards)))
            candidates.append((cost, waste, stock_len, boards))
        if not candidates:
            unplaced.extend(group)
            continue
        # cheapest total, then least waste, then fewest boards, then shortest stock
        candidates.sort(key=lambda c: (c[0], c[1], len(c[3]), c[2]))
        cost, waste, stock_len, boards = candidates[0]

        # assign real part ids to the cuts, longest first within each board
        pool = sorted(group, key=lambda p: -p.w)
        cuts = []
        for board in boards:
            row = []
            for _, used in board:
                part = pool.pop(0)
                row.append((part.id, used))
            cuts.append(row)
        plans.append(BoardPlan(stock=cls, length_mm=stock_len, count=len(boards), cuts=cuts))
    return plans, unplaced
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_optimise_boards -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/optimise.py skills/building-from-reference/scripts/tests/test_optimise_boards.py
git commit -m "woodbuild: 1D cutting-stock that minimises cost, ties broken by waste"
```

---

### Task 5: Framing derivation

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/frame.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_frame.py`

**Interfaces:**
- Consumes: `BuildSpec`, `Part`, `stock`.
- Produces: `stud_positions(length, spacing) -> list[float]`; `header_depth_for_span(span) -> float` (span/20 rounded up to the next stock depth); `derive(spec) -> list[Part]` covering plates, studs, corners, openings, rafters, purlin, blocking, floor, roof deck, siding, sheathing, doors, glazing; `summary(parts) -> dict` (counts by assembly).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_frame.py
import json
import unittest

from woodbuild.frame import derive, header_depth_for_span, stud_positions, summary
from woodbuild.spec import BuildSpec
from woodbuild import stock

SPEC = {
    "build": "unit-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["smartside_grooved", "osb_7_16", "2x4"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span", "deck": "osb_7_16",
             "covering": "corrugated_steel", "build_up": 120.0},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None, "mullions": 4,
         "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},
        {"wall": "left", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": 1508.0, "header": None},
        {"wall": "right", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": 1508.0, "header": None},
    ],
    "substitutions": [],
    "pricing": {"store": "7011", "search": {}},
    "options": {},
}


def spec():
    s = BuildSpec(json.loads(json.dumps(SPEC)))
    s.validate()
    return s


class TestFrame(unittest.TestCase):
    def test_stud_positions_cover_the_wall(self):
        pos = stud_positions(2438.4, 406.4)
        self.assertEqual(pos[0], 0.0)
        self.assertAlmostEqual(pos[-1], 2438.4)
        self.assertTrue(all(b - a <= 406.4 + 1e-6 for a, b in zip(pos, pos[1:])))

    def test_header_depth_rule(self):
        self.assertEqual(header_depth_for_span(1386.84), 89.0)    # <= span/20 = 69 -> 2x4 depth
        self.assertEqual(header_depth_for_span(3000.0), 184.0)    # span/20 = 150 -> 2x8

    def test_every_part_has_a_known_stock_class(self):
        from woodbuild import stock
        for p in derive(spec()):
            self.assertTrue(p.stock in stock.SHEETS or p.stock in stock.BOARDS,
                            "unknown stock on %s: %s" % (p.id, p.stock))

    def test_openings_are_framed_on_both_sides(self):
        parts = derive(spec())
        kings = [p for p in parts if p.assembly == "front_door" and p.id.startswith("king")]
        self.assertEqual(sum(p.qty for p in kings), 2)

    def test_corners_are_three_stud_assemblies(self):
        parts = derive(spec())
        corners = [p for p in parts if p.assembly == "corner_FL"]
        self.assertEqual(sum(p.qty for p in corners if p.id.startswith("corner_stud")), 3)

    def test_floor_structure_sits_below_the_datum(self):
        parts = derive(spec())
        joists = [p for p in parts if p.assembly == "floor"]
        self.assertTrue(any(p.id.startswith("skid") for p in joists))
        self.assertTrue(any(p.id.startswith("deck") for p in joists))

    def test_roof_has_rafters_purlin_and_deck(self):
        ids = [p.id for p in derive(spec()) if p.assembly == "roof"]
        self.assertTrue(any(i.startswith("rafter") for i in ids))
        self.assertIn("purlin", ids)
        self.assertTrue(any(i.startswith("roof_deck") for i in ids))

    def test_glazing_parts_use_polycarbonate(self):
        panes = [p for p in derive(spec()) if p.id.startswith(("band_pane", "transom_pane"))]
        self.assertTrue(panes)
        self.assertTrue(all(p.stock == "polycarbonate_6" for p in panes))
        # glazing is the band height minus two 40 mm rails, not the whole band
        band_pane = [p for p in panes if p.id.startswith("band_pane")][0]
        self.assertAlmostEqual(band_pane.h, 220.0)

    def test_surfaces_are_panelised_to_fit_a_sheet(self):
        s = spec()
        sw, sh = stock.sheet_size("smartside_grooved")
        for p in derive(s):
            if p.id.startswith(("sheathing_", "siding_", "deck", "roof_deck")):
                self.assertLessEqual(max(p.w, p.h), max(sw, sh) + 1e-6, p.id)
                self.assertLessEqual(min(p.w, p.h), min(sw, sh) + 1e-6, p.id)
                self.assertGreater(p.qty, 0)

    def test_studs_stop_at_the_roof_underside(self):
        s = spec()
        stud = [p for p in derive(s) if p.id == "stud_front"][0]
        self.assertAlmostEqual(stud.w, s.wall_top_front())
        self.assertAlmostEqual(stud.w, 2138.06, places=1)   # 2258.06 - 120 mm build-up

    def test_door_opening_has_no_sill_plate(self):
        ids = [p.id for p in derive(spec())]
        self.assertNotIn("sill_front_door", ids)
        self.assertIn("sill_front_band", ids)

    def test_walls_have_blocking_at_the_bearing_line(self):
        parts = derive(spec())
        blocking = [p for p in parts if p.id.startswith("blocking_")]
        self.assertEqual(len(blocking), 4)                 # one run per wall
        front = [p for p in blocking if p.id == "blocking_front"][0]
        self.assertEqual(front.qty, 7)                     # 8 stud positions -> 7 bays

    def test_blocking_fits_the_actual_bay(self):
        # studs sit at span/n, so the clear bay is the step minus a stud's thickness
        parts = derive(spec())
        front = [p for p in parts if p.id == "blocking_front"][0]
        self.assertAlmostEqual(front.w, 2788.92 / 8 - 38.0, places=1)    # 310.6 mm
        left = [p for p in parts if p.id == "blocking_left"][0]
        self.assertAlmostEqual(left.w, 2179.32 / 7 - 38.0, places=1)     # 273.3 mm

    def test_glazing_is_panelised_too(self):
        # a pane wider than a 610 x 1220 polycarbonate sheet must be split
        s = spec()
        sw, sh = stock.sheet_size("polycarbonate_6")
        for p in derive(s):
            if p.id.startswith(("band_pane", "transom_pane")):
                self.assertLessEqual(max(p.w, p.h), max(sw, sh) + 1e-6, p.id)
                self.assertLessEqual(min(p.w, p.h), min(sw, sh) + 1e-6, p.id)

    def test_summary_counts_by_assembly(self):
        s = summary(derive(spec()))
        self.assertIn("wall_front", s)
        self.assertGreater(s["floor"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_frame -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.frame'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/frame.py
"""Derive a stick-framed build from the envelope.

The reference structure supplies the surfaces and the critical dimensions; the
framing schedule is derived here, because a reference model of a moulded panel
shed contains no studs, plates, headers or rafters.
"""

import math

from . import stock
from .optimise import Part

STUD_SPACING_DEFAULT = 406.4
WALL_NAMES = ("front", "back", "left", "right")


def stud_positions(length, spacing):
    """Stud centre lines from 0 to length, closing the run with an end stud."""
    if length <= 0:
        return []
    n = max(1, int(math.ceil(length / spacing)))
    step = length / n
    return [round(i * step, 2) for i in range(n + 1)]


def header_depth_for_span(span):
    """Conventional span rule: header depth >= span/20, rounded up to stock depth."""
    need = span / 20.0
    depths = sorted({stock.board_dims(cls)[1] for cls in stock.BOARDS if cls != "pt_4x4"})
    for d in depths:
        if d >= need:
            return d
    return depths[-1]


def header_class_for_span(span):
    depth = header_depth_for_span(span)
    for cls in ("2x4", "2x6", "2x8"):
        if stock.board_dims(cls)[1] >= depth:
            return cls
    return "2x8"


def _wall_span(spec, wall):
    env = spec.envelope
    return env["width"] if wall in ("front", "back") else env["depth"]


def _split_surface(pid, w, h, cls, assembly, note, grain_locked=True):
    """Tile a surface into sheet-sized panels.

    A 2788.92 mm wall face cannot come off a 1219 mm sheet, so every surface is
    panelised before it reaches the optimiser. One Part per distinct tile size
    (qty = tile count) keeps the cutlist readable.
    """
    sw, sh = stock.sheet_size(cls)
    gap = stock.KERF
    nx = max(1, int(math.ceil(w / (sw - gap))))
    ny = max(1, int(math.ceil(h / (sh - gap))))
    tw = (w - gap * (nx - 1)) / nx
    th = (h - gap * (ny - 1)) / ny
    if tw > sw - gap or th > sh - gap:
        raise ValueError("panel %s still exceeds a %s sheet: %.1f x %.1f"
                         % (pid, cls, tw, th))
    return Part(id=pid, w=round(tw, 2), h=round(th, 2), qty=nx * ny, stock=cls,
                assembly=assembly, grain_locked=grain_locked,
                note="%s (%d x %d panels)" % (note, nx, ny))


def _wall_plates(spec, wall, parts):
    env = spec.envelope
    span = _wall_span(spec, wall)
    sole = Part(id="sole_plate_%s" % wall, w=span, h=stock.board_dims("pt_2x4")[1],
                qty=1, stock="pt_2x4", assembly="wall_%s" % wall,
                note="PT sole plate, ground contact")
    top = Part(id="top_plate_%s" % wall, w=span, h=stock.board_dims("2x4")[1],
               qty=2, stock="2x4", assembly="wall_%s" % wall,
               note="single top plate + bearing plate (sloped bearing cut on site)")
    parts.extend([sole, top])


def _wall_studs(spec, wall, parts):
    span = _wall_span(spec, wall)
    spacing = float(spec.data["wall"].get("spacing", STUD_SPACING_DEFAULT))
    studs = stud_positions(span, spacing)
    # studs stop at the roof underside, not the roof top: the 120 mm build-up is
    # rafters, deck and steel, none of which a stud spans
    parts.append(Part(id="stud_%s" % wall, w=round(spec.wall_top_front(), 2),
                      h=stock.board_dims("2x4")[1], qty=len(studs), stock="2x4",
                      assembly="wall_%s" % wall,
                      note="studs @ %.1f mm o.c." % spacing))


def _blocking(spec, wall, parts):
    """Solid blocking between studs at the roof bearing line."""
    span = _wall_span(spec, wall)
    spacing = float(spec.data["wall"].get("spacing", STUD_SPACING_DEFAULT))
    positions = stud_positions(span, spacing)
    bays = max(0, len(positions) - 1)
    if bays:
        # studs are laid out evenly at span/n, not at the nominal spacing, so the
        # clear bay is step - stud thickness (the nominal spacing would over-length
        # blocking by 8 mm on the long walls and 43 mm on the side walls)
        step = span / len(positions)
        parts.append(Part(id="blocking_%s" % wall,
                          w=round(step - stock.board_dims("2x4")[0], 2),
                          h=stock.board_dims("2x4")[1], qty=bays, stock="2x4",
                          assembly="wall_%s" % wall,
                          note="blocking at the roof bearing line"))


def _corners(spec, parts):
    for tag in ("FL", "FR", "BL", "BR"):
        parts.append(Part(id="corner_stud_" + tag, w=round(spec.wall_top_front(), 2),
                          h=stock.board_dims("2x4")[1], qty=3, stock="2x4",
                          assembly="corner_%s" % tag,
                          note="3-stud corner replacing the moulded 45x45 post"))


def _opening_frame(spec, opening, parts):
    wall = opening["wall"]
    kind = opening["kind"]
    width = float(opening["width"])
    height = float(opening["height"])
    head = float(opening["sill"]) + height
    assembly = "%s_%s" % (wall, kind)
    tall = round(spec.wall_top_front(), 2)

    header_cls = opening.get("header") or header_class_for_span(width)
    # ids carry the wall: a left and a right transom are different parts
    parts.append(Part(id="king_%s_%s" % (wall, kind), w=tall,
                      h=stock.board_dims("2x4")[1],
                      qty=2, stock="2x4", assembly=assembly,
                      note="king studs both sides of the opening"))
    parts.append(Part(id="jack_%s_%s" % (wall, kind), w=height,
                      h=stock.board_dims("2x4")[1],
                      qty=2, stock="2x4", assembly=assembly, note="jack/trim studs"))
    parts.append(Part(id="header_%s_%s" % (wall, kind), w=width,
                      h=stock.board_dims(header_cls)[1], qty=2, stock=header_cls,
                      assembly=assembly, note="doubled header, %s" % header_cls))
    cripple_len = tall - head
    if cripple_len > 50.0:
        n = max(1, int(math.ceil(width / 406.4)) - 1)
        parts.append(Part(id="cripple_%s_%s" % (wall, kind), w=round(cripple_len, 2),
                          h=stock.board_dims("2x4")[1], qty=n, stock="2x4",
                          assembly=assembly, note="cripples above the head"))
    if kind != "door":                      # a door has no sill plate to trip over
        parts.append(Part(id="sill_%s_%s" % (wall, kind), w=width,
                          h=stock.board_dims("2x4")[1],
                          qty=1, stock="2x4", assembly=assembly, note="sill plate"))


def _glazing(spec, parts):
    band = [o for o in spec.openings("front") if o["kind"] == "band"]
    if band:
        b = band[0]
        panes = b.get("panes", [1])
        mullions = int(b.get("mullions", len(panes) - 1))
        usable = float(b["width"])
        total = float(sum(panes))
        glass_h = float(b["height"]) - 2.0 * float(spec.data.get("band_rail", 40.0))
        for i, frac in enumerate(panes, start=1):
            # panes are panelised too: a legal single-pane band is 2610.92 mm wide
            # and a polycarbonate sheet is 610 x 1220
            parts.append(_split_surface("band_pane_%d" % i,
                                        round(usable * frac / total, 2),
                                        round(glass_h, 2), "polycarbonate_6",
                                        "glazing_front",
                                        "clerestory pane %d of %d" % (i, len(panes)),
                                        grain_locked=False))
        parts.append(Part(id="band_mullion", w=round(float(b["height"]), 2),
                          h=stock.board_dims("2x4")[1], qty=mullions, stock="2x4",
                          assembly="glazing_front", note="mullions between panes"))
    for wall in ("left", "right"):
        for o in spec.openings(wall):
            if o["kind"] == "transom":
                parts.append(_split_surface("transom_pane_%s" % wall,
                                            float(o["width"]), float(o["height"]),
                                            "polycarbonate_6", "glazing_%s" % wall,
                                            "side transom glazing",
                                            grain_locked=False))


def _floor(spec, parts):
    env = spec.envelope
    f = spec.data["floor"]
    build_up = float(f["build_up"])
    clear_w = env["width"] - 2 * spec.wall_build_up()
    clear_d = env["depth"] - 2 * spec.wall_build_up()
    parts.append(Part(id="skid", w=env["depth"], h=stock.board_dims(f["skids"])[1],
                      qty=3, stock=f["skids"], assembly="floor",
                      note="PT skids below the datum (%.1f mm total build-up)" % build_up))
    spacing = float(f.get("spacing", 406.4))
    n_joists = len(stud_positions(clear_d, spacing))
    parts.append(Part(id="joist", w=clear_w, h=stock.board_dims(f["joist"])[1],
                      qty=n_joists, stock=f["joist"], assembly="floor",
                      note="PT joists @ %.1f mm o.c." % spacing))
    w, h = stock.sheet_size(f["deck"])
    parts.append(_split_surface("deck", clear_w, clear_d, f["deck"], "floor",
                                "T&G deck, %dx%d mm sheets" % (w, h)))


def _roof(spec, parts):
    env = spec.envelope
    r = spec.data["roof"]
    spacing = float(r.get("spacing", 304.8))
    n_rafters = len(stud_positions(env["depth"], spacing))
    parts.append(Part(id="rafter", w=env["depth"], h=stock.board_dims(r["rafter"])[1],
                      qty=n_rafters, stock=r["rafter"], assembly="roof",
                      note="rafters @ %.1f mm o.c., mid-span purlin" % spacing))
    parts.append(Part(id="purlin", w=env["width"], h=stock.board_dims("2x4")[1],
                      qty=1, stock="2x4", assembly="roof", note="mid-span purlin"))
    ov = r.get("overhang", {})
    w = env["width"] + 2 * float(ov.get("side", 0.0))
    d = env["depth"] + float(ov.get("front", 0.0)) + float(ov.get("back", 0.0))
    parts.append(_split_surface("roof_deck", w, d, r["deck"], "roof",
                                "OSB deck + steel covering"))


def _walls(spec, parts):
    env = spec.envelope
    for wall in WALL_NAMES:
        span = _wall_span(spec, wall)
        h = round(spec.wall_top_front(), 2)
        parts.append(_split_surface("sheathing_%s" % wall, span, h, "osb_7_16",
                                    "wall_%s" % wall, "OSB sheathing"))
        parts.append(_split_surface("siding_%s" % wall, span, h, "smartside_grooved",
                                    "wall_%s" % wall,
                                    "grooved siding laid horizontally"))
        _wall_plates(spec, wall, parts)
        _wall_studs(spec, wall, parts)
        _blocking(spec, wall, parts)


def _doors(spec, parts):
    doors = [o for o in spec.openings() if o["kind"] == "door"]
    for o in doors:
        leaf_w = float(o["width"]) / 2.0
        leaf_h = float(o["height"]) - 4.0
        parts.append(Part(id="leaf_skin", w=leaf_w, h=leaf_h, qty=2,
                          stock="plywood_ext_18", assembly="doors", grain_locked=True,
                          note="exterior plywood skin per leaf"))
        parts.append(Part(id="leaf_frame_rail", w=leaf_w, h=stock.board_dims("2x4")[1],
                          qty=4, stock="2x4", assembly="doors"))
        parts.append(Part(id="leaf_frame_stile", w=leaf_h, h=stock.board_dims("2x4")[1],
                          qty=4, stock="2x4", assembly="doors"))


def derive(spec):
    spec.validate()
    parts = []
    _walls(spec, parts)
    _corners(spec, parts)
    for o in spec.openings():
        _opening_frame(spec, o, parts)
    _glazing(spec, parts)
    _floor(spec, parts)
    _roof(spec, parts)
    _doors(spec, parts)
    return parts


def summary(parts):
    out = {}
    for p in parts:
        out[p.assembly] = out.get(p.assembly, 0) + p.qty
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_frame -v`
Expected: PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/frame.py skills/building-from-reference/scripts/tests/test_frame.py
git commit -m "woodbuild: derive stick framing, openings, floor and roof from the spec"
```

---

### Task 6: Bill of materials and derived consumables

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/bom.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_bom.py`

**Interfaces:**
- Consumes: `Part`, `SheetPlan`, `BoardPlan`, `stock`.
- Produces: `@dataclass BomLine(category, stock, description, qty, uom, unit_price=None, sku=None, source=None, note="")` with `.line_total()`; `build_bom(parts, sheet_plans, board_plans, prices=None, spec=None) -> list[BomLine]`; `consumables(spec, parts) -> list[BomLine]`; `subtotal(lines) -> float`; `unpriced(lines) -> list[BomLine]`; `totals(lines, tax_rate) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bom.py
import unittest

from woodbuild.bom import (BomLine, build_bom, consumables, subtotal, totals,
                           unpriced)
from woodbuild.optimise import BoardPlan, Part, SheetPlan


class TestBom(unittest.TestCase):
    def test_sheets_become_one_line_each(self):
        plans = [SheetPlan(stock="osb_7_16", sheets=[[], []]),
                 SheetPlan(stock="polycarbonate_6", sheets=[[]])]
        lines = build_bom([], plans, [])
        self.assertEqual(len(lines), 2)
        by_stock = {l.stock: l for l in lines}
        self.assertEqual(by_stock["osb_7_16"].qty, 2)
        self.assertEqual(by_stock["osb_7_16"].uom, "sheet")
        self.assertEqual(by_stock["osb_7_16"].category, "sheets")
        self.assertEqual(by_stock["polycarbonate_6"].category, "glazing")

    def test_boards_become_one_line_per_length(self):
        plans = [BoardPlan(stock="2x4", length_mm=2438.4, count=7, cuts=[]),
                 BoardPlan(stock="2x4", length_mm=4876.8, count=2, cuts=[])]
        lines = build_bom([], [], plans)
        self.assertEqual(len(lines), 2)
        notes = " ".join(l.description for l in lines)
        self.assertIn("8 ft", notes)
        self.assertIn("16 ft", notes)

    def test_prices_attach_by_stock_class(self):
        plans = [SheetPlan(stock="osb_7_16", sheets=[[], []])]
        prices = {"osb_7_16": {"price": 28.98, "sku": "123", "source": "hd_product",
                               "desc": '7/16" OSB'}}
        line = build_bom([], plans, [], prices=prices)[0]
        self.assertAlmostEqual(line.unit_price, 28.98)
        self.assertEqual(line.sku, "123")
        self.assertAlmostEqual(line.line_total(), 57.96)

    def test_missing_price_is_unpriced_not_zero(self):
        plans = [SheetPlan(stock="osb_7_16", sheets=[[]])]
        line = build_bom([], plans, [], prices={})[0]
        self.assertIsNone(line.unit_price)
        self.assertIsNone(line.line_total())
        self.assertEqual([l.stock for l in unpriced([line])], ["osb_7_16"])

    def test_parts_only_bom_omits_consumables(self):
        # no spec -> the caller wants the priced plan only (this is how the tests
        # below read one line per stock class)
        lines = build_bom([], [SheetPlan(stock="osb_7_16", sheets=[[]])], [])
        self.assertEqual([l.category for l in lines], ["sheets"])
        # with a spec the derived fasteners, sealant and hardware come along
        with_consumables = build_bom([], [], [], spec={"options": {}})
        self.assertTrue(any(l.category == "fasteners" for l in with_consumables))

    def test_consumables_scale_with_joints(self):
        parts = [Part(id="stud", w=2000.0, h=89.0, qty=10, stock="2x4"),
                 Part(id="deck", w=2500.0, h=1900.0, qty=1, stock="plywood_tg_18")]
        cons = consumables({"options": {}}, parts)
        kinds = {c.description.split(" ")[0] for c in cons}
        self.assertIn("3\"", kinds)
        self.assertTrue(all(c.unit_price is None for c in cons))

    def test_totals_apply_hst(self):
        lines = [BomLine("lumber", "2x4", "2x4 SPF", 10, "each", 4.25),
                 BomLine("lumber", "2x6", "2x6 SPF", 2, "each", 9.98, sku=None)]
        t = totals(lines, 0.13)
        self.assertAlmostEqual(t["subtotal"], 10 * 4.25 + 2 * 9.98, places=2)
        self.assertAlmostEqual(t["tax"], round(t["subtotal"] * 0.13, 2), places=2)
        self.assertAlmostEqual(t["total"], round(t["subtotal"] + t["tax"], 2), places=2)
        self.assertEqual(t["unpriced"], 0)

    def test_subtotal_ignores_unpriced_lines(self):
        lines = [BomLine("lumber", "2x4", "x", 1, "each", 5.0),
                 BomLine("lumber", "2x6", "y", 1, "each", None)]
        self.assertAlmostEqual(subtotal(lines), 5.0)
        self.assertEqual(totals(lines, 0.13)["unpriced"], 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_bom -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.bom'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/bom.py
"""Buy plan -> SKU lines, plus consumables derived from the part list."""

from dataclasses import dataclass

from . import stock


@dataclass
class BomLine:
    category: str
    stock: str
    description: str
    qty: float
    uom: str
    unit_price: float = None
    sku: str = None
    source: str = None
    note: str = ""

    def line_total(self):
        if self.unit_price is None:
            return None
        return round(self.unit_price * self.qty, 2)


def _price_for(prices, cls):
    if not prices:
        return None
    entry = prices.get(cls)
    if not entry or entry.get("price") is None:
        return None
    return entry


def build_bom(parts, sheet_plans, board_plans, prices=None, spec=None):
    lines = []
    for plan in sheet_plans:
        entry = _price_for(prices, plan.stock)
        lines.append(BomLine(
            category=stock.category(plan.stock), stock=plan.stock,
            description=stock.label(plan.stock), qty=plan.count,
            uom=stock.unit_label(plan.stock),
            unit_price=(entry or {}).get("price"), sku=(entry or {}).get("sku"),
            source=(entry or {}).get("source"),
            note="yield %.1f%%" % plan.yield_pct()))
    for plan in board_plans:
        ft = plan.length_mm / stock.FT
        entry = _price_for(prices, plan.stock)
        lines.append(BomLine(
            category=stock.category(plan.stock), stock=plan.stock,
            description="%s - %g ft" % (stock.label(plan.stock), round(ft)),
            qty=plan.count, uom=stock.unit_label(plan.stock),
            unit_price=(entry or {}).get("price"), sku=(entry or {}).get("sku"),
            source=(entry or {}).get("source"),
            note="yield %.1f%%" % plan.yield_pct()))
    if spec is not None:                     # a parts-only BOM omits the consumables
        lines.extend(consumables(spec, parts))
    lines.sort(key=lambda l: (l.category, l.stock, l.description))
    return lines


def consumables(spec, parts):
    """Fasteners, adhesive and sealant derived from geometry, never guessed."""
    total_end_mm = 0.0
    sheathing_perimeter_mm = 0.0
    for p in parts:
        if p.stock in stock.BOARDS:
            total_end_mm += p.w * p.qty
        if p.id.startswith(("sheathing_", "deck", "roof_deck")):
            perim = 2 * (p.w + p.h)
            sheathing_perimeter_mm += perim * p.qty
    screws = int(total_end_mm / 300.0 * 3)                  # 3 screws per connection point
    nails = int(sheathing_perimeter_mm / 150.0 + sheathing_perimeter_mm / 300.0)
    adhesive_tubes = max(1, int(total_end_mm / 8000.0))
    sealant_tubes = max(1, int(sheathing_perimeter_mm / 12000.0))
    out = [
        BomLine("fasteners", "screws_3in", '3" exterior structural screws',
                max(1, screws // 100 + 1), "box", None, None, None,
                "%d screws estimated from %d mm of framing" % (screws, int(total_end_mm))),
        BomLine("fasteners", "nails_8d", "8d galvanised sheathing nails",
                max(1, nails // 500 + 1), "box", None, None, None,
                "%d nails estimated from %d mm of panel perimeter" % (nails, int(sheathing_perimeter_mm))),
        BomLine("fasteners", "adhesive", "construction adhesive", adhesive_tubes, "tube"),
        BomLine("finish", "sealant", "exterior sealant / caulk", sealant_tubes, "tube"),
        BomLine("hardware", "hinges", "shed door hinges (pair per leaf)",
                4, "each", None, None, None, "3 per leaf, 2 leaves"),
        BomLine("hardware", "hasp", "hasp and staple + cylinder lock", 1, "set"),
        BomLine("vents", "louvre_12x18", '12 x 18 in aluminium louvre',
                2, "each", None, None, None,
                "replaces the moulded triangular vent (deviation)"),
        BomLine("roof", "steel_roof", "corrugated steel roofing panel",
                1, "each", None, None, None, "cut to the pent roof span"),
        BomLine("base", "gravel", "compacted gravel / pavers for the pad",
                1, "load", None, None, None, "the reference needs level ground only"),
    ]
    return out


def unpriced(lines):
    return [l for l in lines if l.unit_price is None]


def subtotal(lines):
    return round(sum(l.line_total() for l in lines if l.line_total() is not None), 2)


def totals(lines, tax_rate):
    sub = subtotal(lines)
    tax = round(sub * tax_rate, 2)
    return {"subtotal": sub, "tax": tax, "total": round(sub + tax, 2),
            "unpriced": len(unpriced(lines)),
            "lines": len(lines)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_bom -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/bom.py skills/building-from-reference/scripts/tests/test_bom.py
git commit -m "woodbuild: BOM lines, derived consumables, HST totals"
```

---

### Task 7: Price cache and MCP stdio client

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/pricing.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_pricing.py`

**Interfaces:**
- Consumes: `spec.search_terms()`, `stock.label`.
- Produces: `class PriceCache(path)` with `.load()`, `.save()`, `.get(cls)`, `.is_stale(cls, days=7)`, `.store`, `.province`, `.fetched`, `.unpriced`; `class StdioMCP(command, args, env=None)` with `.call(tool, arguments) -> dict` and `.close()`; `resolve(spec, cache, transport=None, refresh=False, today=None) -> dict` returning `{cls: entry}`; `compare(old, new) -> list[tuple[cls, old_price, new_price]]`; `TAX_RATES = {"ON": 0.13, "AB": 0.05, "BC": 0.12, "QC": 0.14975}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pricing.py
import json
import os
import tempfile
import unittest

from woodbuild.pricing import PriceCache, compare, resolve
from woodbuild.spec import BuildSpec


class FakeTransport:
    """Stands in for the Home Depot MCP server."""

    def __init__(self, results):
        self.results = results
        self.calls = []

    def call(self, tool, arguments):
        self.calls.append((tool, arguments))
        return self.results.get(arguments.get("query") or arguments.get("sku"), {})


def make_spec(search):
    return BuildSpec({"pricing": {"store": "7011", "search": search}})


def tmp_path():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(p)
    return p


SEARCH_HIT = {"products": [{"sku": "1000123456", "name": "2x4x8 SPF Stud",
                            "price": 4.25, "url": "https://example/1000123456",
                            "inStockOnline": True}]}
SEARCH_MISS_PRICE = {"products": [{"sku": "1000999999", "name": "7/16 OSB",
                                   "price": None, "url": "https://example/x",
                                   "inStockOnline": False}]}


class TestPricing(unittest.TestCase):
    def test_resolve_from_cache_offline(self):
        path = tmp_path()
        cache = PriceCache(path)
        cache.data = {"store": "7011", "province": "ON",
                      "items": {"2x4": {"sku": "1000123456", "price": 4.19,
                                        "source": "hd_search"}}}
        cache.save()
        spec = make_spec({"2x4": "2x4x8 SPF stud"})
        prices = resolve(spec, PriceCache(path), transport=None)
        self.assertEqual(prices["2x4"]["price"], 4.19)

    def test_fetch_uses_search_terms_and_stamps_provenance(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "7011", "province": "ON", "items": {}}
        spec = make_spec({"2x4": "2x4x8 SPF stud"})
        transport = FakeTransport({"2x4x8 SPF stud": SEARCH_HIT})
        prices = resolve(spec, cache, transport=transport, refresh=True,
                         today="2026-09-12")
        self.assertEqual(transport.calls[0][0], "hd_search")
        self.assertEqual(transport.calls[0][1]["storeId"], "7011")
        self.assertEqual(prices["2x4"]["sku"], "1000123456")
        self.assertEqual(prices["2x4"]["price"], 4.25)
        self.assertEqual(prices["2x4"]["source"], "hd_search")
        self.assertEqual(prices["2x4"]["fetched"], "2026-09-12")

    def test_null_price_is_recorded_as_unpriced_with_reason(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "7011", "province": "ON", "items": {}}
        spec = make_spec({"osb_7_16": "7/16 OSB sheathing"})
        transport = FakeTransport({"7/16 OSB sheathing": SEARCH_MISS_PRICE})
        prices = resolve(spec, cache, transport=transport, refresh=True,
                         today="2026-09-12")
        self.assertIsNone(prices.get("osb_7_16", {}).get("price"))
        self.assertEqual(cache.data["unpriced"]["osb_7_16"]["reason"],
                         "null price returned")
        self.assertIn("hd_search", cache.data["unpriced"]["osb_7_16"]["tried"])

    def test_cache_persists_and_marks_staleness(self):
        path = tmp_path()
        cache = PriceCache(path)
        cache.data = {"store": "7011", "province": "ON",
                      "items": {"2x4": {"sku": "1", "price": 4.19,
                                        "fetched": "2026-09-01"}}}
        cache.save()
        again = PriceCache(path)
        again.load()
        self.assertEqual(again.get("2x4")["price"], 4.19)
        self.assertTrue(again.is_stale("2x4", days=7, today="2026-09-12"))
        self.assertFalse(again.is_stale("2x4", days=30, today="2026-09-12"))

    def test_offline_run_does_not_invent_a_price(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "7011", "province": "ON", "items": {}}
        spec = make_spec({"2x8": "2x8 SPF"})
        prices = resolve(spec, cache, transport=None)
        self.assertEqual(prices, {})

    def test_compare_reports_deltas(self):
        old = {"items": {"2x4": {"price": 4.19}, "2x6": {"price": 9.98}}}
        new = {"items": {"2x4": {"price": 4.49}, "2x6": {"price": 9.98}}}
        deltas = compare(old, new)
        self.assertEqual(deltas, [("2x4", 4.19, 4.49, 0.30)])

    def test_tax_rate_lookup(self):
        from woodbuild.pricing import tax_rate_for
        self.assertEqual(tax_rate_for("ON"), 0.13)
        self.assertEqual(tax_rate_for("AB"), 0.05)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_pricing -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.pricing'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/pricing.py
"""Cache-first pricing. Never invents a number: a missing price is reported."""

import json
import os
import subprocess
from datetime import date

TAX_RATES = {"ON": 0.13, "AB": 0.05, "BC": 0.12, "QC": 0.14975,
             "MB": 0.12, "SK": 0.11, "NS": 0.15, "NB": 0.15, "NL": 0.15, "PE": 0.15}


def tax_rate_for(province):
    return TAX_RATES.get(province, 0.13)


class PriceCache:
    def __init__(self, path):
        self.path = path
        self.data = {"store": None, "storeName": None, "province": None,
                     "currency": "CAD", "fetched": None, "items": {}, "unpriced": {}}

    def load(self):
        if os.path.exists(self.path):
            with open(self.path) as fh:
                self.data = json.load(fh)
        return self.data

    def save(self):
        with open(self.path, "w") as fh:
            json.dump(self.data, fh, indent=2, sort_keys=True)
            fh.write("\n")

    # accessors
    @property
    def store(self):
        return self.data.get("store")

    @property
    def province(self):
        return self.data.get("province")

    @property
    def fetched(self):
        return self.data.get("fetched")

    @property
    def unpriced(self):
        return self.data.get("unpriced", {})

    def get(self, cls):
        return self.data.get("items", {}).get(cls)

    def put(self, cls, entry):
        self.data.setdefault("items", {})[cls] = entry

    def mark_unpriced(self, cls, reason, tried):
        self.data.setdefault("unpriced", {})[cls] = {"reason": reason, "tried": tried}

    def is_stale(self, cls, days=7, today=None):
        entry = self.get(cls)
        if not entry or not entry.get("fetched"):
            return True
        ref = date.fromisoformat(today) if today else date.today()
        got = date.fromisoformat(entry["fetched"])
        return (ref - got).days > days


class StdioMCP:
    """Minimal MCP stdio client: enough for tools/call on the Home Depot server."""

    def __init__(self, command, args, env=None):
        self.proc = subprocess.Popen([command] + list(args), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, bufsize=1,
                                     env=env or os.environ.copy())
        self._id = 0
        self._send({
            "jsonrpc": "2.0", "id": self._next(), "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "woodbuild", "version": "0.1.0"}}})
        self._read()
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized",
                    "params": {}})

    def _next(self):
        self._id += 1
        return self._id

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read(self):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            try:
                return json.loads(line)
            except ValueError:
                continue

    def call(self, tool, arguments):
        self._send({"jsonrpc": "2.0", "id": self._next(), "method": "tools/call",
                    "params": {"name": tool, "arguments": arguments}})
        reply = self._read() or {}
        content = (reply.get("result") or {}).get("content") or []
        for block in content:
            if block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except ValueError:
                    return {"text": block["text"]}
        return {}

    def close(self):
        try:
            self.proc.terminate()
        except Exception:
            pass


def _entry_from_search(cls, payload, today):
    products = payload.get("products") or []
    for p in products:
        if p.get("price") is not None:
            return {"sku": p.get("sku"), "price": float(p["price"]),
                    "desc": p.get("name"), "url": p.get("url"),
                    "inStock": p.get("inStockOnline"),
                    "source": "hd_search", "fetched": today}
    return None


def resolve(spec, cache, transport=None, refresh=False, today=None):
    """Return {stock class: price entry}. Offline unless refresh and a transport."""
    today = today or date.today().isoformat()
    if spec.data.get("pricing", {}).get("store"):
        cache.data.setdefault("store", spec.data["pricing"]["store"])
    if spec.data.get("pricing", {}).get("province"):
        cache.data.setdefault("province", spec.data["pricing"]["province"])
    terms = spec.search_terms()
    if not terms and spec.data.get("pricing", {}).get("store"):
        # sensible defaults when the spec lists no search terms
        terms = {}
    for cls, query in terms.items():
        entry = cache.get(cls)
        if entry and not refresh and not cache.is_stale(cls, days=7, today=today):
            continue
        if transport is None:
            continue
        payload = transport.call("hd_search", {"query": query,
                                               "storeId": cache.store or "9999",
                                               "pageSize": 5})
        found = _entry_from_search(cls, payload or {}, today)
        if found:
            cache.put(cls, found)
            cache.data.get("unpriced", {}).pop(cls, None)
        else:
            cache.mark_unpriced(cls, "null price returned", ["hd_search"])
    cache.data["fetched"] = today
    return {cls: e for cls, e in cache.data.get("items", {}).items()
            if cls in terms or not terms}


def compare(old, new):
    """Price deltas, sorted by class. Returns [(class, old, new, delta)]."""
    out = []
    for cls in sorted(set(old.get("items", {})) | set(new.get("items", {}))):
        a = (old.get("items", {}).get(cls) or {}).get("price")
        b = (new.get("items", {}).get(cls) or {}).get("price")
        if a is None and b is None:
            continue
        if a != b:
            out.append((cls, a, b, round((b or 0) - (a or 0), 2)))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_pricing -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/pricing.py skills/building-from-reference/scripts/tests/test_pricing.py
git commit -m "woodbuild: cache-first pricing with MCP stdio fetch and cache diff"
```

---

### Task 8: Workbook and exports

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/report.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_report.py`

**Interfaces:**
- Consumes: `BuildSpec`, `Part`, `SheetPlan`, `BoardPlan`, `BomLine`, `totals`, `PriceCache`, `tax_rate_for`.
- Produces: `write_report(spec, parts, sheet_plans, board_plans, lines, cache, out_dir, today=None) -> dict[str, str]` writing `budget.html`, `cutlist.csv`, `cart.csv`, `sku-qty.txt`; `render_html(...) -> str`; `cutlist_rows(parts, sheet_plans, board_plans) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
import json
import os
import shutil
import tempfile
import unittest

from woodbuild.bom import BomLine, build_bom, totals
from woodbuild.optimise import BoardPlan, Part, SheetPlan
from woodbuild.pricing import PriceCache
from woodbuild.report import cutlist_rows, render_html, write_report
from woodbuild.spec import BuildSpec

SPEC = {
    "build": "unit-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["smartside_grooved", "osb_7_16", "2x4"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "deck": "osb_7_16",
             "build_up": 120.0, "overhang": {"front": 60, "back": 40, "side": 45}},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None, "mullions": 4,
         "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},
    ],
    "substitutions": [{"ref": "45mm moulded post", "build": "3-stud 2x4 corner",
                       "consequence": "corner trim needed", "changes_diagram": True}],
    "pricing": {"store": "7011", "province": "ON", "search": {"2x4": "2x4x8 stud"}},
    "options": {},
}


class TestReport(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.spec = BuildSpec(json.loads(json.dumps(SPEC)))
        self.parts = [Part(id="stud", w=2138.06, h=89.0, qty=12, stock="2x4",
                           assembly="wall_front")]
        self.sheets = [SheetPlan(stock="osb_7_16", sheets=[[], []])]
        self.boards = [BoardPlan(stock="2x4", length_mm=2438.4, count=6,
                                 cuts=[[("stud#1", 2138.06)]])]
        prices = {"osb_7_16": {"price": 28.98, "sku": "111", "source": "hd_search"},
                  "2x4": {"price": 4.25, "sku": "222", "source": "hd_search"}}
        self.lines = build_bom(self.parts, self.sheets, self.boards, prices=prices,
                              spec=self.spec.data)
        self.cache = PriceCache(os.path.join(self.out, "prices.json"))
        self.cache.data = {"store": "7011", "storeName": "ETOBICOKE SOUTH",
                           "province": "ON", "fetched": "2026-09-12",
                           "items": prices}

    def tearDown(self):
        shutil.rmtree(self.out)

    def test_writes_four_files(self):
        paths = write_report(self.spec, self.parts, self.sheets, self.boards,
                            self.lines, self.cache, self.out, today="2026-09-12")
        for key in ("html", "cutlist", "cart", "sku_qty"):
            self.assertTrue(os.path.exists(paths[key]), key)
        self.assertEqual(os.path.basename(paths["html"]), "budget.html")
        self.assertEqual(os.path.basename(paths["cutlist"]), "cutlist.csv")
        self.assertEqual(os.path.basename(paths["cart"]), "cart.csv")
        self.assertEqual(os.path.basename(paths["sku_qty"]), "sku-qty.txt")

    def test_html_has_deviations_before_money_and_required_blocks(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                          self.lines, self.cache, today="2026-09-12")
        self.assertLess(html.index("Deviations"), html.index("Bill of materials"))
        for needle in ("ETOBICOKE", "7011", "HST", "13.0", "Sheet yields",
                       "Framing schedule", "unpriced"):
            self.assertIn(needle, html)

    def test_totals_match_bom(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                          self.lines, self.cache, today="2026-09-12")
        t = totals(self.lines, 0.13)
        self.assertIn("%.2f" % t["total"], html)

    def test_cutlist_rows_map_parts_to_sources(self):
        rows = cutlist_rows(self.parts, self.sheets, self.boards)
        self.assertEqual(rows[0]["part"], "stud")
        self.assertEqual(rows[0]["source"], "2x4 @ 8 ft")
        self.assertIn("mm", rows[0]["size"])

    def test_cart_csv_has_sku_and_qty(self):
        paths = write_report(self.spec, self.parts, self.sheets, self.boards,
                            self.lines, self.cache, self.out, today="2026-09-12")
        text = open(paths["cart"]).read()
        self.assertIn("sku", text.splitlines()[0])
        self.assertIn("111", text)
        self.assertIn("222", text)

    def test_sku_qty_is_paste_ready(self):
        paths = write_report(self.spec, self.parts, self.sheets, self.boards,
                            self.lines, self.cache, self.out, today="2026-09-12")
        lines = [l for l in open(paths["sku_qty"]).read().splitlines() if l.strip()]
        for line in lines:
            sku, qty = line.split()
            self.assertTrue(sku.isdigit())
            self.assertTrue(float(qty) > 0)

    def test_unpriced_lines_are_flagged_in_html(self):
        lines = self.lines + [BomLine("vents", "louvre_12x18", "12x18 louvre", 2, "each")]
        html = render_html(self.spec, self.parts, self.sheets, self.boards, lines,
                          self.cache, today="2026-09-12")
        self.assertIn("excludes 1 unpriced", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_report -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.report'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/report.py
"""Workbook + CSV exports. Deviations are printed before any money."""

import csv
import html as html_mod
import os

from . import stock
from .bom import totals, unpriced
from .pricing import tax_rate_for

CSS = """
body{background:#15161a;color:#e8e6e3;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:24px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 8px;color:#c8b48a}
.sub{color:#8d9096;margin:0 0 18px}
table{border-collapse:collapse;width:100%;margin:6px 0 18px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid #2c2f38;vertical-align:top}
th{color:#8d9096;font-weight:500}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 6px}
.card{background:#20222a;border:1px solid #2c2f38;border-radius:10px;padding:10px 14px;min-width:150px}
.card b{display:block;font-size:19px}.card span{color:#8d9096;font-size:12px}
.bar{background:#2c2f38;border-radius:4px;height:8px;width:120px;display:inline-block}
.bar i{display:block;height:8px;border-radius:4px;background:#7f9f6a}
.warn{color:#e0b060}tr.unpriced td{color:#e0b060}
"""


def cutlist_rows(parts, sheet_plans, board_plans):
    """One row per part with its finished size and where it comes off."""
    source = {}
    for plan in sheet_plans:
        for i, sheet in enumerate(plan.sheets, start=1):
            for pl in sheet:
                base = pl.part_id.split("#")[0]
                source[base] = "%s sheet %d" % (plan.stock, i)
    for plan in board_plans:
        for i, board in enumerate(plan.cuts, start=1):
            for pid, _ in board:
                base = pid.split("#")[0]
                source[base] = "%s @ %g ft" % (plan.stock, round(plan.length_mm / stock.FT))
    rows = []
    for p in sorted(parts, key=lambda p: (p.assembly, p.id)):
        rows.append({
            "assembly": p.assembly,
            "part": p.id,
            "qty": p.qty,
            "size": "%.1f x %.1f x %.1f mm" % (p.w, p.h, stock.thickness(p.stock)),
            "stock": p.stock,
            "grain": "locked" if p.grain_locked else "free",
            "source": source.get(p.id, "consumable / uncut"),
            "note": p.note,
        })
    return rows


def _num(v, dash="unpriced"):
    return dash if v is None else "%.2f" % v


def render_html(spec, parts, sheet_plans, board_plans, lines, cache, today=None):
    t = totals(lines, tax_rate_for(cache.province or "ON"))
    rows = cutlist_rows(parts, sheet_plans, board_plans)
    e = html_mod.escape

    out = ["<!doctype html><meta charset=utf-8>",
           "<title>Wood build budget - %s</title>" % e(spec.data.get("build", "")),
           "<style>%s</style>" % CSS,
           "<h1>%s</h1>" % e(spec.data.get("build", "build")),
           "<p class=sub>store %s &middot; %s &middot; price cache %s &middot; "
           "HST %.1f%% &middot; generated %s</p>"
           % (e(str(cache.store)), e(str(cache.data.get("storeName") or "")),
              e(str(cache.fetched)), tax_rate_for(cache.province or "ON") * 100,
              e(today or ""))]

    out.append("<div class=cards>")
    for label, value in (("subtotal", "$%.2f" % t["subtotal"]),
                         ("HST", "$%.2f" % t["tax"]),
                         ("total", "$%.2f" % t["total"]),
                         ("lines", str(t["lines"])),
                         ("unpriced", str(t["unpriced"]))):
        out.append("<div class=card><b>%s</b><span>%s</span></div>" % (value, label))
    out.append("</div>")
    if t["unpriced"]:
        out.append("<p class=warn>Total excludes %d unpriced line(s) - see the "
                   "unpriced section below.</p>" % t["unpriced"])

    # deviations first: read constraints before costs
    out.append("<h2>Deviations from the reference</h2>")
    out.append("<table><tr><th>Reference</th><th>Wood build</th>"
               "<th>Consequence</th><th>Diagram change</th></tr>")
    for s in spec.substitutions():
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (e(s.get("ref", "")), e(s.get("build", "")),
                      e(s.get("consequence", "")),
                      "yes" if s.get("changes_diagram") else "no"))
    out.append("</table>")

    out.append("<h2>Framing schedule</h2>")
    out.append("<table><tr><th>Assembly</th><th>Part</th><th class=num>Qty</th>"
               "<th>Finished size</th><th>Stock</th><th>Note</th></tr>")
    for r in rows:
        out.append("<tr><td>%s</td><td>%s</td><td class=num>%d</td><td>%s</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (e(r["assembly"]), e(r["part"]), r["qty"], e(r["size"]),
                      e(r["stock"]), e(r["note"])))
    out.append("</table>")

    out.append("<h2>Sheet yields</h2>")
    out.append("<table><tr><th>Stock</th><th class=num>Sheets</th>"
               "<th class=num>Yield</th><th>Offcuts kept</th></tr>")
    for plan in sheet_plans:
        off = ", ".join("%.0f x %.0f" % o for o in plan.offcuts()) or "-"
        out.append("<tr><td>%s</td><td class=num>%d</td>"
                   "<td class=num>%.1f%% <span class=bar><i style='width:%.0f%%'></i>"
                   "</span></td><td>%s</td></tr>"
                   % (e(stock.label(plan.stock)), plan.count, plan.yield_pct(),
                      min(100.0, plan.yield_pct()), e(off)))
    out.append("</table>")

    out.append("<h2>Cutlist</h2>")
    out.append("<table><tr><th>Part</th><th class=num>Qty</th><th>Size</th>"
               "<th>Stock</th><th>Grain</th><th>Cut from</th></tr>")
    for r in rows:
        out.append("<tr><td>%s</td><td class=num>%d</td><td>%s</td><td>%s</td>"
                   "<td>%s</td><td>%s</td></tr>"
                   % (e(r["part"]), r["qty"], e(r["size"]), e(r["stock"]),
                      e(r["grain"]), e(r["source"])))
    out.append("</table>")

    out.append("<h2>Bill of materials</h2>")
    current = None
    for line in lines:
        if line.category != current:
            if current is not None:
                out.append("</table>")
            current = line.category
            out.append("<h3>%s</h3>" % e(current))
            out.append("<table><tr><th>Description</th><th>SKU</th>"
                       "<th class=num>Qty</th><th class=num>Unit</th>"
                       "<th class=num>Line</th><th>Source</th></tr>")
        cls_attr = "" if line.unit_price is not None else " class=unpriced"
        out.append("<tr%s><td>%s</td><td>%s</td><td class=num>%g %s</td>"
                   "<td class=num>%s</td><td class=num>%s</td><td>%s</td></tr>"
                   % (cls_attr, e(line.description), e(line.sku or "-"), line.qty,
                      e(line.uom), _num(line.unit_price), _num(line.line_total()),
                      e(line.source or "-")))
    if current is not None:
        out.append("</table>")

    bad = unpriced(lines)
    if bad:
        out.append("<h2>Unpriced lines</h2><table><tr><th>Item</th><th>Why</th></tr>")
        for line in bad:
            out.append("<tr class=unpriced><td>%s</td><td>%s</td></tr>"
                       % (e(line.description), e(line.note or "no price in cache")))
        out.append("</table>")

    sub = spec.substitutions()
    out.append("<h2>Methodology</h2><p class=sub>Dimensions in mm; stock is imperial. "
               "Kerf %.1f mm. Parts are placed by shelf packing; grain-locked parts "
               "are never rotated. Prices come from the committed cache; a fetch "
               "refreshes only missing or stale classes. %d substitutions recorded, "
               "%d of them change the diagram.</p>"
               % (stock.KERF, len(sub), sum(1 for s in sub if s.get("changes_diagram"))))
    return "\n".join(out)


def write_report(spec, parts, sheet_plans, board_plans, lines, cache, out_dir,
                 today=None):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    paths = {"html": os.path.join(out_dir, "budget.html"),
             "cutlist": os.path.join(out_dir, "cutlist.csv"),
             "cart": os.path.join(out_dir, "cart.csv"),
             "sku_qty": os.path.join(out_dir, "sku-qty.txt")}

    with open(paths["html"], "w") as fh:
        fh.write(render_html(spec, parts, sheet_plans, board_plans, lines, cache, today))

    rows = cutlist_rows(parts, sheet_plans, board_plans)
    with open(paths["cutlist"], "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["assembly", "part", "qty", "size", "stock",
                                          "grain", "source", "note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    with open(paths["cart"], "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sku", "qty", "uom", "category", "description", "unit_price",
                    "line_total", "source", "note"])
        for line in sorted(lines, key=lambda l: (l.category, l.stock)):
            w.writerow([line.sku or "", line.qty, line.uom, line.category,
                        line.description, line.unit_price, line.line_total(),
                        line.source or "", line.note])

    with open(paths["sku_qty"], "w") as fh:
        for line in sorted(lines, key=lambda l: (l.category, l.stock)):
            if line.sku:
                fh.write("%s %g\n" % (line.sku, line.qty))
    return paths
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_report -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/report.py skills/building-from-reference/scripts/tests/test_report.py
git commit -m "woodbuild: workbook HTML and cutlist/cart/sku exports"
```

---

### Task 9: CLI end to end

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild.py`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv=None) -> int`; console behaviour `python3 woodbuild.py --spec S --prices P --out DIR [--fetch] [--compare OLD] [--tax-province ON]`, printing a summary and returning 0 on success, 2 on `SpecError`, 3 on unplaced parts.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import json
import os
import shutil
import tempfile
import unittest

from woodbuild_spec_fixture import SPEC   # helper module created in the same step
from woodbuild import cli_main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.spec_path = os.path.join(self.dir, "spec.json")
        with open(self.spec_path, "w") as fh:
            json.dump(SPEC, fh)
        self.prices = os.path.join(self.dir, "prices.json")
        with open(self.prices, "w") as fh:
            json.dump({"store": "7011", "province": "ON", "fetched": "2026-09-12",
                       "items": {"2x4": {"price": 4.25, "sku": "222",
                                         "source": "hd_search"}}}, fh)
        self.out = os.path.join(self.dir, "out")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_run_produces_workbook_and_reports_numbers(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.out, "budget.html")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "cart.csv")))

    def test_invalid_spec_returns_two(self):
        bad = json.loads(json.dumps(SPEC))
        bad["roof"]["build_up"] = 171.0
        with open(self.spec_path, "w") as fh:
            json.dump(bad, fh)
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out])
        self.assertEqual(rc, 2)

    def test_missing_prices_file_is_offline_but_not_fatal(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices + ".nope",
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertIn("unpriced", open(os.path.join(self.out, "budget.html")).read())

    def test_compare_prints_delta(self):
        old = os.path.join(self.dir, "old.json")
        with open(old, "w") as fh:
            json.dump({"items": {"2x4": {"price": 3.99}}}, fh)
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--compare", old, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.out, "price-deltas.txt")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_cli -v`
Expected: FAIL — no module named `woodbuild_spec_fixture` / no CLI.

- [ ] **Step 3: Write minimal implementation**

Create the shared fixture used by the test (identical envelope to the shed, tiny search map):

```python
# tests/woodbuild_spec_fixture.py
SPEC = {
    "build": "cli-test",
    "envelope": {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                 "roof_fall": 200.0, "tall_side": "front"},
    "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2, "corner_width": 89.0,
             "layers_out_to_in": ["smartside_grooved", "osb_7_16", "2x4"]},
    "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span",
             "deck": "osb_7_16", "covering": "corrugated_steel", "build_up": 120.0,
             "overhang": {"front": 60.0, "back": 40.0, "side": 45.0}},
    "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
              "skids": "pt_4x4", "build_up": 196.0, "below_datum": True},
    "openings": [
        {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
         "sill": 0.0, "header": "2x8"},
        {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
         "sill": 1838.04, "header": None, "mullions": 4,
         "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},,
        {"wall": "left", "kind": "transom", "width": 595.0, "height": 220.0, "sill": 1508.0},
        {"wall": "right", "kind": "transom", "width": 595.0, "height": 220.0, "sill": 1508.0},
    ],
    "substitutions": [
        {"ref": "40mm resin panel", "build": "111mm framed wall",
         "consequence": "interior 2566.9 x 1957.3 mm", "changes_diagram": False},
        {"ref": "triangular louvre", "build": "12x18 in rectangular louvre",
         "consequence": "triangular filler needed", "changes_diagram": True},
    ],
    "pricing": {"store": "7011", "province": "ON",
                "search": {"2x4": "2x4x8 SPF stud", "osb_7_16": "7/16 OSB sheathing"}},
    "options": {"kerf": 3.0, "retain_offcut_min": 300.0},
}
```

```python
# woodbuild.py
#!/usr/bin/env python3
"""woodbuild CLI: build spec in, workbook + CSVs out."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from woodbuild import bom, frame, optimise, pricing, report  # noqa: E402
from woodbuild.optimise import NestError  # noqa: E402
from woodbuild.spec import BuildSpec, SpecError  # noqa: E402

HD_SERVER = os.path.expanduser("~/.pi/agent/mcp-servers/mcp_homedepot/dist/index.js")


def cli_main(argv=None):
    ap = argparse.ArgumentParser(prog="woodbuild")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fetch", action="store_true",
                    help="refresh missing/stale prices over MCP stdio")
    ap.add_argument("--compare", help="old prices.json to diff against")
    ap.add_argument("--today", default=None)
    ap.add_argument("--server", default=HD_SERVER)
    args = ap.parse_args(argv)

    try:
        spec = BuildSpec.load(args.spec)
        spec.validate()
    except SpecError as exc:
        print("spec error: %s" % exc, file=sys.stderr)
        return 2

    cache = pricing.PriceCache(args.prices)
    cache.load()
    transport = None
    if args.fetch and os.path.exists(args.server):
        transport = pricing.StdioMCP("node", [args.server],
                                     env=dict(os.environ, HD_DEFAULT_STORE=str(cache.store or "7011")))
    try:
        prices = pricing.resolve(spec, cache, transport=transport, refresh=args.fetch,
                                 today=args.today)
    finally:
        if transport:
            transport.close()
    cache.save()

    parts = frame.derive(spec)
    try:
        sheet_plans, unplaced_sheets = optimise.pack_sheets(parts)
        board_plans, unplaced_boards = optimise.cut_boards(parts, prices=prices)
    except NestError as exc:
        print("nesting error: %s" % exc, file=sys.stderr)
        return 3
    unplaced = unplaced_sheets + unplaced_boards
    if unplaced:
        for p in unplaced:
            print("unplaced: %s (%s)" % (p.id, p.stock), file=sys.stderr)
        return 3

    lines = bom.build_bom(parts, sheet_plans, board_plans, prices=prices, spec=spec.data)
    paths = report.write_report(spec, parts, sheet_plans, board_plans, lines, cache,
                                args.out, today=args.today)

    t = bom.totals(lines, pricing.tax_rate_for(cache.province or "ON"))
    print("%s: %d parts, %d sheet plan(s), %d board plan(s)" %
          (spec.data.get("build"), len(parts), len(sheet_plans), len(board_plans)))
    print("subtotal $%.2f + tax $%.2f = $%.2f (%d lines, %d unpriced, tax rate %.3f)" %
          (t["subtotal"], t["tax"], t["total"], t["lines"], t["unpriced"],
           pricing.tax_rate_for(cache.province or "ON")))
    for key in ("html", "cutlist", "cart", "sku_qty"):
        print("  %s" % paths[key])

    if args.compare and os.path.exists(args.compare):
        import json
        with open(args.compare) as fh:
            old = json.load(fh)
        deltas = pricing.compare(old, cache.data)
        out = os.path.join(args.out, "price-deltas.txt")
        with open(out, "w") as fh:
            for cls, a, b, d in deltas:
                fh.write("%s %s -> %s (%+.2f)\n" % (cls, a, b, d))
        print("  %s (%d changes)" % (out, len(deltas)))
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
```

Add to `woodbuild/__init__.py` the re-export the test imports:

```python
from .cli import cli_main  # noqa: E402,F401
```

…and create `woodbuild/cli.py` holding the `cli_main` body above, with `woodbuild.py` reduced to:

```python
#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from woodbuild.cli import cli_main

if __name__ == "__main__":
    sys.exit(cli_main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && PYTHONPATH=. python3 -m unittest tests.test_cli -v`
Expected: PASS (4 tests). `test_invalid_spec_returns_two` proves the 171 mm roof build-up is rejected end to end.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild.py skills/building-from-reference/scripts/woodbuild skills/building-from-reference/scripts/tests
git commit -m "woodbuild: CLI wiring spec -> nest -> bom -> workbook"
```

---

### Task 10: Shed spec and FreeCAD extraction

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/scripts/woodbuild/spec_from_freecad.py`
- Create: `~/freecad/keter_pent97_build/keter_pent97.spec.json`
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_spec_from_freecad.py`

**Interfaces:**
- Consumes: `BuildSpec`, FreeCAD (`Part`, `FreeCAD`).
- Produces: `envelope_from_shape_bounds(xmin, xmax, ymin, ymax, zmax_wall, model_roof_t, roof_fall) -> dict`; `band_opening(model_band, envelope_width, corner_width, height_tall, roof_build_up, door_head) -> dict`; `openings_from_doc(doc, envelope) -> list[dict]`; `spec_from_doc(doc, wall_zmax=None) -> dict`; `check_envelope(spec, doc) -> None` raising `SpecError` on mismatch; `main(doc_path=None, out_path=None)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec_from_freecad.py
import unittest

from woodbuild.spec_from_freecad import (band_opening, envelope_from_shape_bounds,
                                         spec_skeleton)


class TestExtraction(unittest.TestCase):
    """Pure-python halves of the extractor, testable without FreeCAD installed."""

    def test_envelope_uses_the_model_roof_top_not_the_wood_build_up(self):
        # the model's wall top is its roof underside; add the MODEL's own roof
        # thickness (80 mm) to recover the product's 2258.06 mm overall height.
        # The wood roof build-up (120 mm) is a spec decision, not an envelope input.
        env = envelope_from_shape_bounds(xmin=0.0, xmax=2788.92, ymin=0.0,
                                         ymax=2179.32, zmax_wall=2178.06,
                                         model_roof_t=80.0, roof_fall=200.0)
        self.assertAlmostEqual(env["width"], 2788.92)
        self.assertAlmostEqual(env["depth"], 2179.32)
        self.assertAlmostEqual(env["height_tall"], 2258.06)
        self.assertEqual(env["roof_fall"], 200.0)

    def test_band_sill_is_recomputed_for_the_wood_roof(self):
        # wood roof build-up 120 mm vs the model's 80 mm lowers the band by 40 mm,
        # keeping the 300 mm band under an unchanged envelope and above the door head
        band = band_opening(model_band=(2698.92, 300.0, 1878.06),
                            envelope_width=2788.92, corner_width=89.0,
                            height_tall=2258.06, roof_build_up=120.0,
                            door_head=1811.02)
        self.assertAlmostEqual(band["width"], 2610.92)
        self.assertAlmostEqual(band["sill"], 1838.06)
        self.assertAlmostEqual(band["height"], 300.0)
        self.assertGreaterEqual(band["sill"], 1811.02)

    def test_spec_skeleton_has_expected_locked_decisions(self):
        env = {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
               "roof_fall": 200.0, "tall_side": "front"}
        spec = spec_skeleton(env)
        self.assertEqual(spec["wall"]["stud"], "2x4")
        self.assertEqual(spec["wall"]["corner_width"], 89.0)
        self.assertEqual(spec["wall"]["layers_out_to_in"],
                         ["smartside_grooved", "osb_7_16", "2x4"])
        self.assertEqual(spec["roof"]["build_up"], 120.0)
        self.assertTrue(spec["floor"]["below_datum"])
        self.assertEqual(spec["pricing"]["store"], "7011")
        # the door opening and band come from the model, so they are placeholders here
        self.assertEqual(spec["openings"], [])

    def test_skeleton_validates_with_openings_filled_in(self):
        env = {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
               "roof_fall": 200.0, "tall_side": "front"}
        spec = spec_skeleton(env)
        spec["openings"] = [
            {"wall": "front", "kind": "door", "width": 1386.84, "height": 1811.02,
             "sill": 0.0, "header": "2x8"},
            {"wall": "front", "kind": "band", "width": 2610.92, "height": 300.0,
             "sill": 1838.06, "header": None, "mullions": 4,
             "panes": [3.5, 1.5, 4.5, 4.5, 1.5]},
        ]
        from woodbuild.spec import BuildSpec
        BuildSpec(spec).validate()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_spec_from_freecad -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'woodbuild.spec_from_freecad'`

- [ ] **Step 3: Write minimal implementation**

```python
# woodbuild/spec_from_freecad.py
"""FreeCAD document -> build spec.  The ONLY module that imports FreeCAD.

The model supplies the envelope, the door opening and the band; the framing,
build-up and roof structure are locked decisions from the design document.
"""

import json
import os
import sys

from .spec import BuildSpec, SpecError

# locked build decisions (design doc, "Reference -> wood translation")
WALL_LAYERS = ["smartside_grooved", "osb_7_16", "2x4"]
MODEL_ROOF_T = 80.0                        # the resin roof's own thickness in KeterPent97.FCStd
ROOF_BUILD_UP = 89.0 + 11.0 + 20.0        # 2x4 rafter + OSB deck + steel
FLOOR_BUILD_UP = 89.0 + 89.0 + 18.0       # skid + joist + deck
STORE = "7011"
PROVINCE = "ON"


def envelope_from_shape_bounds(xmin, xmax, ymin, ymax, zmax_wall,
                               model_roof_t, roof_fall):
    """Build the envelope from the model's wall bounds.

    In the model the wall top IS the roof underside, so the product's overall
    height is that z plus the MODEL's own roof thickness (80 mm). The wood roof
    build-up (120 mm) is a spec decision and must not enter the envelope.
    """
    return {"width": round(xmax - xmin, 2), "depth": round(ymax - ymin, 2),
            "height_tall": round(zmax_wall + model_roof_t, 2),
            "roof_fall": float(roof_fall), "tall_side": "front"}


def band_opening(model_band, envelope_width, corner_width, height_tall,
                 roof_build_up, door_head):
    """Re-place the clerestory band for the wood roof build-up and corners.

    The model's band spans between 45 mm moulded posts and sits under an 80 mm
    resin roof. Wood corners are 89 mm and the wood roof build-up is 120 mm, so
    the band both narrows (2698.92 -> 2610.92) and drops 40 mm. Dropping it keeps
    the 300 mm band under an unchanged envelope while staying above the door head.
    """
    band_w, band_h, _model_sill = model_band
    wall_top = height_tall - roof_build_up
    sill = round(wall_top - band_h, 2)
    if sill < door_head:
        raise SpecError("band does not fit: sill %.2f mm is below the door head %.2f mm"
                        % (sill, door_head))
    return {"wall": "front", "kind": "band",
            "width": round(envelope_width - 2 * corner_width, 2),
            "height": float(band_h), "sill": sill, "header": None,
            "mullions": 4, "panes": [3.5, 1.5, 4.5, 4.5, 1.5]}


def spec_skeleton(envelope):
    return {
        "build": "keter-pent-97-wood",
        "source": {"kind": "product", "sku": "1001865367", "model": "260435",
                   "cad": "~/freecad/KeterPent97.FCStd",
                   "url": "https://www.homedepot.ca/product/1001865367"},
        "envelope": envelope,
        "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2,
                 "sole_plate": "pt_2x4", "bearing_plate": True, "corner_width": 89.0,
                 "layers_out_to_in": WALL_LAYERS},
        "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span",
                 "deck": "osb_7_16", "covering": "corrugated_steel",
                 "build_up": ROOF_BUILD_UP,
                 "overhang": {"front": 60.0, "back": 40.0, "side": 45.0}},
        "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
                  "skids": "pt_4x4", "build_up": FLOOR_BUILD_UP, "below_datum": True},
        "openings": [],
        "substitutions": [
            {"ref": "40 mm resin double-wall panel", "build": "111 mm framed wall",
             "consequence": "interior clear 2566.9 x 1957.3 mm, volume ~10.2 m3",
             "changes_diagram": False},
            {"ref": "clerestory band 2698.92 mm between 45 mm moulded posts",
             "build": "band 2610.92 mm between 89 mm corners, dropped 40 mm",
             "consequence": "sill strip above the doors shrinks 67 mm to 27 mm",
             "changes_diagram": True},
            {"ref": "45 x 45 mm moulded corner post", "build": "3-stud 2x4 corner, 89 x 140",
             "consequence": "corner trim detail required", "changes_diagram": True},
            {"ref": "triangular louvre vent 620 x 300", "build": "12 x 18 in rectangular louvre",
             "consequence": "triangular filler panel needed, rough opening changed",
             "changes_diagram": True},
            {"ref": "resin floor + 60 mm plinth", "build": "PT joists + T&G deck",
             "consequence": "196 mm of structure below the datum; base must be excavated/levelled",
             "changes_diagram": True},
            {"ref": "resin/steel sandwich roof (80 mm)", "build": "2x4 rafters + purlin + OSB + steel (120 mm)",
             "consequence": "keeps the 300 mm clerestory band under the fixed envelope",
             "changes_diagram": True},
            {"ref": "moulded resin door leaves", "build": "framed 18 mm plywood leaves",
             "consequence": "hinges and hasp must suit outward-swinging doors",
             "changes_diagram": True},
            {"ref": "level ground only", "build": "compacted gravel/pavers + skids",
             "consequence": "new requirement the reference does not have",
             "changes_diagram": False},
            {"ref": "145 mm plank grooves", "build": "manufacturer's grooved siding",
             "consequence": "groove pitch differs (cosmetic)", "changes_diagram": False},
        ],
        "pricing": {"store": STORE, "province": PROVINCE, "search": {
            "2x4": "2x4x8 SPF stud", "2x6": "2x6x8 SPF", "2x8": "2x8x8 SPF",
            "pt_2x4": "2x4x8 pressure treated", "pt_4x4": "4x4x8 pressure treated",
            "osb_7_16": "7/16 OSB sheathing", "plywood_tg_18": "3/4 tongue and groove plywood",
            "plywood_ext_18": "3/4 exterior plywood", "smartside_grooved": "LP SmartSide panel siding grooved",
            "polycarbonate_6": "6mm polycarbonate sheet", "louvre_12x18": "12x18 aluminium gable vent",
            "steel_roof": "corrugated steel roofing panel"}},
        "options": {"kerf": 3.0, "retain_offcut_min": 300.0},
    }


def openings_from_doc(doc, envelope):
    """Read the door and band from the model's own cutter objects.

    The door opening and the transoms keep the model's sizes; the band is
    re-placed for the wood roof build-up and corner width by band_opening().
    """
    door = doc.getObject("fw_door")
    band = doc.getObject("fw_band")
    if door is None or band is None:
        raise SpecError("model is missing fw_door / fw_band cutters")
    dbb = door.Shape.BoundBox
    bbb = band.Shape.BoundBox
    door_w = round(dbb.XLength, 2)
    door_h = round(dbb.ZLength, 2)
    door_head = round(dbb.ZMax, 2)
    band_block = band_opening(model_band=(round(bbb.XLength, 2), round(bbb.ZLength, 2),
                                          round(bbb.ZMin, 2)),
                              envelope_width=envelope["width"],
                              corner_width=89.0,
                              height_tall=envelope["height_tall"],
                              roof_build_up=ROOF_BUILD_UP,
                              door_head=door_head)
    transom_sill = round(door_head - 300.0, 2)
    louvre_sill = round(door_head - 480.0, 2)
    return [
        {"wall": "front", "kind": "door", "width": door_w, "height": door_h,
         "sill": 0.0, "header": "2x8"},
        band_block,
        {"wall": "left", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": transom_sill, "header": None},
        {"wall": "right", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": transom_sill, "header": None},
        {"wall": "left", "kind": "louvre", "width": 457.0, "height": 305.0,
         "sill": louvre_sill, "header": None, "near": "back_top"},
        {"wall": "right", "kind": "louvre", "width": 457.0, "height": 305.0,
         "sill": louvre_sill, "header": None, "near": "back_top"},
    ]


def spec_from_doc(doc, wall_zmax=None):
    import FreeCAD  # noqa: F401
    walls = doc.getObject("WallsOpen")
    if walls is None:
        raise SpecError("model has no WallsOpen object")
    bb = walls.Shape.BoundBox
    env = envelope_from_shape_bounds(bb.XMin, bb.XMax, bb.YMin, bb.YMax,
                                     wall_zmax if wall_zmax is not None else bb.ZMax,
                                     MODEL_ROOF_T, 200.0)
    spec = spec_skeleton(env)
    spec["openings"] = openings_from_doc(doc, env)
    return spec


def check_envelope(spec, doc):
    """Fail loudly if the model no longer matches the spec."""
    walls = doc.getObject("WallsOpen")
    bb = walls.Shape.BoundBox
    env = spec["envelope"]
    if abs(bb.XLength - env["width"]) > 1.0 or abs(bb.YLength - env["depth"]) > 1.0:
        raise SpecError("envelope mismatch: model is %.1f x %.1f mm, spec says %.1f x %.1f mm"
                        % (bb.XLength, bb.YLength, env["width"], env["depth"]))


def main(doc_path=None, out_path=None):
    import FreeCAD
    doc_path = doc_path or os.path.expanduser("~/freecad/KeterPent97.FCStd")
    out_path = out_path or os.path.expanduser(
        "~/freecad/keter_pent97_build/keter_pent97.spec.json")
    doc = FreeCAD.openDocument(doc_path)
    spec = spec_from_doc(doc)
    BuildSpec(spec).validate()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(spec, fh, indent=2)
    print("wrote %s" % out_path)
    return out_path


if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_spec_from_freecad -v`
Expected: PASS (4 tests, no FreeCAD needed).

Then generate the real spec and check it:

```bash
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
  ~/.pi/agent/skills/building-from-reference/scripts/woodbuild/spec_from_freecad.py
python3 -c "import json;s=json.load(open('$HOME/freecad/keter_pent97_build/keter_pent97.spec.json'));print(s['envelope']);print([ (o['wall'],o['kind'],o['width'],o['height']) for o in s['openings']])"
```

Expected: envelope `width 2788.92, depth 2179.32, height_tall 2258.06`, door `1386.84 x 1811.02`, band `2610.92 x 300.0` at sill `1838.06` (narrowed from the model's 2698.92 mm and dropped 40 mm for the wood roof build-up), and the deviation row `clerestory band 2698.92 mm between 45 mm moulded posts` must be present. If the door or band numbers differ, the model changed — do not edit the numbers by hand, re-derive.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/woodbuild/spec_from_freecad.py skills/building-from-reference/scripts/tests/test_spec_from_freecad.py
git commit -m "woodbuild: derive the build spec from the FreeCAD model"
```

---

### Task 11: First real build and numeric verification

**Files:**
- Create: `~/freecad/keter_pent97_build/prices.json` (seeded by `--fetch`)
- Create: `~/freecad/keter_pent97_build/out/*` (workbook + exports)
- Test: `~/.pi/agent/skills/building-from-reference/scripts/tests/test_real_build.py`

**Interfaces:**
- Consumes: the CLI, the shed spec, the Home Depot MCP server.
- Produces: a committed price cache, a workbook, and an assertion suite that fails if the real build stops matching the model or the geometry stops fitting.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_real_build.py
"""End-to-end checks on the real shed build. Skips if the build data is absent."""
import json
import os
import unittest

from woodbuild import bom, frame, optimise, stock
from woodbuild.spec import BuildSpec

BUILD_DIR = os.path.expanduser("~/freecad/keter_pent97_build")
SPEC_PATH = os.path.join(BUILD_DIR, "keter_pent97.spec.json")
PRICES = os.path.join(BUILD_DIR, "prices.json")


@unittest.skipUnless(os.path.exists(SPEC_PATH), "shed spec not generated yet")
class TestRealBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = BuildSpec.load(SPEC_PATH)
        cls.spec.validate()
        cls.parts = frame.derive(cls.spec)
        cls.sheets, cls.unplaced_s = optimise.pack_sheets(cls.parts)
        prices = {}
        if os.path.exists(PRICES):
            prices = json.load(open(PRICES)).get("items", {})
        cls.boards, cls.unplaced_b = optimise.cut_boards(cls.parts, prices=prices)
        cls.lines = bom.build_bom(cls.parts, cls.sheets, cls.boards, prices=prices,
                                 spec=cls.spec.data)

    def test_envelope_matches_the_product_sheet(self):
        env = self.spec.envelope
        self.assertAlmostEqual(env["width"], 2788.92, places=1)
        self.assertAlmostEqual(env["depth"], 2179.32, places=1)
        self.assertAlmostEqual(env["height_tall"], 2258.06, places=1)

    def test_door_opening_is_preserved_exactly(self):
        self.assertAlmostEqual(self.spec.door_head(), 1811.02, places=1)
        door = [o for o in self.spec.openings("front") if o["kind"] == "door"][0]
        self.assertAlmostEqual(door["width"], 1386.84, places=1)

    def test_every_part_placed(self):
        self.assertEqual(self.unplaced_s, [])
        self.assertEqual(self.unplaced_b, [])

    def test_no_sheet_overfills(self):
        for plan in self.sheets:
            w, h = stock.sheet_size(plan.stock)
            for sheet in plan.sheets:
                for p in sheet:
                    self.assertLessEqual(p.x + p.w, w + 1e-6)
                    self.assertLessEqual(p.y + p.h, h + 1e-6)

    def test_sheet_quantity_is_plausible_for_a_9x7_shed(self):
        total = sum(p.count for p in self.sheets)
        self.assertGreaterEqual(total, 10)
        self.assertLessEqual(total, 40)

    def test_framing_counts_are_sane(self):
        studs = [p for p in self.parts if p.id == "stud_front"][0]
        # a 2.79 m wall at 406.4 mm o.c. gives 7 studs + an end stud
        self.assertGreaterEqual(studs.qty, 8)
        self.assertLessEqual(studs.qty, 10)

    def test_bom_has_every_category(self):
        cats = {l.category for l in self.lines}
        for required in ("lumber", "sheets", "glazing", "fasteners", "hardware",
                         "vents", "roof", "base", "finish"):
            self.assertIn(required, cats)

    def test_deviations_cover_the_known_gaps(self):
        refs = " ".join(s["ref"] for s in self.spec.substitutions())
        for needle in ("resin", "louvre", "corner post", "floor"):
            self.assertIn(needle, refs)

    def test_unpriced_lines_are_reported_not_guessed(self):
        bad = bom.unpriced(self.lines)
        for line in bad:
            self.assertIsNone(line.unit_price)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails for the right reason**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_real_build -v`
Expected: FAIL once the spec exists (missing `prices.json` is fine) — most likely on `test_bom_has_every_category` or a nesting failure, because no real run has happened yet.

- [ ] **Step 3: Run the real build**

```bash
cd ~/.pi/agent/skills/building-from-reference/scripts
mkdir -p ~/freecad/keter_pent97_build
python3 woodbuild.py \
  --spec ~/freecad/keter_pent97_build/keter_pent97.spec.json \
  --prices ~/freecad/keter_pent97_build/prices.json \
  --out ~/freecad/keter_pent97_build/out \
  --fetch --today $(date +%F)
```

Expected: a printed subtotal/tax/total, four files written, and `prices.json` populated for the stock classes. Store a copy of the pre-fetch cache as `prices.baseline.json` so later `--compare` runs have something to diff against.

- [ ] **Step 4: Run the tests again**

Run: `cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest tests.test_real_build -v`
Expected: PASS. Any unplaced part or plausible-range failure means the spec (not the test) needs fixing — re-derive it from the model in Task 10 rather than hand-editing sizes.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference/scripts/tests/test_real_build.py
git commit -m "woodbuild: end-to-end assertions for the real shed build"
```

---

### Task 12: Skill `building-from-reference` (baseline → skill → verify)

**Files:**
- Create: `~/.pi/agent/skills/building-from-reference/SKILL.md`
- Create: `~/.pi/agent/skills/building-from-reference/framing-rules.md`
- Create: `~/.pi/agent/skills/building-from-reference/stock-catalogue.md`
- Create: `~/.pi/agent/skills/building-from-reference/substitutions.md`

**Interfaces:**
- Consumes: the CLI and its spec format.
- Produces: a discoverable skill; `framing-rules.md` documents every rule `frame.py` implements.

- [ ] **Step 1: Run the baseline (RED) — dispatch a fresh subagent**

Dispatch a subagent with this exact task and **no skill available**:

> You have a Home Depot Canada MCP server (`hd_search`, `hd_product`) and this spec at `~/freecad/keter_pent97_build/keter_pent97.spec.json`. Produce a cutlist and a priced shopping cart for building this shed out of wood. Write your answer to `/tmp/baseline-cutlist.md`.

Record verbatim: does it invent quantities from area maths, invent prices, skip framing, skip deviations, or claim HD stocks a moulded resin panel? Keep the transcript — it is the failing test this skill must fix.

- [ ] **Step 2: Write the skill**

```markdown
---
name: building-from-reference
description: Use when asked to rebuild an existing structure or product in wood, to produce a cutlist, bill of materials or priced shopping list for a build, or to turn a photo, drawing, product page or CAD model into buildable lumber and sheet-goods parts.
---

# Building from a reference

A reference is not a build. A moulded panel shed, a photo of a bench, or a
drawing of a cabinet contains no studs, plates, headers or fasteners — those
must be derived. Never translate a reference's parts straight into wood, and
never price from memory.

## Workflow

1. **Intake** — get the numbers, not the impression: envelope dimensions,
   opening sizes and positions, roof pitch, and what each part is made of.
   Prefer a product data sheet or an existing CAD model over a photo. If the
   only source is an image, state which dimensions you are guessing.
2. **Translate** — for every reference material write the wood equivalent and
   its dimensional consequence (see `substitutions.md`). Anything Home Depot
   does not stock becomes a substitution row; the diagram changes, that is
   expected and must be recorded, not hidden.
3. **Decide the invariants** — say out loud which dimensions are fixed (usually
   the exterior envelope and the clear door opening) and which give: wall
   thickness, floor structure, roof build-up.
4. **Write the spec** — one JSON file, envelope + wall build-up + openings +
   roof + floor + substitutions + price search terms. Use
   `scripts/woodbuild/spec_from_freecad.py` when a CAD model exists.
5. **Run the engine** — `python3 scripts/woodbuild.py --spec S --prices P --out DIR`
   (add `--fetch` only when the cache is stale). It derives framing, nests
   sheets, cuts boards, builds the BOM and writes the workbook.
6. **Verify before reporting** — every part placed, no sheet overfilled, sheet
   count plausible, door opening still the reference's size. `spec.py` refuses
   to run when the band no longer fits under the roof build-up.
7. **Report** — read the deviations table *before* the totals, and pass on any
   `unpriced` lines with their reason.

## Hard rules

- **No invented prices.** A price comes from the cache, fetched from the Home
  Depot server, or it is `unpriced`. Never estimate, never zero.
- **No invented quantities.** Quantities come from nesting and cutting-stock,
  not from area ÷ sheet size.
- **Framing is derived, never copied.** See `framing-rules.md`.
- **Fixed dimensions stay fixed** unless the person you are building for agrees
  to change them; a fixed exterior plus thicker walls means a smaller interior,
  and that must be stated in cubic metres.

## Scripts

- `scripts/woodbuild.py` — spec → workbook + `cutlist.csv` + `cart.csv` + `sku-qty.txt`
- `scripts/woodbuild/spec_from_freecad.py` — FreeCAD document → spec
- `scripts/woodbuild/audit.py` — not here; see the `freecad-model-hygiene` skill
```

- [ ] **Step 3: Write the heavy reference files**

`framing-rules.md` must state, with the values `frame.py` uses: stud spacing 406.4 mm o.c. and how the end studs close a run; sole plate PT plus one top plate and one bearing plate; 3-stud corner assemblies replacing moulded posts (**89 mm along the wall, which is why the clerestory band narrows from 2698.92 mm to 2610.92 mm**); king/jack studs both sides of every opening; header depth ≥ span ÷ 20 rounded up to stock depth, doubled; cripples above heads; rafters 2×4 @ 304.8 mm o.c. with a mid-span purlin when the roof build-up is capped at 120 mm; blocking at panel joints and hardware; and the three datum rules (floor structure below the datum; band top = wall top; band sill ≥ door head).

`stock-catalogue.md` must list every class in `stock.py` with its size, thickness, unit, grain flag and BOM category, plus kerf 3.0 mm and `retain_offcut_min` 300 mm, and how to add a class (add to `SHEETS`/`BOARDS` *and* `CATEGORIES`).

`substitutions.md` must carry the eight known translations from the shed build: resin panel → 111 mm framed wall; moulded corner post → 3-stud corner; triangular louvre → 12×18 in rectangular louvre plus filler; resin floor → PT joists + T&G deck below the datum; resin/steel roof → 2×4 rafters + purlin + OSB + steel; moulded door leaves → framed 18 mm plywood leaves; level ground → gravel/pavers pad; 145 mm grooves → manufacturer's siding pitch. Each with its dimensional consequence.

- [ ] **Step 4: Verify (GREEN)**

Re-dispatch the Step 1 task **with the skill loaded** (tell the subagent to read `~/.pi/agent/skills/building-from-reference/SKILL.md` and use the scripts). Expected: it writes a spec, runs the engine, and reports deviations and unpriced lines instead of inventing either. Then run a discovery check: give a third subagent the bare task "make a cutlist for this shed in wood" (nothing else) and confirm it selects this skill by description.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/building-from-reference
git commit -m "skill: building-from-reference (cutlist, cart, deviations workflow)"
```

---

### Task 13: Skill `freecad-render-views` (baseline → skill → verify)

**Files:**
- Create: `~/.pi/agent/skills/freecad-render-views/SKILL.md`
- Create: `~/.pi/agent/skills/freecad-render-views/scripts/freecad_views.py`

**Interfaces:**
- Produces: `render_views(doc, prefix, views, out_dir, width, height) -> dict` and `SIDE_VIEWS` mapping names to FreeCAD view methods; the skill documents when each workaround is needed.

- [ ] **Step 1: Run the baseline (RED)**

Dispatch a subagent with: *Render front, left, right and exploded PNGs of `~/freecad/KeterPent97.FCStd` and `~/freecad/KeterPent97_exploded.FCStd` into `~/freecad/views_test/` using the FreeCAD MCP, then tell me what the images show.* Record the failures verbatim: expect the wrong document captured, stale frames, steep unreadable angles, or the GUI thread wedging after several captures.

- [ ] **Step 2: Write the skill**

```markdown
---
name: freecad-render-views
description: Use when rendering or screenshotting FreeCAD views, exporting per-side or exploded image sets, or when a FreeCAD render comes out blank, stale, of the wrong document, or refuses to change.
---

# Rendering FreeCAD views reliably

FreeCAD 1.1's view API is narrower than it looks. Every rule below was learned
by getting it wrong.

## The rules

- **Render through the document's own view.** `FreeCADGui.ActiveDocument` points
  at whichever document was built last, so rendering "the assembled model" while
  another document exists silently captures the wrong one. Use
  `FreeCADGui.getDocument(doc.Name).ActiveView`.
- **`viewPosition` and `viewUp` are read-only** in 1.1 — assigning them raises
  `RuntimeError: Extension object missing implement of setattr`. Only the named
  presets work: `viewFront`, `viewRear`, `viewLeft`, `viewRight`, `viewTop`,
  `viewBottom`, `viewIsometric`, `viewDimetric`, `viewTrimetric`, `viewAxonometric`.
- **Preset names do not mean what they look like.** Empirically, for a model
  whose front wall faces −Y: `viewRear` = the door side, `viewFront` = the back
  wall, `viewLeft`/`viewRight` = the side panels. Print and check one image
  before rendering a whole set.
- **`saveImage` wedges the GUI thread after about five captures in one call.**
  Batch three per tool call at most, and reopen the document
  (`closeDocument` + `openDocument`) when the camera state looks stale — a fresh
  document gives a fresh view.
- **Orthographic camera for elevations:** `av.setCameraType("Orthographic")`
  before rendering; the default perspective makes preset views look steep.
- **TechDraw page objects have no `.Shape`.** Anything that walks the document
  and reads `.Shape` (including the FreeCAD MCP screenshot path) breaks on a
  `TechDraw::DrawPage`, and every later tool call in that document fails. Keep
  drawing pages out of documents you still want to drive over MCP.
- **Exploded views separate parts along their own normals** (roof up, panels
  outward), and `Flat Lines` display mode is what makes the joins readable.
  Straight-on views show 40 mm panels edge-on — use a trimetric or plan view.
- **A sloped roof hides horizontal parts.** If a band or rail looks like it
  disappears under the roof, it is an intersection, not a rendering bug — check
  the model.

## Script

`scripts/freecad_views.py` implements all of the above; import it rather than
re-deriving the workarounds:

```python
from freecad_views import render_views, SIDE_VIEWS
render_views(doc, "KeterPent97", ["doors", "side_left", "plan"], "~/freecad/views")
```
```

- [ ] **Step 3: Write the script**

```python
# scripts/freecad_views.py
"""FreeCAD 1.1 view rendering that respects the API's real limits."""

import os
import time

SIDE_VIEWS = {
    "doors": "viewRear",         # -Y face: double doors + clerestory band
    "back": "viewFront",         # +Y face: plain back wall
    "side_left": "viewLeft",
    "side_right": "viewRight",
    "plan": "viewTop",
    "iso": "viewIsometric",
    "dimetric": "viewDimetric",
    "trimetric": "viewTrimetric",
}


def render_views(doc, prefix, views, out_dir, width=1200, height=900, settle=2):
    """One PNG per view. Uses the document's OWN view, batches are the caller's job."""
    import FreeCADGui
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    av = FreeCADGui.getDocument(doc.Name).ActiveView
    try:
        av.setCameraType("Orthographic")
    except Exception:
        pass
    saved = {}
    for name in views:
        getattr(av, SIDE_VIEWS[name])()
        av.fitAll()
        for _ in range(settle):
            FreeCADGui.updateGui()
            time.sleep(0.3)
        path = os.path.join(out_dir, "%s_%s.png" % (prefix, name))
        av.saveImage(path, width, height, "White")
        saved[name] = path
    return saved
```

- [ ] **Step 4: Verify (GREEN)**

Re-dispatch the Step 1 task with the skill and script available. Expected: per-side PNGs that actually show the assembled model on the door side, sides and plan, and exploded PNGs where the panels are separated and readable — no wrong-document captures, no wedged calls. Confirm by opening two of the produced PNGs and checking they are not identical.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/freecad-render-views
git commit -m "skill: freecad-render-views (per-document views, batch limits, exploded)"
```

---

### Task 14: Skill `freecad-model-hygiene` (baseline → skill → verify)

**Files:**
- Create: `~/.pi/agent/skills/freecad-model-hygiene/SKILL.md`
- Create: `~/.pi/agent/skills/freecad-model-hygiene/scripts/audit.py`

**Interfaces:**
- Produces: `check_disjoint(parts) -> tuple[float, float, float]` (sum, union, overlap); `pairwise_overlap(parts, threshold=1.0) -> list[tuple[str, str, float]]`; the skill states the design rule and the silent-boolean bugs.

- [ ] **Step 1: Run the baseline (RED)**

Dispatch a subagent with: *Open `~/freecad/KeterPent97.FCStd`, add a triangular louvre vent to the right side wall near the back top, and add a small plinth skirt 10 mm proud of the walls. Verify the cut actually removed material and that no parts overlap.* Record what it does: expect a cutter placed exactly tangent to the face (removes nothing), and no overlap check at all.

- [ ] **Step 2: Write the skill**

```markdown
---
name: freecad-model-hygiene
description: Use when building parametric FreeCAD models, boolean cuts, or anything with multiple touching parts - especially when faces look doubled, joins are unreadable, or a cut silently removes nothing.
---

# FreeCAD model hygiene

Overlapping solids are why you cannot see where one part ends. Two parts that
interpenetrate leave doubled edges on a shared face, and a cutter that only
touches a surface removes nothing at all — FreeCAD reports success either way.

## Design rule

**No two parts overlap.** Panels butt into posts, a skirt sits proud of the
walls, a floor sits between the posts. Check it, do not assume it:

```python
from audit import check_disjoint, pairwise_overlap
print(check_disjoint(parts))          # (sum, union, overlap) - overlap must be 0
print(pairwise_overlap(parts))        # names every offending pair
```

A sum-versus-union comparison catches overlaps; the pairwise sweep tells you
*which* pair. Use both — the pairwise sweep is what found the five real faults in
this model.

## Silent boolean bugs

| Symptom | Cause | Fix |
|---|---|---|
| A cut removes nothing; face count and volume unchanged | cutter exactly **tangent** to the surface | extend the cutter 1 mm past the face (`y = -1.0, length = depth + 1.0`) |
| Roof cuts into a rail or post | sloped underside vs a horizontal top | size the part from the roof underside at its **far** edge, or cut a wedge |
| Louvre slats poke through a wall or roof | slats sized from the opening's nominal size, not the triangle actually cut | compute each slat's length from the cut geometry at its own height |
| Louvres vanish under the roof | slats placed from the wrong reference (the high end) | place from the roof underside at the back edge and work down |
| Panel top "disappears" into the roof | horizontal panel under a sloped roof | subtract a wedge, or stop the panel at the underside on its inner face |

## Verification loop

1. Build booleans.
2. `check_disjoint()` → overlap must be exactly 0.
3. `pairwise_overlap()` → fix each named pair, re-run.
4. Only then render or export.

## Saving

- Build in the GUI when you intend to keep the file: a document created headless
  saves without view state, and reopens with everything hidden or colourless.
- Keep a `parts` dict in the build script (`{key: object}`) and derive names,
  colours and visibility from it; name-based rules silently miss renamed parts.
- `Part::MultiFuse` and `Part::Cut` results are fine as final objects, but keep
  the raw panels and cutters in the tree so a change is traceable.
```

- [ ] **Step 3: Write the script**

```python
# scripts/audit.py
"""Overlap auditing for FreeCAD assemblies."""


def check_disjoint(parts):
    """(sum_of_volumes, fused_union_volume, overlap). overlap must be 0."""
    shapes = [o for o in parts if getattr(o, "Shape", None) and not o.Shape.isNull()]
    total = sum(o.Shape.Volume for o in shapes)
    union = shapes[0].Shape.multiFuse([o.Shape for o in shapes[1:]]).Volume
    return total, union, total - union


def pairwise_overlap(parts, threshold=1.0):
    """[(name_a, name_b, overlap_mm3)] for every pair that interpenetrates."""
    shapes = [o for o in parts if getattr(o, "Shape", None) and not o.Shape.isNull()]
    out = []
    for i, a in enumerate(shapes):
        for b in shapes[i + 1:]:
            if not a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                continue
            try:
                vol = a.Shape.common(b.Shape).Volume
            except Exception:
                vol = 0.0
            if vol > threshold:
                out.append((a.Name, b.Name, vol))
    return sorted(out, key=lambda t: -t[2])
```

- [ ] **Step 4: Verify (GREEN)**

Re-dispatch the Step 1 task with the skill loaded. Expected: the louvre slot is cut with a cutter that overlaps the wall (volume drop non-zero and reported), the skirt is built as a ring outside the wall faces, and the agent runs `check_disjoint` + `pairwise_overlap` and reports zero overlap before finishing.

- [ ] **Step 5: Commit**

```bash
cd ~/.pi/agent && git add skills/freecad-model-hygiene
git commit -m "skill: freecad-model-hygiene (disjoint parts, silent boolean bugs, audit)"
```

---

### Task 15: Document the workflow and finish

**Files:**
- Modify: `~/.pi/agent/README.md` (add the three skills and the shed build layout)
- Create: `~/freecad/keter_pent97_build/README.md`

- [ ] **Step 1: Update the pi-config README**

Add to the Notes list: the three skills under `~/.pi/agent/skills/` with one line each on what they cover, and that `building-from-reference` carries the `woodbuild` engine with its own `unittest` suite (command: `python3 -m unittest discover -s ~/.pi/agent/skills/building-from-reference/scripts/tests -v`).

- [ ] **Step 2: Write the build README**

State: what the build is (wood replica of SKU 1001865367), the locked decisions, the two dimensional collisions and their resolutions, the command to re-run the budget, how the price cache works (committed, `--fetch` to refresh, `--compare prices.baseline.json` to see drift), and that the framing is conventional rules of thumb, not engineered.

- [ ] **Step 3: Run everything**

```bash
cd ~/.pi/agent/skills/building-from-reference/scripts && python3 -m unittest discover -s tests -v 2>&1 | tail -5
python3 woodbuild.py --spec ~/freecad/keter_pent97_build/keter_pent97.spec.json \
  --prices ~/freecad/keter_pent97_build/prices.json \
  --out ~/freecad/keter_pent97_build/out --today $(date +%F)
```

Expected: all tests pass; the run prints a subtotal, tax and total, exits 0.

- [ ] **Step 4: Commit**

```bash
cd ~/.pi/agent && git add README.md && git commit -m "docs: skills and the wood-build workflow"
```

---

## Self-Review

**1. Spec coverage**

| Spec requirement | Task |
|---|---|
| Stdlib-only engine, spec as the only seam | 1, 2, 9 |
| Envelope fixed; band-fits and floor-below-datum enforced | 2, 10 |
| Derived framing (plates, studs, corners, openings, rafters, purlin, blocking) | 5 |
| Grain-aware 2D sheet nesting, yields, offcuts | 3 |
| Cost-minimising 1D cutting-stock | 4 |
| BOM with categories, consumables derived from geometry | 6 |
| Cache-first pricing, `--fetch` over MCP stdio, `unpriced` never guessed, `--compare` | 7 |
| HTML workbook with deviations before costs, plus `cutlist.csv` / `cart.csv` / `sku-qty.txt` | 8 |
| CLI end to end with failure codes | 9 |
| Spec derived from the FreeCAD model, envelope cross-check | 10 |
| Real build verified numerically, HST 13 % at store 7011 | 11 |
| Skill `building-from-reference` + heavy reference files | 12 |
| Skill `freecad-render-views` + script | 13 |
| Skill `freecad-model-hygiene` + script | 14 |
| Committed to `pi-config`, documented | 15 |
| Baseline-tested skills (RED → GREEN) | 12, 13, 14 |
| Deferred: per-sheet SVG diagrams | not planned (spec non-goal) |

**2. Placeholder scan:** no `TBD`/`TODO`; every code step carries runnable code; every test step names the file, the command and the expected result.

**3. Type consistency:** `Part(id, w, h, qty, stock, grain_locked, assembly, note)` is used with those exact keyword names in Tasks 3–6 and 9–11; `SheetPlan(stock, sheets)` and `BoardPlan(stock, length_mm, count, cuts)` likewise; `BomLine(category, stock, description, qty, uom, unit_price, sku, source, note)` is constructed positionally in Task 6 and by keyword in Task 8; `resolve(spec, cache, transport, refresh, today)` matches Task 7's tests and Task 9's CLI; `render_views(doc, prefix, views, out_dir, ...)` matches Task 13's skill text. `woodbuild.cli.cli_main` is imported by `test_cli.py` and re-exported from `woodbuild/__init__.py` in Task 9.
