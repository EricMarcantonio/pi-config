# Design: splitting `building-from-reference` into single-purpose skills

Date: 2026-09-13
Status: approved (design), pending implementation plan

## Problem

One skill (`building-from-reference`) currently carries five unrelated
capabilities and three reference documents:

- the intake/translation/verify workflow for turning a reference into a wood build
- wood framing rules (`framing-rules.md`)
- sheet and board nesting rules (inside `stock-catalogue.md`)
- a store-agnostic pricing method (judge candidates, record provenance) tangled with
  one store's details (Home Depot Canada MCP tool names, store IDs, Ontario tax,
  MicroPro Sienna, "what the store does not stock")
- one project's ingestion constants (KeterPent97 object names, wall layers, roof
  build-up, store 7011, a nine-row substitution table)

The coupling is asymmetric and wrong: store knowledge sits inside generic pricing,
and one project's decisions sit inside reusable ingestion code. The skill cannot be
reused for a different structure or a different store without editing it.

## Goal

Each skill does one thing. Store knowledge is confined to one skill. The engine is a
shared library, not a capability. No build-specific data lives in the config repo.

## Non-goals

- Rewriting the engine's algorithms (framing, nesting, BOM, report keep their behaviour).
- Changing the price cache JSON schema (existing caches keep working).
- Preserving the KeterPent97 project. Its constants are deleted, not migrated; the
  build can be re-derived as spec data if it is ever wanted again.
- Adding a second store adapter. The protocol is built so one can be added; only Home
  Depot is implemented.

## Decisions

### D1 — One package, seven skill directories

Pi discovers any directory containing `SKILL.md` recursively under a package's
`skills/` dir or under `PI_CODING_AGENT_DIR`. Skills have no formal dependency
mechanism, so sharing is by relative path inside the same tree. Grouping dirs are not
needed; all seven skills are siblings.

```
pi-config/skills/
├── building-from-reference/SKILL.md
├── wood-framing/SKILL.md, framing-rules.md
├── sheet-and-board-nesting/SKILL.md
├── build-pricing/SKILL.md
├── homedepot-catalogue/SKILL.md, stock-availability.md, substitutions-hd.md,
│   scripts/homedepot_adapter.py
├── freecad-model-to-spec/SKILL.md
└── woodbuild-engine/SKILL.md, scripts/woodbuild.py, scripts/woodbuild/*.py,
    scripts/tests/
```

### D2 — The engine is a hidden skill

`woodbuild-engine` holds every Python file and the test suite. It declares
`disable-model-invocation: true`, so it never enters the system prompt; it is read on
demand when another skill's instructions point at it, or explicitly with
`/skill:woodbuild-engine`.

Rationale: a plain `lib/` at the config root is invisible to pi's packaging story and
would be lost by an npm install that only carries `skills/`. A skill directory is the
unit this system knows how to move, and its own `SKILL.md` documents the API.

The other six skills reference it as `../woodbuild-engine/scripts/...`. The engine
never references a skill.

### D3 — Store knowledge is an injected adapter

`homedepot-catalogue/scripts/homedepot_adapter.py` is the only file in the tree that
names a store. It exposes:

| member | purpose |
|---|---|
| `search_tool` | MCP tool used for candidate search |
| `product_tool` | MCP tool used to verify a chosen SKU |
| `source_search` | label written into a line and cache entry for a search hit |
| `source_product` | label written for a verified product |
| `candidate_sources` | source labels that mean "not yet verified", including legacy ones such as `hd_search` |
| `server_path` | path to the MCP server entry point, or `None` |
| `default_store` | store id used for a *search candidate* when the spec names none; never used to price a class, where an explicit store or a hard error is required |
| `tax_rate(province)` | tax rate for the spec's province |
| `env()` | extra environment for the MCP subprocess |

`woodbuild/adapters.py` defines the protocol and a loader for a Python file path.
`woodbuild/pricing.py` takes an adapter and never contains a store name, a tool name,
a store id, or a tax table. Its existing generic parts stay: `PriceCache`,
`StdioMCP`, `put_matched`, `needs_match`, `candidates`, `set_price`, `resolve`,
`compare`, `MATCH_MAX_AGE_DAYS`. `PricingTransportError` and `PriceError` stay.

`woodbuild/report.py` stops importing `tax_rate_for` and receives the rate as an
argument (from the CLI, which got it from the adapter). `woodbuild/cli.py` drops
`HD_SERVER` and `HD_DEFAULT_STORE`, and takes `--adapter <path>`. With no adapter the
CLI prices from the cache only and reports tax as 0.0 with a warning line.

`woodbuild/stock.py` keeps geometry only: `SHEETS`, `BOARDS`, `CATEGORIES`, `KERF`,
`FT`, `is_sheet`, `thickness`, `label`, and the import-time validation. Its
store-availability prose moves to `homedepot-catalogue/stock-availability.md`.

### D4 — Ingestion is generic; the project's numbers are data

`woodbuild/spec_from_freecad.py` is deleted. Its reusable, pure parts become
`woodbuild/from_model.py`:

- `wall_bounds(doc, names)` — bounds over the objects the caller names (a wall object,
  or a set of panel/post prefixes), instead of hardcoded `WallsOpen`/`Cut`/`Post`.
- `envelope_from_bounds(bounds, model_roof_t, roof_fall, tall_side)` — unchanged maths.
- `band_opening(model_band, envelope_width, corner_width, height_tall, roof_build_up,
  door_head)` — unchanged maths.
- `check_envelope(spec, doc, names)` — unchanged check, caller-supplied object names.

Everything KeterPent97-specific is removed: `WALL_LAYERS`, `MODEL_ROOF_T`,
`ROOF_BUILD_UP`, `FLOOR_BUILD_UP`, `STORE`, `PROVINCE`, `spec_skeleton`, the
nine-row substitution list, the hardcoded `homedepot.ca` URL, and `openings_from_doc`'s
door/transom/louvre literals. `openings_from_doc` becomes
`openings_from_cutters(doc, door_name, band_name, ...)` returning only the two
openings it can actually read from the model; the rest are spec data.

`freecad-model-to-spec` (D5) owns the generic workflow prose and points at these
helpers. A build's locked decisions are written into its own `spec.json` by
`building-from-reference` at intake.

### D5 — `freecad-model-to-spec` is a visible sixth skill

It sits beside the existing `freecad-model-hygiene` and `freecad-render-views`. It
covers: opening a document, choosing which objects bound the envelope, reading the
door and band cutters, deriving the envelope from the model's own roof thickness,
re-placing a band for a different roof build-up, and failing loudly when the model no
longer matches the spec.

Rationale: ingestion is exactly where the photo/drawing/CAD difference lives, so it
must be reachable on its own. It names no store.

### D6 — Builds live outside the repo

The config repo holds no project data. On intake the orchestrator asks for a slug,
never guesses one, and creates:

```
~/Documents/woodbuild/<project-slug>/
├── spec.json        envelope (the fixed invariants), wall/roof/floor build-ups,
│                    openings, substitutions, pricing.store, pricing.province,
│                    pricing.search, options
├── prices.json      the price cache
├── candidates.json  written by the candidate pass, read by the agent
├── decisions.md     prose: why these invariants are what they are
└── out/             budget.html, cutlist.csv, cart.csv, sku-qty.txt, price-deltas.txt
```

Root `~/Documents/woodbuild/` is overridable with a flag. Invariants are machine-
checked where they can be (`spec.envelope` is already the fixed thing, and
`spec.validate()` refuses an envelope that no longer closes); `decisions.md` carries
the human reasoning that cannot be checked.

### D7 — Skill ownership

| skill | owns | must not contain |
|---|---|---|
| `building-from-reference` | intake, invariant naming, reference→wood translation, spec authoring, verification, running the engine | store names, framing rules, nesting constants |
| `wood-framing` | spacings, headers, rafters, blocking, panelisation, datums | prices, stores, spec schema |
| `sheet-and-board-nesting` | kerf, offcut policy, grain locking, shelf packing, yield expectations | framing rules, prices |
| `build-pricing` | candidate pass, agent judgement, provenance, staleness, pack sizes, unpriced honesty | any store name, any tax number |
| `homedepot-catalogue` | HD adapter, store ids, CA tax, availability gaps, MicroPro Sienna, per-SKU price nulls | framing, nesting, pricing policy |
| `freecad-model-to-spec` | model → spec ingestion | stores, prices, framing rules |
| `woodbuild-engine` | all Python, tests, engine API reference | store names, framing policy prose |

The engine's `SKILL.md` documents the API and how to run the tests; it does not
restate the framing or pricing policy that lives in the visible skills.

### D8 — A test enforces the split

`tests/test_boundaries.py` walks `skills/` and asserts:

1. No directory except `homedepot-catalogue/` contains the store's identity
   (`Home Depot`, `homedepot.ca`, `homedepot.com`, `hd_search`, `hd_product`,
   `HD_DEFAULT_STORE`, `MicroPro`) in any `.py` or `.md` —
   **including `tests/`**, so engine tests use neutral source labels (`search`,
   `product`) and legacy labels are recognised only through
   `adapter.candidate_sources`. The bare skill slug `homedepot-catalogue` is
   deliberately **not** banned: it is the path to the adapter, and every visible
   skill must be able to name the file it passes to `--adapter`. The guard itself
   and the engine test that verifies the shipped adapter are the only two exempt
   files, and a test asserts exactly that.
2. `woodbuild/` contains no tax numbers (`TAX_RATES`, province rate literals).
3. Every directory with a `SKILL.md` has a `description` and a `name` matching its
   directory name.
4. `pricing.resolve` works end to end with a fake adapter and asserts the tax arrives
   through the adapter, not from a module constant.

The test is the mechanism that keeps "one thing only" true after this refactor.

## Data flow

```
product page / photo / drawing ── intake ──┐
CAD model ── freecad-model-to-spec ───────┤
                                          ▼
                              spec.json in ~/Documents/woodbuild/<slug>/
                                          │
                    building-from-reference orchestrates:
                    wood-framing rules → frame.derive(spec)
                    split sheet vs board → optimise.pack_sheets / cut_boards
                    bom.build_bom(parts, plans, prices, spec)
                    build-pricing: candidates → agent judges → set_price verifies
                                   through the homedepot-catalogue adapter
                    report.write_report(..., tax_rate=adapter.tax_rate(province))
                                          │
                                          ▼
                    out/budget.html, cutlist.csv, cart.csv, sku-qty.txt
```

## Interfaces

- Skills → engine: `../woodbuild-engine/scripts/woodbuild.py` and the
  `../woodbuild-engine/scripts/` package dir on `sys.path`.
- Skills → store: `../homedepot-catalogue/scripts/homedepot_adapter.py`, passed to the
  CLI as `--adapter`.
- Engine → store: nothing. The adapter is always injected.
- Cache schema: unchanged (`store`, `storeName`, `province`, `currency`, `fetched`,
  `items`, `unpriced`; entries carry `sku`, `desc`, `price`, `url`, `source`,
  `fetched`, `matched_by`, `matched_on`, `why`, `pack`).

## Testing

- Suite moves to `skills/woodbuild-engine/scripts/tests/`; run with
  `python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -v`.
- Existing tests keep passing except those that exercised the deleted KeterPent97
  path (`test_spec_from_freecad.py` is rewritten against `from_model.py` with
  caller-supplied object names and no project constants).
- New: `test_boundaries.py` (D8), `test_adapters.py` (protocol, loader, tax
  injection, offline mode with no adapter).
- The engine stays stdlib-only.

## Migration

1. Create `woodbuild-engine/`, move `woodbuild.py`, `woodbuild/`, and `tests/` there.
2. Split `stock.py` prose out; add `homedepot-catalogue/stock-availability.md`.
3. Add `adapters.py`; strip store constants from `pricing.py`; thread the adapter and
   the tax rate through `cli.py` and `report.py`.
4. Replace `spec_from_freecad.py` with `from_model.py`; delete the project constants.
5. Split the old `SKILL.md` into the orchestrator plus `wood-framing`,
   `sheet-and-board-nesting`, `build-pricing`, `homedepot-catalogue`,
   `freecad-model-to-spec`; move `framing-rules.md` and the HD parts of
   `substitutions.md` to their owners.
6. Delete the old skill directory.
7. Add `test_boundaries.py`; fix whatever it catches.
8. Update `README.md`: "three skills" → the new roster, new test path, workspace root.

## Risks

- **Prompt cost.** Six descriptions, roughly 1.2k characters, are always in context.
  Accepted; the previous single description hid five capabilities.
- **Cross-skill paths.** Relative reach only works while the whole `skills/` tree ships
  together. Stated in both the engine and the orchestrator `SKILL.md`.
- **Engine-as-skill.** A hidden skill used as a library is a mild abuse of the
  mechanism; its `SKILL.md` says so. The alternative (`lib/`) is invisible to pi's
  packaging and would be dropped by an npm install.
- **Behaviour risk in the pricing seam.** Moving tool names behind an adapter can
  silently break a live MCP call. Covered by `test_adapters.py` and one manual
  `--candidates` run against the HD server before the old directory is deleted.
