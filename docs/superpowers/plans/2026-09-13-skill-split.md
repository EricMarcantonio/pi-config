# Skill Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the single `building-from-reference` skill into six single-purpose skills plus a hidden engine skill, with store knowledge confined to one adapter file and no build data in the repo.

**Architecture:** The `woodbuild` Python package becomes the body of a hidden skill (`woodbuild-engine`) that the six visible skills read by relative path. Store knowledge moves behind an injected `StoreAdapter`: the engine names no store, tool, store id or tax rate; `homedepot-catalogue` supplies all of them. One project's hardcoded ingestion constants are deleted and replaced by a generic `from_model` helper module, with project decisions living in each build's own `spec.json` under `~/Documents/woodbuild/<slug>/`.

**Tech Stack:** Python 3 standard library only (no new dependencies); pi skills (directories containing `SKILL.md`); MCP stdio for the Home Depot server; `unittest` for tests.

**Spec:** `docs/superpowers/specs/2026-09-13-skill-split-design.md`

## Global Constraints

- **Stdlib only.** The engine adds no third-party imports. No new `requirements.txt`.
- **Cache schema unchanged.** `prices.json` keeps `store`, `storeName`, `province`, `currency`, `fetched`, `items`, `unpriced`; entries keep `sku`, `desc`, `price`, `url`, `source`, `fetched`, `matched_by`, `matched_on`, `why`, `pack`.
- **No invented prices, no invented quantities.** Unmatched stays `unpriced` with a reason; quantities come from nesting and cutting-stock.
- **Store knowledge lives only in `skills/homedepot-catalogue/`.** No other skill or engine file may contain `homedepot`, `hd_search`, `hd_product`, `HD_DEFAULT_STORE`, `TAX_RATES`, or `MicroPro`. Enforced by `tests/test_boundaries.py` (Task 9).
- **Test command** (works from the repo root; the README's current command is broken — see Task 10):
  `python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts`
  Before Task 1, the same command with `skills/building-from-reference/scripts` in place of `skills/woodbuild-engine/scripts`.
- **Baseline:** 120 tests, `OK (skipped=9)`, at repo root `e044dc4` (spec commit).
- **Commit after every task.** Messages in the existing style, e.g. `skills: move the woodbuild engine into its own skill`.
- **No project data in this repo.** Nothing for KeterPent97 or any other build.

## Spec Amendments (apply before Task 1)

Three details the spec left ambiguous. Edit `docs/superpowers/specs/2026-09-13-skill-split-design.md` first:

1. **D1:** `freecad-model-to-spec/SKILL.md, references/` → `freecad-model-to-spec/SKILL.md` (no `references/` dir; the workflow fits in `SKILL.md`).
2. **D3 adapter table:** add two rows — `server_path` (path to the MCP server entry point, or `None`) and `candidate_sources` (the source labels that mean "not yet verified", including legacy ones such as `hd_search`).
3. **D8 item 1:** state that the guard covers `.py` and `.md` under `skills/` **including `tests/`** — engine tests therefore use neutral source labels (`search`, `product`), and legacy labels are recognised only through `adapter.candidate_sources`.

## File Structure

```
skills/
├── building-from-reference/SKILL.md                  # orchestrator (Task 7)
├── wood-framing/
│   ├── SKILL.md                                      # Task 7
│   └── framing-rules.md                              # git mv from the old skill (Task 7)
├── sheet-and-board-nesting/SKILL.md                  # Task 7
├── build-pricing/SKILL.md                            # Task 8
├── homedepot-catalogue/
│   ├── SKILL.md                                      # Task 6
│   ├── stock-availability.md                         # new prose from stock-catalogue.md (Task 6)
│   ├── substitutions-hd.md                           # git mv of substitutions.md (Task 6)
│   └── scripts/homedepot_adapter.py                  # the only store-naming file (Task 6)
├── freecad-model-to-spec/SKILL.md                    # Task 8
└── woodbuild-engine/
    ├── SKILL.md                                      # Task 8
    └── scripts/
        ├── woodbuild.py                              # moved (Task 1)
        ├── woodbuild/__init__.py                     # moved (Task 1)
        ├── woodbuild/adapters.py                     # new (Task 2)
        ├── woodbuild/cli.py                          # moved, modified (Tasks 4)
        ├── woodbuild/pricing.py                      # moved, modified (Task 3)
        ├── woodbuild/report.py                       # moved, modified (Task 4)
        ├── woodbuild/from_model.py                   # new, replaces spec_from_freecad.py (Task 5)
        ├── woodbuild/stock.py                        # moved, docstring trimmed (Task 6)
        ├── woodbuild/spec.py, frame.py, optimise.py, bom.py   # moved, unchanged
        └── tests/                                    # moved, extended (Tasks 2-5, 9)
```

Deleted: `skills/building-from-reference/` (last of it in Task 8), `woodbuild/spec_from_freecad.py`, `tests/test_spec_from_freecad.py`.

---

### Task 1: Move the engine into its own skill directory

**Files:**
- Move: `skills/building-from-reference/scripts/` → `skills/woodbuild-engine/scripts/`

**Interfaces:**
- Consumes: nothing.
- Produces: every later task edits files under `skills/woodbuild-engine/scripts/`. Import name stays `woodbuild`.

- [ ] **Step 1: Move with git so history follows**

```bash
cd /Users/eric/pi-config
mkdir -p skills/woodbuild-engine
git mv skills/building-from-reference/scripts skills/woodbuild-engine/scripts
git status --short
```

Expected: renames listed as `R  skills/building-from-reference/scripts/... -> skills/woodbuild-engine/scripts/...`.

- [ ] **Step 2: Run the suite from the new path**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 120 tests` and `OK (skipped=9)`.

- [ ] **Step 3: Confirm no stale import of the old path anywhere**

```bash
cd /Users/eric/pi-config
grep -rn "building-from-reference/scripts" --include=*.py --include=*.md skills/ README.md
```

Expected: only `README.md` (fixed in Task 10) and the old `skills/building-from-reference/SKILL.md` (deleted in Task 8).

- [ ] **Step 4: Commit**

```bash
cd /Users/eric/pi-config
git add -A skills/woodbuild-engine skills/building-from-reference
git commit -m "skills: move the woodbuild engine into its own skill directory"
```

---

### Task 2: Add the store adapter protocol

**Files:**
- Create: `skills/woodbuild-engine/scripts/woodbuild/adapters.py`
- Test: `skills/woodbuild-engine/scripts/tests/test_adapters.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `StoreAdapter` (class), `NullAdapter` (class), `AdapterError` (exception), `load_adapter(path) -> StoreAdapter`. Attributes/methods every adapter must have: `name: str`, `server_path: str | None`, `search_tool: str | None`, `product_tool: str | None`, `source_search: str`, `source_product: str`, `candidate_sources: tuple[str, ...]`, `default_store: str | None`, `tax_rate(province: str) -> float`, `env(store: str | None) -> dict`, `is_candidate(source: str) -> bool`. Tasks 3, 4, 6 and 9 use these exact names.

- [ ] **Step 1: Write the failing test**

Create `skills/woodbuild-engine/scripts/tests/test_adapters.py`:

```python
import os
import tempfile
import unittest

from woodbuild.adapters import AdapterError, NullAdapter, StoreAdapter, load_adapter


class TestNullAdapter(unittest.TestCase):
    def test_null_adapter_invents_nothing(self):
        a = NullAdapter()
        self.assertIsNone(a.search_tool)
        self.assertIsNone(a.product_tool)
        self.assertIsNone(a.server_path)
        self.assertIsNone(a.default_store)
        self.assertEqual(a.tax_rate("ON"), 0.0)
        self.assertEqual(a.env("7011"), {})

    def test_null_adapter_knows_search_labels_are_candidates(self):
        a = NullAdapter()
        self.assertTrue(a.is_candidate(a.source_search))
        self.assertFalse(a.is_candidate(a.source_product))
        self.assertFalse(a.is_candidate(None))


class TestLoadAdapter(unittest.TestCase):
    def _write(self, source):
        fd, path = tempfile.mkstemp(suffix="-adapter.py")
        with os.fdopen(fd, "w") as fh:
            fh.write(source)
        self.addCleanup(os.unlink, path)
        return path

    def test_loads_an_adapter_instance_from_a_file(self):
        path = self._write(
            "from woodbuild.adapters import StoreAdapter\n"
            "class A(StoreAdapter):\n"
            "    name = 'fake'\n"
            "    search_tool = 'find'\n"
            "    product_tool = 'verify'\n"
            "    source_search = 'search'\n"
            "    source_product = 'product'\n"
            "    default_store = '0001'\n"
            "    def tax_rate(self, province):\n"
            "        return 0.25\n"
            "ADAPTER = A()\n")
        a = load_adapter(path)
        self.assertEqual(a.name, "fake")
        self.assertEqual(a.search_tool, "find")
        self.assertEqual(a.tax_rate("ON"), 0.25)
        self.assertEqual(a.default_store, "0001")

    def test_a_file_without_an_adapter_is_an_error(self):
        path = self._write("x = 1\n")
        with self.assertRaises(AdapterError):
            load_adapter(path)

    def test_a_missing_file_is_an_error(self):
        with self.assertRaises(AdapterError):
            load_adapter("/nonexistent/adapter.py")

    def test_legacy_candidate_labels_come_from_the_adapter(self):
        path = self._write(
            "from woodbuild.adapters import StoreAdapter\n"
            "class A(StoreAdapter):\n"
            "    candidate_sources = ('search', 'legacy_search')\n"
            "ADAPTER = A()\n")
        a = load_adapter(path)
        self.assertTrue(a.is_candidate("legacy_search"))
        self.assertFalse(a.is_candidate("product"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/eric/pi-config
python3 -m unittest tests.test_adapters -v 2>&1 | tail -5
```

Run it from `skills/woodbuild-engine/scripts` (the tests import `woodbuild` by name). Expected: `ModuleNotFoundError: No module named 'woodbuild.adapters'`.

- [ ] **Step 3: Write the implementation**

Create `skills/woodbuild-engine/scripts/woodbuild/adapters.py`:

```python
"""Store adapter: the only seam between the engine and a shop.

The engine names no store, no MCP tool, no store id and no tax rate. An adapter
supplies all four. `homedepot-catalogue` ships the only real adapter; the tests
ship fakes. With no adapter the engine prices from the cache alone and taxes at
zero, which is the honest answer rather than a guessed store.
"""

import importlib.util
import os


class AdapterError(Exception):
    """A store adapter could not be loaded or does not look like one."""


class StoreAdapter:
    """What a store must supply. Subclass it; no registration is needed."""

    name = "none"
    server_path = None          # entry point for the MCP stdio server, or None
    search_tool = None          # MCP tool used for candidate search
    product_tool = None         # MCP tool used to verify a chosen sku
    source_search = "search"    # label written for a search hit
    source_product = "product"  # label written for a verified product
    candidate_sources = ("search",)   # labels meaning "not yet verified"
    default_store = None

    def tax_rate(self, province):
        """Tax rate for a province code, or 0.0 when the store has no answer."""
        return 0.0

    def env(self, store=None):
        """Extra environment for the MCP subprocess."""
        return {}

    def is_candidate(self, source):
        """True when a price line's source means it still needs verifying."""
        return source in self.candidate_sources


class NullAdapter(StoreAdapter):
    """No store: cached agent-matched prices only, tax 0.0, no lookups."""


def load_adapter(path):
    """Load the `ADAPTER` instance from a python file. Raise AdapterError."""
    if not path or not os.path.exists(path):
        raise AdapterError("adapter file not found: %s" % path)
    spec = importlib.util.spec_from_file_location("woodbuild_adapter", path)
    if spec is None or spec.loader is None:
        raise AdapterError("adapter file is not importable: %s" % path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:                      # a broken adapter is not a store
        raise AdapterError("adapter %s failed to import: %s" % (path, exc))
    adapter = getattr(module, "ADAPTER", None)
    if adapter is None:
        raise AdapterError("adapter %s defines no ADAPTER" % path)
    if not isinstance(adapter, StoreAdapter):
        raise AdapterError("adapter %s is not a StoreAdapter" % path)
    return adapter
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_adapters -v 2>&1 | tail -3
```

Expected: `OK`.

- [ ] **Step 5: Run the whole suite**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 126 tests` (120 + 6), `OK (skipped=9)`.

- [ ] **Step 6: Commit**

```bash
cd /Users/eric/pi-config
git add skills/woodbuild-engine/scripts/woodbuild/adapters.py skills/woodbuild-engine/scripts/tests/test_adapters.py
git commit -m "engine: add the store adapter protocol"
```

---

### Task 3: Take store knowledge out of pricing

**Files:**
- Modify: `skills/woodbuild-engine/scripts/woodbuild/pricing.py`
- Modify: `skills/woodbuild-engine/scripts/woodbuild/__init__.py` (lazy `cli_main`)
- Modify: `skills/woodbuild-engine/scripts/tests/test_pricing.py`

**Interfaces:**
- Consumes: `StoreAdapter`, `NullAdapter` from Task 2.
- Produces: `candidates(spec, transport, adapter=None, classes=None)`, `set_price(cache, cls, sku, why, transport, adapter=None, store=None, today=None, pack=None)`, `resolve(spec, cache, transport=None, adapter=None, refresh=False, today=None)`, `put_matched(cache, cls, entry, why, today=None, pack=None, source="product")`. `tax_rate_for` and `TAX_RATES` are **removed** — Task 4 replaces their callers.

- [ ] **Step 1: Write the failing tests**

In `skills/woodbuild-engine/scripts/tests/test_pricing.py`:

1. Delete `test_tax_rate_lookup` (lines beginning `    def test_tax_rate_lookup` through `self.assertEqual(tax_rate_for("AB"), 0.05)`).
2. Delete the import line `from woodbuild.pricing import (PriceCache, PriceError, PricingTransportError,` … through `resolve, set_price)` and replace with:

```python
from woodbuild.adapters import StoreAdapter
from woodbuild.pricing import (PriceCache, PriceError, PricingTransportError,
                               StdioMCP, candidates, compare, needs_match, put_matched,
                               resolve, set_price)


class FakeAdapter(StoreAdapter):
    """A neutral store: no real product names, no tax table, no store literals."""

    name = "fake"
    search_tool = "find"
    product_tool = "verify"
    source_search = "search"
    source_product = "product"
    candidate_sources = ("search", "legacy_search")
    default_store = "0001"

    def tax_rate(self, province):
        return {"ON": 0.13}.get(province, 0.0)
```

3. Rename `FakeTransport`'s docstring from `"""Stands in for the Home Depot MCP server."""` to `"""Stands in for a store MCP server."""`.
4. Replace every `"hd_product"` source label in the file with `"product"` and every
   `"hd_search"` with `"search"`. Tool-name assertions are a different thing and
   must match the adapter: a call's tool is `FakeAdapter.product_tool` (`"verify"`)
   or `FakeAdapter.search_tool` (`"find"`), never the source label. The `"tried"`
   list in an unpriced reason carries the tool name too.
5. Add `adapter=FakeAdapter()` to every `resolve(...)`, `candidates(...)` and `set_price(...)` call in the file that passes a `transport=`. Leave the offline `resolve(spec, cache, transport=None)` calls alone — the default `None` adapter keeps them working.
6. Add three new tests to `class TestAgentMatchedPricing`:

```python
    def test_tools_come_from_the_adapter_not_the_engine(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "0001", "province": "ON", "items": {}}
        spec = BuildSpec({"pricing": {"store": "0001", "search": {"2x4": "2x4x8 stud"}}})
        transport = FakeTransport({"1000123456": {"name": "stud", "price": 4.25}})
        set_price(cache, "2x4", "1000123456", "the stud", transport,
                  adapter=FakeAdapter(), store="0001", today="2026-09-12")
        self.assertEqual(transport.calls[0][0], "verify")
        self.assertEqual(cache.get("2x4")["source"], "product")

    def test_candidates_use_the_adapter_search_tool_and_default_store(self):
        spec = BuildSpec({"pricing": {"search": {"2x4": "2x4x8 stud"}}})
        transport = FakeTransport({"2x4x8 stud": SEARCH_HIT})
        found = candidates(spec, transport, adapter=FakeAdapter())
        self.assertEqual(transport.calls[0][0], "find")
        self.assertEqual(transport.calls[0][1]["storeId"], "0001")
        self.assertEqual(found["2x4"][0]["sku"], "1000123456")

    def test_refresh_with_no_store_anywhere_is_unpriced_not_guessed(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": None, "province": "ON", "items": {
            "2x4": {"sku": "1", "price": 3.00, "source": "product",
                    "fetched": "2026-01-01", "matched_by": "agent",
                    "matched_on": "2026-01-01", "why": "stud"}}}
        spec = BuildSpec({"pricing": {"search": {"2x4": "2x4x8 stud"}}})

        class NeverCalled:
            def call(self, tool, arguments):
                raise AssertionError("must not query without a store")

        prices = resolve(spec, cache, transport=NeverCalled(), adapter=FakeAdapter(),
                         refresh=True, today="2026-09-12")
        self.assertNotIn("2x4", prices)
        self.assertIn("no store", cache.data["unpriced"]["2x4"]["reason"])
```

7. In the existing `test_set_price_uses_the_spec_store_on_a_storeless_cache`, change
   the final storeless `set_price` call to pass `adapter=FakeAdapter()` while still
   expecting `PriceError` — the test must prove a default store is never used to
   price a class:

```python
        storeless = PriceCache(tmp_path())
        storeless.data = {"items": {}, "unpriced": {}}
        with self.assertRaises(PriceError):
            # FakeAdapter carries a default_store, and it must NOT be used: a price
            # fetched from a default store would later be labelled with the spec's.
            set_price(storeless, "2x4", "1000123456", "x", NeverCalledT(),
                      adapter=FakeAdapter())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_pricing -v 2>&1 | tail -8
```

Expected: FAIL — `ImportError: cannot import name 'tax_rate_for'` (from the untouched test), and `TypeError: ... unexpected keyword argument 'adapter'`.

- [ ] **Step 3: Implement the seam in `pricing.py`**

Apply these edits:

```python
# header: drop the unused imports/constants
import collections
import json
import os
import subprocess
import threading
from datetime import date

from .adapters import NullAdapter

# delete: TAX_RATES = {...} and def tax_rate_for(province)
```

```python
def put_matched(cache, cls, entry, why, today=None, pack=None, source="product"):
    """Record an agent's match. Requires a sku; stamps provenance.

    `pack` is the pack size the price is for, e.g. "50 count" or "295 ml". It
    travels with the match because a per-pack price may only price a pack, never
    a count of pieces. A missing pack is honestly "unknown", never guessed.
    `source` is the label the adapter calls a verified product.
    """
    if not entry or not entry.get("sku"):
        raise ValueError("an agent match needs a sku for class %r" % (cls,))
    today = today or date.today().isoformat()
    rec = dict(entry)
    rec["matched_by"] = "agent"
    rec["matched_on"] = today
    rec["why"] = why
    rec.setdefault("source", source)
    rec.setdefault("fetched", today)
    if pack:
        rec["pack"] = pack
    cache.put(cls, rec)
    cache.data.setdefault("unpriced", {}).pop(cls, None)
    return rec
```

```python
def _adapter(adapter):
    return adapter if adapter is not None else NullAdapter()


def candidates(spec, transport, adapter=None, classes=None):
    """{class: [{sku, name, price, url}]} from the adapter's search tool.

    A search hit is a candidate, never a price: this never touches the cache.
    """
    adapter = _adapter(adapter)
    terms = spec.search_terms()
    chosen = sorted(terms) if classes is None else list(classes)
    store = spec.data.get("pricing", {}).get("store") or adapter.default_store
    out = {}
    for cls in chosen:
        query = terms.get(cls)
        if not query or not adapter.search_tool:
            continue
        try:
            payload = transport.call(adapter.search_tool,
                                     {"query": query, "storeId": store, "pageSize": 5})
        except PricingTransportError:
            out[cls] = []
            continue
        out[cls] = [{"sku": p.get("sku"), "name": p.get("name"),
                     "price": p.get("price"), "url": p.get("url")}
                    for p in ((payload or {}).get("products") or [])
                    if p.get("sku")]
    return out


def set_price(cache, cls, sku, why, transport, adapter=None, store=None, today=None,
              pack=None):
    """Verify the SKU with the adapter's product tool, then record the match.

    `store` must come from the spec: a cache that has never been written has no
    store of its own, and querying a default store would record a price that
    later gets labelled with the spec's store. With no store at all, refuse —
    `adapter.default_store` is for search candidates, which are not prices.
    """
    adapter = _adapter(adapter)
    today = today or date.today().isoformat()
    store_id = str(store or cache.store or "")
    if not store_id:
        raise PriceError("set_price needs a store: pass the spec's store")
    payload = transport.call(adapter.product_tool, {"sku": sku, "storeId": store_id})
    if not payload or payload.get("price") is None:
        raise PricingTransportError("%s returned no price for sku %s"
                                    % (adapter.product_tool, sku))
    entry = {"sku": sku, "desc": payload.get("name"),
             "price": float(payload["price"]), "url": payload.get("url"),
             "source": adapter.source_product, "fetched": today}
    return put_matched(cache, cls, entry, why, today=today, pack=pack,
                       source=adapter.source_product)
```

`woodbuild/__init__.py` also changes: it eagerly imports `cli_main`, which imports `report.py`,
so once `pricing` stops exporting `tax_rate_for` that eager import breaks every
`from woodbuild.pricing import ...`. Replace it with a PEP 562 lazy accessor:

```python
"""woodbuild - reference structure -> wood cutlist, optimised buy plan, priced cart."""
__version__ = "0.1.0"


def __getattr__(name):
    """Expose `cli_main` lazily: importing the package must not pull in the CLI."""
    if name == "cli_main":
        from .cli import cli_main
        return cli_main
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
```

```python
def resolve(spec, cache, transport=None, adapter=None, refresh=False, today=None):
    """Return {stock class: price entry} for agent-matched classes only.

    A script may never accept a search hit as a price: an unmatched class stays
    `unpriced` with reason 'not agent-matched'. With a transport, refresh
    re-verifies the price of an already-matched sku; a stale match is a
    re-matching prompt, never silent trust. A cache priced for a different store
    than the spec is a hard error. With no store id anywhere, a stale class is
    marked unpriced rather than queried against a guessed store.
    """
    adapter = _adapter(adapter)
    today = today or date.today().isoformat()
    cache.load()                 # a cache handed in cold reads its file first
    want_store = spec.data.get("pricing", {}).get("store")
    want_prov = spec.data.get("pricing", {}).get("province")
    if cache.store and want_store and str(cache.store) != str(want_store):
        raise PriceError("price cache is for store %s but the spec says store %s; "
                         "re-point the spec or delete the cache" % (cache.store, want_store))
    if cache.province and want_prov and cache.province != want_prov:
        raise PriceError("price cache is %s but the spec says %s"
                         % (cache.province, want_prov))
    if want_store and not cache.data.get("store"):
        cache.data["store"] = want_store
    if want_prov and not cache.data.get("province"):
        cache.data["province"] = want_prov

    terms = spec.search_terms()
    unpriced = cache.data.setdefault("unpriced", {})
    result = {}
    for cls in terms:
        entry = cache.get(cls)
        if not _is_agent_matched(entry):
            cache.mark_unpriced(cls, "not agent-matched", [])
            continue
        if refresh and transport is not None and cache.is_stale(cls, days=7, today=today):
            # refresh re-verifies an existing match, so it needs the store that
            # match came from. With no store in the spec or the cache, refuse:
            # querying the adapter's default store could record a price for a
            # different store than the one this entry was matched against.
            store_id = str(cache.store or "")
            if not store_id:
                cache.mark_unpriced(cls, "no store configured for a refresh", [])
                continue
            try:
                payload = transport.call(adapter.product_tool,
                                         {"sku": entry["sku"], "storeId": store_id})
            except PricingTransportError as exc:
                cache.mark_unpriced(cls, "transport error: %s" % exc,
                                    [adapter.product_tool])
                continue
            price = (payload or {}).get("price")
            if price is None:
                cache.mark_unpriced(cls, "null price returned", [adapter.product_tool])
                continue
            entry = dict(entry)
            entry.update({"price": float(price),
                          "desc": payload.get("name", entry.get("desc")),
                          "url": payload.get("url", entry.get("url")),
                          "source": adapter.source_product, "fetched": today})
            cache.put(cls, entry)
        unpriced.pop(cls, None)
        result[cls] = entry

    if not terms:                # a spec with no search terms prices every match
        result = {cls: e for cls, e in cache.data.get("items", {}).items()
                  if _is_agent_matched(e)}
    cache.data["fetched"] = today
    return {cls: e for cls, e in result.items() if cls in terms or not terms}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_pricing -v 2>&1 | tail -3
```

Expected: `OK`. If `tax_rate_for` is still imported anywhere, the run fails loudly here — good, Task 4 fixes it.

- [ ] **Step 5: Commit**

```bash
cd /Users/eric/pi-config
git add skills/woodbuild-engine/scripts/woodbuild/pricing.py skills/woodbuild-engine/scripts/tests/test_pricing.py
git commit -m "engine: price through an injected store adapter"
```

---

### Task 4: Thread the adapter and the tax rate through the CLI and the report

**Files:**
- Modify: `skills/woodbuild-engine/scripts/woodbuild/report.py`
- Modify: `skills/woodbuild-engine/scripts/woodbuild/cli.py`
- Modify: `skills/woodbuild-engine/scripts/tests/test_report.py`
- Modify: `skills/woodbuild-engine/scripts/tests/test_cli.py`
- Modify: `skills/woodbuild-engine/scripts/tests/test_bom.py` (neutral source labels only)

**Interfaces:**
- Consumes: `StoreAdapter`/`load_adapter` (Task 2), the new `pricing` signatures (Task 3).
- Produces: `render_html(spec, parts, sheet_plans, board_plans, lines, cache, adapter=None, tax_rate=0.0, today=None)`, `write_report(spec, parts, sheet_plans, board_plans, lines, cache, out_dir, adapter=None, tax_rate=0.0, today=None)`, `cli_main(argv=None)` with `--adapter PATH` and `--server PATH` (no hardcoded default; falls back to `adapter.server_path`).

- [ ] **Step 1: Write the failing tests**

In `test_report.py`:

1. Replace the import line `from woodbuild.pricing import PriceCache` with:

```python
from woodbuild.adapters import StoreAdapter
from woodbuild.pricing import PriceCache


class FakeAdapter(StoreAdapter):
    source_search = "search"
    source_product = "product"
    candidate_sources = ("search", "legacy_search")
```

2. In `setUp`, replace `"source": "hd_search"` with `"source": "search"` (two occurrences in the `prices` dict).
3. Replace the requirement loop in `test_html_has_deviations_before_money_and_required_blocks` — `("ETOBICOKE", "7011", "HST", "13.0", ...)` becomes `("ETOBICOKE", "7011", "tax", "13.0", ...)`, and the `render_html(...)` call gains `tax_rate=0.13, adapter=FakeAdapter()`.
4. Replace every remaining `"hd_search"` / `"hd_product"` string in the file with `"search"` / `"product"`, and every `render_html(...)`/`write_report(...)` call gains `adapter=FakeAdapter(), tax_rate=0.13`.
5. Add to `class TestReport`:

```python
    def test_tax_comes_from_the_caller_not_a_module_table(self):
        html = render_html(self.spec, self.parts, self.sheets, self.boards,
                           self.lines, self.cache, adapter=FakeAdapter(),
                           tax_rate=0.05, today="2026-09-12")
        t = totals(self.lines, 0.05)
        self.assertIn("5.0%", html)
        self.assertIn("%.2f" % t["total"], html)
        self.assertNotIn("13.0%", html)
```

In `test_cli.py`:

1. Change the `prices.json` fixture's `"source": "hd_search"` to `"source": "search"`.
2. In `STUB_MCP`, rename the tool branch `if name == "hd_product":` to `if name == "verify":`, and add a module-level fake adapter file writer:

```python
ADAPTER_PY = '''
from woodbuild.adapters import StoreAdapter

class A(StoreAdapter):
    name = "test-store"
    search_tool = "find"
    product_tool = "verify"
    source_search = "search"
    source_product = "product"
    default_store = "7011"
    server_path = None

ADAPTER = A()
'''
```

3. Add `self.adapter = os.path.join(self.dir, "adapter.py")` to `setUp` and write `ADAPTER_PY` into it.
4. Add `"--adapter", self.adapter` to every `cli_main([...])` call that uses `--server`.
5. In `test_bom.py`, replace the two store source labels with the neutral pair:
   `"hd_product"` → `"product"` at line 32 and `"hd_search"` → `"search"` at lines
   66 and 71 (the assertion at 71 asserts the label it just set, so it changes too).
   `bom.py` copies a price entry's `source` through, so no production code changes.
6. Add to `class TestCLI`:

```python
    def test_offline_run_without_an_adapter_reports_zero_tax(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        html = open(os.path.join(self.out, "budget.html")).read()
        self.assertIn("tax 0.0%", html)

    def test_adapter_supplies_the_tax_rate(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--adapter", self.adapter,
                       "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        html = open(os.path.join(self.out, "budget.html")).read()
        self.assertIn("tax 0.0%", html)   # the test adapter declares no tax table
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_report tests.test_cli 2>&1 | tail -6
```

Expected: FAIL — `render_html() got an unexpected keyword argument 'adapter'`, and `unrecognized arguments: --adapter`.

- [ ] **Step 3: Implement in `report.py`**

```python
# imports: drop the tax import
from . import bom, stock
from .bom import totals, unpriced
```

```python
def _provenance(line, cache, adapter=None):
    """What backs a line's price: an agent match, a raw candidate, or nothing.

    Returns (label, warn). The cache entry is authoritative: a line built from
    an agent-matched class is labelled 'agent' even if the line carries a search
    source, and a search entry with no matched_by is a candidate that still
    needs verifying. Which labels mean 'candidate' is the adapter's business.
    """
    entry = cache.get(line.stock) if cache is not None else None
    if entry and entry.get("matched_by") == "agent":
        return "agent", False
    if adapter is not None and adapter.is_candidate(line.source):
        return "candidate - verify", True
    if line.unit_price is None:
        return "unpriced", True
    return (line.source or "-"), False
```

```python
def render_html(spec, parts, sheet_plans, board_plans, lines, cache, adapter=None,
                tax_rate=0.0, today=None):
    t = totals(lines, tax_rate)
```

Then in the same function: replace the subtitle's `"HST %.1f%%"` / `tax_rate_for(cache.province or "ON") * 100` pair with

```python
           "<p class=sub>store %s &middot; %s &middot; price cache %s &middot; "
           "tax %.1f%% &middot; generated %s</p>"
           % (e(str(cache.store)), e(str(cache.data.get("storeName") or "")),
              e(str(cache.fetched)), tax_rate * 100, e(today or ""))]
```

replace the cards' `("HST", "$%.2f" % t["tax"])` with `("tax", "$%.2f" % t["tax"])`, replace `if line.source == "hd_search":` with

```python
        if adapter is not None and adapter.is_candidate(line.source):
```

and replace `prov, warn = _provenance(line, cache)` with `prov, warn = _provenance(line, cache, adapter)`.

```python
def write_report(spec, parts, sheet_plans, board_plans, lines, cache, out_dir,
                 adapter=None, tax_rate=0.0, today=None):
```

and inside it pass both through: `render_html(spec, parts, sheet_plans, board_plans, lines, cache, adapter, tax_rate, today)`.

- [ ] **Step 4: Implement in `cli.py`**

```python
"""woodbuild CLI: build spec in, workbook + CSVs out."""

import argparse
import os
import sys

from . import adapters, bom, frame, optimise, pricing, report, stock
from .optimise import NestError
from .spec import BuildSpec, SpecError


def _build_transport(server, adapter, spec, cache):
    """The MCP stdio client, or None when this run needs no lookups."""
    server = server or getattr(adapter, "server_path", None)
    if not server or not os.path.exists(server):
        return None, server
    store = str(spec.data.get("pricing", {}).get("store")
                or cache.store or adapter.default_store or "")
    env = dict(os.environ, **(adapter.env(store) if store else {}))
    if server.endswith(".py"):
        command, server_args = sys.executable, [server]
    else:
        command, server_args = "node", [server]
    return pricing.StdioMCP(command, server_args, env=env), server
```

Replace the argument definitions:

```python
    ap.add_argument("--today", default=None)
    ap.add_argument("--server", default=None,
                    help="MCP server entry point; defaults to the adapter's server_path")
    ap.add_argument("--adapter", default=None,
                    help="python file defining an ADAPTER StoreAdapter instance")
```

Replace the `HD_SERVER` constant and everything from `cache = pricing.PriceCache(args.prices)` through the `finally:` block with:

```python
    cache = pricing.PriceCache(args.prices)
    cache.load()
    try:
        adapter = adapters.load_adapter(args.adapter) if args.adapter else adapters.NullAdapter()
    except adapters.AdapterError as exc:
        print("adapter error: %s" % exc, file=sys.stderr)
        return 2
    province = (spec.data.get("pricing", {}).get("province")
                or cache.data.get("province") or "")
    tax_rate = adapter.tax_rate(province)
    uses_transport = args.fetch or args.candidates or args.set_price
    transport, server_path = _build_transport(args.server, adapter, spec, cache) \
        if uses_transport else (None, None)
    if uses_transport and transport is None:
        print("pricing error: no MCP server; pass --server or use an adapter with "
              "server_path (looked at %s)" % (args.server or adapter.server_path),
              file=sys.stderr)
        return 2
    try:
        if args.set_price:
            cls, sku = args.set_price
            if cls not in spec.search_terms():
                print("warning: %s is not in the spec's pricing.search map, so it "
                      "will never appear in a budget" % cls, file=sys.stderr)
            try:
                pricing.set_price(cache, cls, sku, args.why or "", transport,
                                  adapter=adapter,
                                  store=spec.data.get("pricing", {}).get("store"),
                                  today=args.today, pack=args.pack)
            except (pricing.PriceError, pricing.PricingTransportError) as exc:
                print("pricing error: %s" % exc, file=sys.stderr)
                return 2
            cache.save()
            entry = cache.get(cls)
            print("agent-matched %s -> %s %s ($%.2f)%s" %
                  (cls, entry.get("sku"), entry.get("desc") or "", entry.get("price") or 0.0,
                   " [%s]" % entry["pack"] if entry.get("pack") else ""))
            return 0
        if args.candidates:
            pending = pricing.needs_match(spec, cache, today=args.today)
            found = pricing.candidates(spec, transport, adapter=adapter, classes=pending)
            if not os.path.isdir(args.out):
                os.makedirs(args.out)
            path = os.path.join(args.out, "candidates.json")
            import json
            with open(path, "w") as fh:
                json.dump(found, fh, indent=2, sort_keys=True)
                fh.write("\n")
            print("%d class(es) need an agent match; candidates written to %s"
                  % (len(pending), path))
            return 0
        prices = pricing.resolve(spec, cache, transport=transport, adapter=adapter,
                                 refresh=args.fetch, today=args.today)
    except pricing.PriceError as exc:
        print("pricing error: %s" % exc, file=sys.stderr)
        return 2
    finally:
        if transport:
            transport.close()
    cache.save()
```

Replace the report/tax tail:

```python
    lines = bom.build_bom(parts, sheet_plans, board_plans, prices=prices, spec=spec.data)
    paths = report.write_report(spec, parts, sheet_plans, board_plans, lines, cache,
                                args.out, adapter=adapter, tax_rate=tax_rate,
                                today=args.today)

    t = bom.totals(lines, tax_rate)
    if not province:
        print("note: no province in the spec or cache; tax reported as 0.0%%",
              file=sys.stderr)
    print("%s: %d parts, %d sheet plan(s), %d board plan(s)" %
          (spec.data.get("build"), len(parts), len(sheet_plans), len(board_plans)))
    print("subtotal $%.2f + tax $%.2f = $%.2f (%d lines, %d unpriced, tax rate %.3f)" %
          (t["subtotal"], t["tax"], t["total"], t["lines"], t["unpriced"], tax_rate))
    pending = pricing.needs_match(spec, cache, today=args.today)
    print("agent-matched: %d, unmatched: %d" %
          (len(spec.search_terms()) - len(pending), len(pending)))
    matched = sum(1 for l in lines if adapter.is_candidate(l.source))
    if matched:
        print("unverified description-matched lines: %d (verify SKUs before ordering)"
              % matched)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 131 tests`, `OK (skipped=9)`.

- [ ] **Step 6: Prove no tax or store literal is left in the engine**

```bash
cd /Users/eric/pi-config
grep -rn "TAX_RATES\|tax_rate_for\|HD_SERVER\|HD_DEFAULT_STORE\|hd_product\|hd_search\|homedepot" skills/woodbuild-engine/scripts/ 2>/dev/null
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
cd /Users/eric/pi-config
git add skills/woodbuild-engine/scripts/woodbuild/report.py skills/woodbuild-engine/scripts/woodbuild/cli.py \
        skills/woodbuild-engine/scripts/tests/test_report.py skills/woodbuild-engine/scripts/tests/test_cli.py
git commit -m "engine: inject the adapter and the tax rate through report and cli"
```

---

### Task 5: Replace the project extractor with a generic `from_model`

**Files:**
- Create: `skills/woodbuild-engine/scripts/woodbuild/from_model.py`
- Delete: `skills/woodbuild-engine/scripts/woodbuild/spec_from_freecad.py`
- Create: `skills/woodbuild-engine/scripts/tests/test_from_model.py`
- Delete: `skills/woodbuild-engine/scripts/tests/test_spec_from_freecad.py`
- Modify: `skills/woodbuild-engine/scripts/tests/test_real_build.py`

**Interfaces:**
- Consumes: `BuildSpec`, `SpecError` from `woodbuild.spec`.
- Produces: `bounds_from_shapes(boxes) -> tuple[float, float, float, float, float, float]` (xmin, xmax, ymin, ymax, zmin, zmax); `envelope_from_bounds(bounds, model_roof_t, roof_fall, tall_side="front") -> dict`; `wall_bounds(doc, wall_object=None, panel_suffixes=("Cut", "CutL", "CutR"), post_prefixes=("Post",)) -> tuple`; `band_opening(model_band, envelope_width, corner_width, height_tall, roof_build_up, door_head) -> dict`; `openings_from_cutters(doc, envelope, door_name="fw_door", band_name="fw_band", corner_width=89.0, roof_build_up=0.0, extra=())  -> list[dict]`; `check_envelope(spec, doc, **wall_bounds_kwargs) -> None`.

- [ ] **Step 1: Write the failing test**

Create `skills/woodbuild-engine/scripts/tests/test_from_model.py`:

```python
import unittest

from woodbuild.from_model import (band_opening, bounds_from_shapes,
                                  envelope_from_bounds)
from woodbuild.spec import BuildSpec


class TestBounds(unittest.TestCase):
    def test_bounds_union_of_shapes(self):
        # no FreeCAD needed: two panels whose union is the wall envelope
        got = bounds_from_shapes([[0.0, 2788.92, 0.0, 2179.32, 2100.0, 2178.06],
                                  [0.0, 2788.92, 0.0, 2179.32, 0.0, 2100.0]])
        self.assertEqual(got, (0.0, 2788.92, 0.0, 2179.32, 0.0, 2178.06))

    def test_no_shapes_is_an_error_not_an_empty_envelope(self):
        from woodbuild.spec import SpecError
        with self.assertRaises(SpecError):
            bounds_from_shapes([])


class TestEnvelope(unittest.TestCase):
    def test_envelope_uses_the_model_roof_top_not_the_wood_build_up(self):
        # the model's wall top is its roof underside; add the MODEL's own roof
        # thickness (80 mm) to recover the product's overall height. The wood
        # roof build-up is a spec decision, not an envelope input.
        env = envelope_from_bounds((0.0, 2788.92, 0.0, 2179.32, 0.0, 2178.06),
                                   model_roof_t=80.0, roof_fall=200.0)
        self.assertAlmostEqual(env["width"], 2788.92)
        self.assertAlmostEqual(env["depth"], 2179.32)
        self.assertAlmostEqual(env["height_tall"], 2258.06)
        self.assertEqual(env["roof_fall"], 200.0)
        self.assertEqual(env["tall_side"], "front")

    def test_tall_side_is_a_parameter(self):
        env = envelope_from_bounds((0.0, 1000.0, 0.0, 2000.0, 0.0, 1000.0),
                                   model_roof_t=80.0, roof_fall=0.0, tall_side="back")
        self.assertEqual(env["tall_side"], "back")


class TestBand(unittest.TestCase):
    def test_band_sill_is_recomputed_for_a_thicker_roof(self):
        # a 120 mm wood roof build-up vs the model's 80 mm resin roof lowers the
        # band by 40 mm, keeping the band under an unchanged envelope while
        # staying above the door head
        band = band_opening(model_band=(2698.92, 300.0, 1878.06),
                            envelope_width=2788.92, corner_width=89.0,
                            height_tall=2258.06, roof_build_up=120.0,
                            door_head=1811.02)
        self.assertAlmostEqual(band["width"], 2610.92)
        self.assertAlmostEqual(band["sill"], 1838.06)
        self.assertAlmostEqual(band["height"], 300.0)
        self.assertGreaterEqual(band["sill"], 1811.02)

    def test_a_band_that_would_not_clear_the_door_head_is_refused(self):
        from woodbuild.spec import SpecError
        with self.assertRaises(SpecError):
            band_opening(model_band=(2698.92, 300.0, 1878.06),
                         envelope_width=2788.92, corner_width=89.0,
                         height_tall=2258.06, roof_build_up=400.0,
                         door_head=1811.02)


if __name__ == "__main__":
    unittest.main()
```

6. The three `doc`-touching wrappers are tested too, with a stub document — no
   FreeCAD needed, because they are duck-typed (`doc.Objects`, `doc.getObject`,
   `obj.Name`, `obj.Shape.isNull()`, `obj.Shape.BoundBox` with
   `XMin/XMax/YMin/YMax/ZMin/ZMax` and `XLength/ZLength/ZMax`), and a stub is the
   real shape of the input, not a mock of the module under test. Add this to
   `test_from_model.py`, and add `wall_bounds`, `openings_from_cutters` and
   `check_envelope` to its imports (and drop the unused `BuildSpec` import):

```python
class StubBox:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.XMin, self.XMax = xmin, xmax
        self.YMin, self.YMax = ymin, ymax
        self.ZMin, self.ZMax = zmin, zmax

    @property
    def XLength(self):
        return self.XMax - self.XMin

    @property
    def ZLength(self):
        return self.ZMax - self.ZMin


class StubShape:
    def __init__(self, box):
        self.BoundBox = box

    def isNull(self):
        return self.BoundBox is None


class StubObj:
    def __init__(self, name, box):
        self.Name = name
        self.Shape = StubShape(box)


class StubDoc:
    def __init__(self, objs):
        self.Objects = objs

    def getObject(self, name):
        return next((o for o in self.Objects if o.Name == name), None)


class TestWallBounds(unittest.TestCase):
    def test_wall_object_wins_over_the_naming_convention(self):
        doc = StubDoc([StubObj("WallsOpen", StubBox(0, 10, 0, 20, 0, 30)),
                       StubObj("panelCut", StubBox(0, 999, 0, 999, 0, 999))])
        self.assertEqual(wall_bounds(doc, wall_object="WallsOpen"),
                         (0, 10, 0, 20, 0, 30))

    def test_naming_convention_selects_panels_and_posts(self):
        doc = StubDoc([StubObj("sideCut", StubBox(0, 10, 0, 20, 0, 30)),
                       StubObj("Post1", StubBox(-5, 10, 0, 20, 0, 30)),
                       StubObj("ignored", StubBox(0, 500, 0, 500, 0, 500))])
        self.assertEqual(wall_bounds(doc), (-5, 10, 0, 20, 0, 30))

    def test_a_model_with_neither_is_refused(self):
        with self.assertRaises(SpecError):
            wall_bounds(StubDoc([StubObj("ignored", StubBox(0, 1, 0, 1, 0, 1))]))

    def test_a_missing_named_object_is_refused(self):
        with self.assertRaises(SpecError):
            wall_bounds(StubDoc([]), wall_object="WallsOpen")


class TestCutters(unittest.TestCase):
    ENVELOPE = {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                "roof_fall": 200.0, "tall_side": "front"}

    def _doc(self):
        return StubDoc([StubObj("fw_door", StubBox(0, 1386.84, 0, 1, 0, 1811.02)),
                        StubObj("fw_band", StubBox(0, 2698.92, 0, 1, 1878.06, 2178.06))])

    def test_door_and_band_read_from_the_model(self):
        got = openings_from_cutters(self._doc(), self.ENVELOPE, corner_width=89.0,
                                    roof_build_up=120.0)
        door, band = got[0], got[1]
        self.assertEqual(door["kind"], "door")
        self.assertAlmostEqual(door["width"], 1386.84)
        self.assertAlmostEqual(door["height"], 1811.02)
        self.assertAlmostEqual(band["width"], 2610.92)
        self.assertAlmostEqual(band["sill"], 1838.06)

    def test_extra_openings_are_appended_in_order(self):
        extra = [{"wall": "left", "kind": "transom", "width": 595.0,
                  "height": 220.0, "sill": 1511.02, "header": None}]
        got = openings_from_cutters(self._doc(), self.ENVELOPE, corner_width=89.0,
                                    roof_build_up=120.0, extra=extra)
        self.assertEqual([o["kind"] for o in got], ["door", "band", "transom"])

    def test_missing_cutters_are_refused(self):
        with self.assertRaises(SpecError):
            openings_from_cutters(StubDoc([]), self.ENVELOPE)


class TestEnvelopeCheck(unittest.TestCase):
    class StubSpec:
        envelope = {"width": 2788.92, "depth": 2179.32, "height_tall": 2258.06,
                    "roof_fall": 200.0, "tall_side": "front"}

    def test_a_matching_model_passes(self):
        doc = StubDoc([StubObj("WallsOpen",
                               StubBox(0, 2788.92, 0, 2179.32, 0, 2178.06))])
        check_envelope(self.StubSpec(), doc, wall_object="WallsOpen")

    def test_a_moved_model_is_refused(self):
        doc = StubDoc([StubObj("WallsOpen",
                               StubBox(0, 2800.0, 0, 2179.32, 0, 2178.06))])
        with self.assertRaises(SpecError):
            check_envelope(self.StubSpec(), doc, wall_object="WallsOpen")
```

Then retarget `test_real_build.py`'s paths to the new workspace convention. That
file gains **no** new test — it stays the optional end-to-end check, and the
wrappers are covered by the stub tests above:

```python
BUILD_DIR = os.path.expanduser("~/Documents/woodbuild/keter-pent97")
SPEC_PATH = os.path.join(BUILD_DIR, "spec.json")
PRICES = os.path.join(BUILD_DIR, "prices.json")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_from_model -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'woodbuild.from_model'`.

- [ ] **Step 3: Write the implementation**

Create `skills/woodbuild-engine/scripts/woodbuild/from_model.py`:

```python
"""FreeCAD document -> build spec, generically.

Nothing here knows a project. Object names, the model's own roof thickness, the
roof fall and the corner width are all arguments. A build's locked decisions —
wall layers, roof build-up, floor build-up, store, substitutions — are spec data
written by `building-from-reference` at intake, never constants in this module.

This is the only module in the engine that may import FreeCAD, and only inside
the functions that need it, so the pure helpers stay testable without it.
"""

from .spec import SpecError


def bounds_from_shapes(boxes):
    """Union of [xmin, xmax, ymin, ymax, zmin, zmax] boxes."""
    boxes = list(boxes)
    if not boxes:
        raise SpecError("no shapes to bound the envelope")
    return (min(b[0] for b in boxes), max(b[1] for b in boxes),
            min(b[2] for b in boxes), max(b[3] for b in boxes),
            min(b[4] for b in boxes), max(b[5] for b in boxes))


def envelope_from_bounds(bounds, model_roof_t, roof_fall, tall_side="front"):
    """Build the envelope from the model's wall bounds.

    In the model the wall top IS the roof underside, so the product's overall
    height is that z plus the MODEL's own roof thickness. A wood roof build-up is
    a spec decision and must not enter the envelope.
    """
    xmin, xmax, ymin, ymax, _zmin, zmax_wall = bounds
    return {"width": round(xmax - xmin, 2), "depth": round(ymax - ymin, 2),
            "height_tall": round(zmax_wall + model_roof_t, 2),
            "roof_fall": float(roof_fall), "tall_side": tall_side}


def _shape_box(obj):
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return None
    bb = shape.BoundBox
    return [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]


def wall_bounds(doc, wall_object=None, panel_suffixes=("Cut", "CutL", "CutR"),
                post_prefixes=("Post",)):
    """Bounds of the wall envelope: `wall_object` when given, else the panels.

    The caller names its own objects: a modelled wall solid by name, or the panel
    and post naming convention of the model. No project names are baked in.
    """
    if wall_object:
        obj = doc.getObject(wall_object)
        if obj is None:
            raise SpecError("model has no object named %s" % wall_object)
        box = _shape_box(obj)
        if box is None:
            raise SpecError("%s has no shape" % wall_object)
        return tuple(box)
    boxes = []
    for obj in doc.Objects:
        name = obj.Name
        if not (name.endswith(tuple(panel_suffixes))
                or name.startswith(tuple(post_prefixes))):
            continue
        box = _shape_box(obj)
        if box:
            boxes.append(box)
    if not boxes:
        raise SpecError("model has neither %s nor objects starting with %s"
                        % (wall_object or "a wall solid", ", ".join(post_prefixes)))
    return bounds_from_shapes(boxes)


def band_opening(model_band, envelope_width, corner_width, height_tall,
                 roof_build_up, door_head):
    """Re-place a clerestory band for a different roof build-up and corner width.

    The band spans between the corners, not the moulded posts, and sits under the
    roof build-up, so it both narrows and drops when the build-up grows. Dropping
    it keeps the band's own height under an unchanged envelope while staying above
    the door head; if it cannot, that is a spec error, not a clamp.
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


def openings_from_cutters(doc, envelope, door_name="fw_door", band_name="fw_band",
                          corner_width=89.0, roof_build_up=0.0, extra=()):
    """Read the door and the band from the model's own cutter objects.

    Everything else an opening needs — transoms, louvres, headers, sills — is
    spec data the caller supplies through `extra`, because a model's cutters do
    not carry intent.
    """
    door = doc.getObject(door_name)
    band = doc.getObject(band_name)
    if door is None or band is None:
        raise SpecError("model is missing %s / %s cutters" % (door_name, band_name))
    dbb = door.Shape.BoundBox
    bbb = band.Shape.BoundBox
    door_head = round(dbb.ZMax, 2)
    band_block = band_opening(
        model_band=(round(bbb.XLength, 2), round(bbb.ZLength, 2), round(bbb.ZMin, 2)),
        envelope_width=envelope["width"], corner_width=corner_width,
        height_tall=envelope["height_tall"], roof_build_up=roof_build_up,
        door_head=door_head)
    return [{"wall": "front", "kind": "door", "width": round(dbb.XLength, 2),
             "height": round(dbb.ZLength, 2), "sill": 0.0, "header": "2x8"},
            band_block] + list(extra)


def check_envelope(spec, doc, **wall_bounds_kwargs):
    """Fail loudly if the model no longer matches the spec."""
    xmin, xmax, ymin, ymax, _zmin, _zmax = wall_bounds(doc, **wall_bounds_kwargs)
    env = spec.envelope
    width = xmax - xmin
    depth = ymax - ymin
    if abs(width - env["width"]) > 1.0 or abs(depth - env["depth"]) > 1.0:
        raise SpecError("envelope mismatch: model is %.1f x %.1f mm, spec says "
                        "%.1f x %.1f mm" % (width, depth, env["width"], env["depth"]))
```

- [ ] **Step 4: Delete the project extractor and its test**

```bash
cd /Users/eric/pi-config
git rm skills/woodbuild-engine/scripts/woodbuild/spec_from_freecad.py \
       skills/woodbuild-engine/scripts/tests/test_spec_from_freecad.py
grep -rn "spec_from_freecad\|spec_skeleton" skills/woodbuild-engine/scripts/ || echo "no references left"
```

Expected: only test names in old docs; no code references.

- [ ] **Step 5: Run the suite**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 141 tests` (131 − 5 extractor tests + 15 new: 6 pure + 9 stub-doc), `OK (skipped=9)`.

- [ ] **Step 6: Commit**

```bash
cd /Users/eric/pi-config
git add -A skills/woodbuild-engine/scripts
git commit -m "engine: replace the project extractor with a generic from_model"
```

---

### Task 6: Create `homedepot-catalogue` with the only store adapter

**Files:**
- Create: `skills/homedepot-catalogue/scripts/homedepot_adapter.py`
- Create: `skills/homedepot-catalogue/SKILL.md`
- Create: `skills/homedepot-catalogue/stock-availability.md`
- Move: `skills/building-from-reference/substitutions.md` → `skills/homedepot-catalogue/substitutions-hd.md`
- Modify: `skills/woodbuild-engine/scripts/woodbuild/stock.py` (docstring only)
- Test: `skills/woodbuild-engine/scripts/tests/test_adapters.py` (add one case)

**Interfaces:**
- Consumes: `StoreAdapter` (Task 2), the tool names the HD MCP server exposes (`hd_search`, `hd_product`), `HD_DEFAULT_STORE`.
- Produces: `ADAPTER` — the instance `load_adapter(...)` returns; store id `7011`; CA tax table; candidate labels `("hd_search", "search")`.

- [ ] **Step 1: Write the failing test**

Add to `class TestLoadAdapter` in `skills/woodbuild-engine/scripts/tests/test_adapters.py`:

```python
    def test_the_shipped_store_adapter_satisfies_the_protocol(self):
        import json
        import pathlib
        repo = pathlib.Path(__file__).resolve().parents[4]
        path = repo / "skills" / "homedepot-catalogue" / "scripts" / "homedepot_adapter.py"
        self.assertTrue(path.exists(), "the store adapter must exist at %s" % path)
        a = load_adapter(str(path))
        self.assertEqual(a.search_tool, "hd_search")
        self.assertEqual(a.product_tool, "hd_product")
        self.assertEqual(a.default_store, "7011")
        self.assertAlmostEqual(a.tax_rate("ON"), 0.13)
        self.assertAlmostEqual(a.tax_rate("ZZ"), 0.0)
        self.assertTrue(a.is_candidate("hd_search"))
        self.assertFalse(a.is_candidate("hd_product"))
        self.assertTrue(str(a.server_path).endswith("index.js"))
        self.assertEqual(a.env("7011"), {"HD_DEFAULT_STORE": "7011"})
        json.dumps({})          # the module must not need a config file to load
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_adapters.TestLoadAdapter.test_the_shipped_store_adapter_satisfies_the_protocol -v 2>&1 | tail -5
```

Expected: FAIL — `AssertionError: the store adapter must exist at .../skills/homedepot-catalogue/scripts/homedepot_adapter.py`.

- [ ] **Step 3: Write the adapter**

Create `skills/homedepot-catalogue/scripts/homedepot_adapter.py`:

```python
"""Home Depot Canada: the only file in this repository that names a store.

Everything store-specific lives here: the MCP tool names, the store id, the
machine-local server path, the provincial tax table and the availability labels.
The engine takes this as data through `woodbuild.adapters.StoreAdapter`, so a
different retailer is a different file like this one and no engine change.

Pass it to the CLI:  --adapter skills/homedepot-catalogue/scripts/homedepot_adapter.py
"""

import os

from woodbuild.adapters import StoreAdapter

# 2026 rates. A rate that is not listed returns 0.0: a guessed tax is worse than
# no tax, and the CLI prints a note when it reports zero.
TAX_RATES = {"ON": 0.13, "AB": 0.05, "BC": 0.12, "QC": 0.14975, "MB": 0.12,
             "SK": 0.11, "NS": 0.15, "NB": 0.15, "NL": 0.15, "PE": 0.15}

# Machine-local clone of the Home Depot MCP server; see README for how to restore it.
DEFAULT_SERVER = os.path.expanduser(
    "~/.pi/agent/mcp-servers/mcp_homedepot/dist/index.js")

PROVINCE_ALIASES = {"ONTARIO": "ON", "ALBERTA": "AB", "BRITISH COLUMBIA": "BC",
                    "QUEBEC": "QC", "QUÉBEC": "QC", "MANITOBA": "MB",
                    "SASKATCHEWAN": "SK", "NOVA SCOTIA": "NS",
                    "NEW BRUNSWICK": "NB", "NEWFOUNDLAND": "NL",
                    "PRINCE EDWARD ISLAND": "PE"}


class HomeDepotCanada(StoreAdapter):
    name = "homedepot-ca"
    server_path = os.environ.get("HD_SERVER_PATH") or DEFAULT_SERVER
    search_tool = "hd_search"
    product_tool = "hd_product"
    source_search = "hd_search"      # kept: existing caches carry this label
    source_product = "hd_product"
    candidate_sources = ("hd_search", "search")
    default_store = "7011"           # the store the shed build was priced against

    def tax_rate(self, province):
        code = (province or "").strip().upper()
        code = PROVINCE_ALIASES.get(code, code)
        return TAX_RATES.get(code, 0.0)

    def env(self, store=None):
        store = str(store or self.default_store)
        return {"HD_DEFAULT_STORE": store}


ADAPTER = HomeDepotCanada()
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd /Users/eric/pi-config/skills/woodbuild-engine/scripts
python3 -m unittest tests.test_adapters -v 2>&1 | tail -3
```

Expected: `OK` (7 tests).

- [ ] **Step 5: Move the store prose in, and trim the engine docstring**

```bash
cd /Users/eric/pi-config
git mv skills/building-from-reference/substitutions.md \
       skills/homedepot-catalogue/substitutions-hd.md
```

Create `skills/homedepot-catalogue/stock-availability.md` with exactly these sections, moved verbatim from `skills/building-from-reference/stock-catalogue.md`:

````markdown
# What the store actually carries

Learned the hard way, one unpriced or wrong line at a time. Prices and stock are
per SKU and per store, never per product line.

## Consumables

Screws, nails, adhesive, sealant, hinges, hasp, louvre, steel roofing and pad
material are not stock classes: `bom.consumables()` invents their keys and emits
**physical amounts** (pieces, ml). Their prices are keyed the same way in the spec's
`pricing.search` map.

## What the store does not have

- **No ground-contact rated 2x4 pressure-treated lumber.** The ground-contact range
  is 4x4 / 4x6 / 5x5 / 6x6 posts only; every 2x4 PT board is "Above Ground Use
  Only". Design so that only skids need ground contact — joists on skids and a sole
  plate on a deck are above grade, which makes above-ground PT correct there. See
  `substitutions-hd.md`.
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
````

Then edit `skills/woodbuild-engine/scripts/woodbuild/stock.py`'s docstring from:

```python
"""Home Depot Canada stock catalogue: sheet goods, dimensional lumber, kerf.

All sizes in mm. Imperial names are kept because that is what the store sells
and what a builder asks for at the saw.
"""
```

to:

```python
"""Stock geometry catalogue: sheet goods, dimensional lumber, kerf.

All sizes in mm. Imperial names are kept because that is what a builder asks for
at the saw. This module knows geometry, not availability: whether a store carries
a class is the store adapter's business.
"""
```

- [ ] **Step 6: Write the skill**

Create `skills/homedepot-catalogue/SKILL.md`:

````markdown
---
name: homedepot-catalogue
description: Use when sourcing or pricing a build from Home Depot Canada — finding the right SKU for a stock class, resolving a per-store price, or deciding what to buy when the store does not carry the ideal material.
---

# Home Depot catalogue

The store-specific half of pricing. `build-pricing` holds the method; this skill
holds everything that names a shop.

## Adapter

`scripts/homedepot_adapter.py` is the only file in the repository that names a
store. It supplies the MCP tool names, the store id, the provincial tax table and
the availability labels to the engine, which knows none of them:

```bash
python3 ../woodbuild-engine/scripts/woodbuild.py \
  --spec <workspace>/spec.json --prices <workspace>/prices.json \
  --out <workspace>/out --adapter scripts/homedepot_adapter.py
```

Without `--adapter` the engine prices from the cache only and reports tax as zero.

## MCP server

`server_path` defaults to `~/.pi/agent/mcp-servers/mcp_homedepot/dist/index.js`
(override with `HD_SERVER_PATH`). The clone is machine-local and gitignored; to
restore it:

```bash
git clone https://github.com/sstepanovvl/mcp_homedepot.git \
  ~/.pi/agent/mcp-servers/mcp_homedepot
cd ~/.pi/agent/mcp-servers/mcp_homedepot && npm install && npm run build
```

`HD_DEFAULT_STORE` is set from the spec's `pricing.store` (default 7011) by the
adapter's `env()`. The spec's store wins over the cache's.

## Tax

`TAX_RATES` covers the provinces in the adapter file. A province that is not
listed returns **0.0** — a guessed tax is worse than no tax — and the CLI prints a
note when it reports zero. Put the spec's `pricing.province` in and check the
workbook subtitle.

## What the store actually carries

See `stock-availability.md` for the availability traps and
`substitutions-hd.md` for the material translations this store forced. The
headlines: no ground-contact 2x4 exists; bulk packs pay off only at the right
size; price availability is per SKU; and search terms decide everything
(`2x4x8 SPF stud` returns anchor bolts).
````

- [ ] **Step 7: Run the suite and the boundary grep**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
grep -rln "homedepot\|hd_product\|hd_search" skills/ --include=*.py --include=*.md | sort
```

Expected: `Ran 142 tests`, `OK (skipped=9)`. Grep lists **only** files under `skills/homedepot-catalogue/`, plus `skills/building-from-reference/SKILL.md` (deleted in Task 8).

- [ ] **Step 8: Commit**

```bash
cd /Users/eric/pi-config
git add -A skills/homedepot-catalogue skills/woodbuild-engine/scripts/woodbuild/stock.py \
        skills/woodbuild-engine/scripts/tests/test_adapters.py
git commit -m "skills: add homedepot-catalogue and its store adapter"
```

---

### Task 7: Split the orchestrator, framing and nesting skills

**Files:**
- Modify: `skills/building-from-reference/SKILL.md` (full rewrite)
- Create: `skills/wood-framing/SKILL.md`
- Move: `skills/building-from-reference/framing-rules.md` → `skills/wood-framing/framing-rules.md`
- Create: `skills/sheet-and-board-nesting/SKILL.md`

**Interfaces:**
- Consumes: engine paths from Tasks 1-5, the workspace convention from the spec (D6).
- Produces: the three skill names and descriptions other tasks and the README refer to.

- [ ] **Step 1: Move the framing reference**

```bash
cd /Users/eric/pi-config
mkdir -p skills/wood-framing
git mv skills/building-from-reference/framing-rules.md skills/wood-framing/framing-rules.md
```

- [ ] **Step 2: Write `wood-framing/SKILL.md`**

````markdown
---
name: wood-framing
description: Use when deriving wall, roof or floor framing for a stick-built structure — studs, plates, corners, headers, rafters, blocking, panelisation or datums — or when a framing count, header depth or part length needs to be justified.
---

# Wood framing

The rules `woodbuild/frame.py` implements, in `framing-rules.md`. **Change the code
and that file together** — a rule that lives only in prose does not get built.

Read it for: stud layout as `span / n` (not the nominal spacing), three-stud
corners, doubled headers sized at span ÷ 20 rounded up to the next stock depth,
cripples over a head, no sill across a door, blocking at the roof bearing line,
and part ids that carry their wall.

## Running the derivation

```bash
cd <workspace>
python3 ../woodbuild-engine/scripts/woodbuild.py --spec spec.json --prices prices.json \
  --out out            # --adapter ... for live prices; not needed to see framing
```

`frame.derive(spec)` is the entry point the CLI calls. It reads the spec and
nothing else; it never touches prices or nesting.

## What this skill does not decide

- Stock sizes and kerf — the engine's geometry catalogue.
- Whether the parts fit on the sheets and boards — `sheet-and-board-nesting`.
- What the material costs — `build-pricing`.
- The envelope and openings — `building-from-reference`.
````

- [ ] **Step 3: Write `sheet-and-board-nesting/SKILL.md`**

````markdown
---
name: sheet-and-board-nesting
description: Use when laying out sheet goods or dimensional lumber for a cutlist — shelf packing, grain locking, kerf, offcut retention, board choice or yield — or when a nesting result, sheet count or board count looks wrong.
---

# Sheet and board nesting

Turning parts into sheets and boards. The rules the optimiser implements, and what
a sane result looks like.

## Constants and policy

- **Kerf 3.0 mm** between adjacent parts and at board cut ends.
- **Offcuts ≥ 300 mm** are reported as reusable; smaller remainders are waste.
- **Grain-locked parts are never rotated.** They are reported unplaced instead, so
  a face-grained panel can never come out cross-grained.
- Sheet nesting is shelf packing, decreasing height.
- Board choice minimises cost, then waste, then the number of boards, then stock
  length. Waste counts kerfs **actually cut** (`parts − boards`, not `boards − 1`).

## Calling it

```python
from woodbuild import optimise, stock
sheet_parts = [p for p in parts if stock.is_sheet(p.stock)]
board_parts = [p for p in parts if not stock.is_sheet(p.stock)]
sheet_plans, unplaced_sheets = optimise.pack_sheets(sheet_parts)
board_plans, unplaced_boards = optimise.cut_boards(board_parts, prices=prices)
```

Each optimiser rejects a foreign stock class, so **partition first**. `NestError`
means a part cannot be placed at all; unplaced parts are a build failure, not a
warning — report them and stop.

## Hard rule

**No invented quantities.** Sheet counts and board counts come from nesting and
cutting-stock. Area ÷ sheet size is not a quantity.

## What this skill does not decide

- Which stock classes exist and how thick they are — `woodbuild-engine`'s
  `woodbuild/stock.py`.
- Why a part is that size — `wood-framing` and the build's spec.
- What a board costs — `build-pricing`.
````

- [ ] **Step 4: Rewrite `building-from-reference/SKILL.md`**

````markdown
---
name: building-from-reference
description: Use when asked to rebuild an existing structure or product in wood — a shed, bench, cabinet or fence from a photo, drawing, product page or CAD model — producing a build spec, a cutlist, an optimised buy plan and a priced deviations table.
---

# Building from a reference

A reference is not a build. A moulded panel shed, a photo of a bench, or a drawing
of a cabinet contains no studs, plates, headers or fasteners — those must be
derived. Never translate a reference's parts straight into wood, and never price
anything from memory.

This skill orchestrates. Framing rules live in `wood-framing`, nesting in
`sheet-and-board-nesting`, the pricing method in `build-pricing`, the store in
`homedepot-catalogue`, and model ingestion in `freecad-model-to-spec`. The engine
they all use is `woodbuild-engine`.

## Workspace

Ask for a project slug — never guess one — and create:

```
~/Documents/woodbuild/<slug>/
├── spec.json        envelope (the fixed thing), wall/roof/floor build-ups,
│                    openings, substitutions, pricing.store/province/search, options
├── prices.json      the price cache
├── decisions.md     prose: why these invariants are what they are
└── out/             budget.html, cutlist.csv, cart.csv, sku-qty.txt,
                     candidates.json (written by the candidate pass, read by you),
                     price-deltas.txt (only with --compare)
```

The CLI writes everything it produces under `--out`; that is why `candidates.json`
lives there and not beside `spec.json`.

## Workflow

1. **Intake** — get numbers, not impressions: envelope, opening sizes and positions,
   roof pitch, and what each part is made of. A data sheet or an existing CAD model
   beats a photo; if the only source is an image, write down which dimensions you are
   guessing. For a CAD model, hand off to `freecad-model-to-spec`.
2. **Name the invariants** — which dimensions are fixed (usually the exterior
   envelope and the clear door opening) and which give (wall build-up, floor
   structure, roof build-up). State it out loud in `decisions.md`; every later
   conflict resolves against it.
3. **Translate** — for every reference material write the wood equivalent and its
   dimensional consequence, as a row in `spec.json`'s `substitutions`. Anything the
   store does not stock becomes a substitution row. Changing the diagram is expected;
   hiding it is not.
4. **Write the spec** — one `spec.json`. With a CAD model, `from_model` derives the
   envelope and the door and band openings; everything else is locked decisions you
   write down.
5. **Derive and nest** — `wood-framing` and `sheet-and-board-nesting` own those rules.
   Run the engine (below) and read the cutlist.
6. **Verify** — every part placed, no sheet overfilled, sheet count plausible, and
   the door opening still the reference's size. `spec.validate()` refuses a spec whose
   band no longer fits under the roof build-up or whose openings no longer close;
   treat a refusal as the design conflict it is.
7. **Match products, then price** — `build-pricing` for the method,
   `homedepot-catalogue` for the store. Read the deviations table *before* the
   totals, and report anything unpriced with its reason.

## Running the engine

```bash
cd ~/Documents/woodbuild/<slug>
E=../woodbuild-engine/scripts   # absolute: <repo>/skills/woodbuild-engine/scripts
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out --candidates \
  --adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py
```

The engine is stdlib-only; there is nothing to install.

## Hard rules

- **No invented prices, and no auto-accepted ones.** Unmatched stays `unpriced`.
- **No invented quantities.** Quantities come from nesting and cutting-stock.
- **Framing is derived, never copied** — see `wood-framing`.
- **Fixed dimensions stay fixed** unless the person you are building for agrees;
  thicker walls mean a smaller interior, and that must be stated in m²/m³.
- **Consumables come from connections and joints**, not from material length, and
  their coverage assumptions belong in the workbook.
````

- [ ] **Step 5: Verify the skills are well-formed and self-describing**

```bash
cd /Users/eric/pi-config
python3 - <<'PY'
import pathlib, re
for skill in ("building-from-reference", "wood-framing", "sheet-and-board-nesting"):
    text = pathlib.Path("skills", skill, "SKILL.md").read_text()
    name = re.search(r"^name: (.+)$", text, re.M).group(1).strip()
    desc = re.search(r"^description: (.+)$", text, re.M).group(1).strip()
    assert name == skill, (skill, name)
    assert 20 < len(desc) <= 1024, (skill, len(desc))
    print("ok %s (%d chars)" % (name, len(desc)))
PY
grep -rn "Home Depot\|homedepot\|hd_search" skills/building-from-reference/ skills/wood-framing/ skills/sheet-and-board-nesting/ || echo "no store references in these three"
```

Expected: three `ok` lines, then `no store references in these three`.

- [ ] **Step 6: Commit**

```bash
cd /Users/eric/pi-config
git add -A skills/building-from-reference skills/wood-framing skills/sheet-and-board-nesting
git commit -m "skills: split the orchestrator, framing and nesting skills"
```

---

### Task 8: Split pricing, model ingestion and the engine reference; delete the old skill

**Files:**
- Create: `skills/build-pricing/SKILL.md`
- Create: `skills/freecad-model-to-spec/SKILL.md`
- Create: `skills/woodbuild-engine/SKILL.md`
- Delete: `skills/building-from-reference/` (whatever remains)
- Modify: `skills/building-from-reference/SKILL.md` → move generic rules out before deletion

**Interfaces:**
- Consumes: all engine interfaces from Tasks 2-6.
- Produces: the final roster; Task 9's boundary test depends on it.

- [ ] **Step 1: Write `build-pricing/SKILL.md`**

````markdown
---
name: build-pricing
description: Use when pricing a material list — turning stock classes into verified prices with provenance, deciding whether a search hit may become a price, or reporting a line as unpriced. Store-agnostic: it never names a retailer.
---

# Pricing a build

The method. Which shop answers, and how to reach it, is the store adapter's job
(`homedepot-catalogue` is one).

## The rule that matters

**A search hit is never a price.** A script may not convert a description match into
money. Only an agent's judgement, recorded with a reason, prices a class.

```bash
E=<repo>/skills/woodbuild-engine/scripts
cd <workspace>
# 1. what still needs a match, with candidates to read
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out --candidates \
  --adapter <store adapter>
# 2. judge, then record the decision and the reasoning
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out \
  --set-price 2x4 1001802962 --why "2x4x8 ft SPF standard stud" --today 2026-08-01 \
  --adapter <store adapter>
```

`--set-price` re-fetches the SKU through the store's product tool and writes the
name, url, price and your `--why` into the cache. The durable artifact is the
decision **and its justification**, not the SKU.

## Cache

`prices.json`: `store`, `storeName`, `province`, `currency`, `fetched`, `items`,
`unpriced`. Each item carries `sku`, `desc`, `price`, `url`, `source`, `fetched`,
`matched_by`, `matched_on`, `why`, and `pack` when the match recorded one.

- A cache priced for a different store than the spec is a hard error, not a merge.
- A match older than **30 days** must be re-judged, not trusted.
- A `null` price is a real answer: the line stays unpriced with that reason.

## Packs

Consumables are bought in packs. Record the pack size with the match
(`--pack "50 count"`), because a per-pack price may only price a pack, never a count
of pieces. Without a recorded pack the line stays unpriced. For consumables prefer
the **best value pack** — compare price per piece, not the first correct product.

## Reporting

Never invent a price or a pack size. Leave a class unpriced with a reason and report
it; the workbook prints every unpriced line with its reason, and the deviations table
is read before the totals for the same reason: constraints before costs.

## What this skill does not decide

- Tool names, store ids, tax rates, SKU availability — the store adapter.
- What the materials are — `building-from-reference` and `wood-framing`.
````

- [ ] **Step 2: Write `freecad-model-to-spec/SKILL.md`**

````markdown
---
name: freecad-model-to-spec
description: Use when turning a FreeCAD model into a build spec for a wood rebuild — bounding the envelope from the model's own geometry, reading door and band cutters, re-placing an opening for a different build-up, or failing loudly when a model no longer matches its spec.
---

# FreeCAD model to build spec

Ingestion only: a model in, an envelope and openings out. No stores, no prices, no
framing policy. If the model is being *built or repaired* rather than read, that is
`freecad-model-hygiene`; if it needs screenshots, `freecad-render-views`.

`woodbuild-engine`'s `woodbuild/from_model.py` is the engine half. It names no
project: object names,
the model's own roof thickness, the roof fall and the corner width are arguments.

## Workflow

1. **Bound the envelope.** `wall_bounds(doc, wall_object="WallsOpen")` when the model
   has a wall solid, otherwise let the panel and post naming convention supply it:
   `wall_bounds(doc, panel_suffixes=("Cut",), post_prefixes=("Post",))`. An empty
   bound is a spec error, never an empty envelope.
2. **Derive the envelope.** `envelope_from_bounds(bounds, model_roof_t=80.0,
   roof_fall=200.0, tall_side="front")`. The model's wall top *is* its roof
   underside, so the product's overall height is that z plus the **model's own** roof
   thickness. The wood roof build-up is a spec decision and must not enter here —
   mixing the two is how an envelope silently grows.
3. **Read the openings.** `openings_from_cutters(doc, envelope, door_name="fw_door",
   band_name="fw_band", corner_width=..., roof_build_up=...)` reads only what a
   cutter can tell you: the door's clear size and head, and the band's size and sill.
   Transoms, louvres, headers and sills are intent, so they arrive as spec data.
4. **Re-place the band, do not clamp it.** A thicker roof build-up drops the band and
   narrower corners narrow it. If the new sill lands below the door head,
   `band_opening` raises — that is a design conflict for
   `building-from-reference` to resolve, not something to fudge.
5. **Check before trusting.** `check_envelope(spec, doc)` re-bounds the model and
   refuses a mismatch beyond 1 mm, so a moved part cannot quietly invalidate a spec.
6. **Write the spec's openings, not its decisions.** Locked decisions — wall layers,
   roof and floor build-up, store, substitutions — belong to the spec's author.

## Testing without FreeCAD

`bounds_from_shapes`, `envelope_from_bounds` and `band_opening` are pure: they take
numbers and lists, so they are testable with FreeCAD absent. Keep new logic on that
side of the line, and keep the `import FreeCAD` inside the functions that need it.
````

- [ ] **Step 3: Write `woodbuild-engine/SKILL.md`**

````markdown
---
name: woodbuild-engine
description: The stdlib-only woodbuild engine — build spec to cutlist, nesting plan, bill of materials and priced workbook. Use when reading, running or extending the engine, or when another skill points here for its API.
disable-model-invocation: true
---

# woodbuild engine

The shared library behind `building-from-reference`, `wood-framing`,
`sheet-and-board-nesting`, `build-pricing` and `freecad-model-to-spec`. This is a
library that happens to ship as a skill: it is hidden from the model prompt and is
read when another skill points at it, or explicitly with
`/skill:woodbuild-engine`.

**Path coupling:** the other skills reach it as `../woodbuild-engine/scripts/...`.
That holds only while the whole `skills/` tree travels together — same repo, same
package. Do not split the tree across packages.

## Modules

| module | responsibility |
|---|---|
| `stock.py` | stock geometry: sheet sizes, board sections, sale lengths, kerf. No availability |
| `spec.py` | the spec dataclass, derived dimensions, `validate()` |
| `frame.py` | framing derivation (the rules are in `wood-framing`) |
| `optimise.py` | sheet nesting and board cutting-stock |
| `bom.py` | bill of materials and consumable amounts from geometry |
| `pricing.py` | the price cache and the candidate/verify/resolve policy |
| `adapters.py` | `StoreAdapter`, `NullAdapter`, `load_adapter` — the store seam |
| `from_model.py` | FreeCAD document → envelope and openings; the only FreeCAD importer |
| `report.py` | `budget.html`, `cutlist.csv`, `cart.csv`, `sku-qty.txt` |
| `cli.py` | the command line and the pipeline order |

The engine names **no** store, tool, store id or tax rate. Those arrive as a
`StoreAdapter`; with none, prices come from the cache only and tax is 0.0.

## Stock geometry

Moved here from the old `stock-catalogue.md` as that file is deleted: this is the
engine's own vocabulary, not a store's availability (that is
`homedepot-catalogue/stock-availability.md`). Sizes are millimetres; the names are
imperial because that is what a builder asks for at the saw.

| class | size | thick | grain | category |
|---|---|---|---|---|
| `osb_7_16` | 1219 × 2438 | 11 | – | sheets |
| `plywood_tg_18` | 1219 × 2438 | 18 | deck | sheets |
| `plywood_ext_18` | 1219 × 2438 | 18 | face | sheets |
| `smartside_grooved` | 1219 × 2438 | 11 | groove | sheets |
| `polycarbonate_6` | 610 × 1220 | 6 | – | glazing |

| class | section | sale lengths | category |
|---|---|---|---|
| `2x4` | 38 × 89 | 8 / 10 / 12 / 16 ft | lumber |
| `2x6` | 38 × 140 | 8 / 10 / 12 / 16 ft | lumber |
| `2x8` | 38 × 184 | 8 / 10 / 12 / 16 ft | lumber |
| `pt_2x4` | 38 × 89 | 8 / 10 / 12 / 16 ft | lumber |
| `pt_4x4` | 89 × 89 | 8 / 10 / 12 ft | base |

Optimiser constants: **kerf 3.0 mm** between adjacent parts and at board cut ends;
**offcuts ≥ 300 mm** reported as reusable. The rules that use them are in
`sheet-and-board-nesting`.

## Running

```bash
python3 scripts/woodbuild.py --spec <workspace>/spec.json \
  --prices <workspace>/prices.json --out <workspace>/out \
  [--adapter <repo>/skills/homedepot-catalogue/scripts/homedepot_adapter.py] \
  [--candidates | --set-price CLASS SKU --why TEXT | --fetch] \
  [--compare old-prices.json] [--server PATH] [--today YYYY-MM-DD]
```

Pipeline order matters: `frame.derive` → partition sheet/board → `optimise` →
`bom.build_bom` → `report`. Prices are resolved **before** BOM and nesting, because
board choice is cost-aware.

## Tests

```bash
cd <repo>
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests \
  -t skills/woodbuild-engine/scripts
```

`-t` is required: the tests and the package are siblings under `scripts/`, and
without the top-level dir the `woodbuild` import fails.

## Extending

- New stock class: geometry in `stock.py` **and** a category, then a test
  (`test_every_class_has_a_category` catches a miss). Missing geometry or category
  fails at import, not at build time.
- New store: a new adapter file, not an engine change.
- New project: a new spec and workspace, not an engine change.
````

- [ ] **Step 4: Preserve the generic substitution rules, then delete the old skill**

Move the generic half of the old `substitutions.md` into the orchestrator as a
reference file:

```bash
cd /Users/eric/pi-config
mkdir -p skills/building-from-reference
```
Create `skills/building-from-reference/reference/substitutions.md`:

```markdown
# Rules for translating a reference

The store-specific rows live with the store (`homedepot-catalogue/substitutions-hd.md`).
These rules are general and came out of more than one build.

- **A substitution that changes the diagram must say so.** Say it in the row's
  `changes_diagram` and in the deviations table.
- **Preserve what the reference promises.** Usually the exterior envelope and the
  clear opening the machine has to fit through. Decide this *before* deriving
  anything, and hold it exactly while everything else gives.
- **Prefer a product that already exists over making one.** The whole point is to
  trade "buy a finished object" for "buy stock a shop sells".
- **When a material is unavailable, redesign rather than substitute silently.**
  Change the detail so the unavailable material is not needed, and write the
  reasoning into the row.
- **Record every row.** The workbook's deviations table is generated from these, so
  an unrecorded substitution is a lie of omission.
```

Then point at it from the orchestrator by adding to `skills/building-from-reference/SKILL.md`,
after the "Translate" step's paragraph:

```markdown
   The general rules are in `reference/substitutions.md`.
```

Delete what remains of the old skill (each path separately: one missing file must
not silently cancel the whole deletion). Before deleting `stock-catalogue.md`, confirm
its geometry tables now exist in `woodbuild-engine/SKILL.md`'s "Stock geometry"
section (they are the engine's vocabulary) and its optimiser constants exist in
`sheet-and-board-nesting/SKILL.md`:

```bash
cd /Users/eric/pi-config
git rm -q skills/building-from-reference/stock-catalogue.md
git rm -q --ignore-unmatch skills/building-from-reference/substitutions.md
ls -R skills/building-from-reference
```

Expected: `SKILL.md` and `reference/substitutions.md` only.

- [ ] **Step 5: Verify the roster is complete and well-formed**

```bash
cd /Users/eric/pi-config
python3 - <<'PY'
import pathlib, re
want = {"building-from-reference", "wood-framing", "sheet-and-board-nesting",
        "build-pricing", "homedepot-catalogue", "freecad-model-to-spec",
        "woodbuild-engine",
        # pre-existing, unrelated to this split and not to be touched or counted
        "freecad-model-hygiene", "freecad-render-views"}
found = {p.parent.name for p in pathlib.Path("skills").rglob("SKILL.md")}
missing, extra = want - found, found - want
print("found:", sorted(found))
assert not missing, "missing skills: %s" % sorted(missing)
assert not extra, "unexpected skills: %s" % sorted(extra)
for name in sorted(want):
    text = pathlib.Path("skills", name, "SKILL.md").read_text()
    fm = re.search(r"^---\n(.*?)\n---\n", text, re.S).group(1)
    assert re.search(r"^name: %s$" % re.escape(name), fm, re.M), name
    assert re.search(r"^description: .{20,}$", fm, re.M), name
    print("ok", name, "hidden" if "disable-model-invocation: true" in fm else "visible")
PY
grep -rn "homedepot\|hd_search\|hd_product\|MicroPro" skills/ --include=*.py --include=*.md -l | sort
```

Expected: all seven skills `ok`, only `woodbuild-engine` hidden, and the grep lists
only files under `skills/homedepot-catalogue/`.

- [ ] **Step 6: Commit**

```bash
cd /Users/eric/pi-config
git add -A skills/
git commit -m "skills: split pricing, model ingestion and the engine reference; drop the old skill"
```

---

### Task 9: Add the boundary test

**Files:**
- Create: `skills/woodbuild-engine/scripts/tests/test_boundaries.py`

**Interfaces:**
- Consumes: every skill directory from Tasks 6-8; `load_adapter` from Task 2.
- Produces: the guard that keeps the split true. Nothing consumes it.

- [ ] **Step 1: Write the test**

Create `skills/woodbuild-engine/scripts/tests/test_boundaries.py`:

```python
"""The split, enforced. A store name outside homedepot-catalogue is a regression.

These tests are the reason the refactor stays done: prose drifts, and a helpful
sentence about Home Depot in the framing rules would re-couple the two concerns
without anyone noticing.
"""

import pathlib
import re
import unittest

from woodbuild.adapters import load_adapter

SKILLS = pathlib.Path(__file__).resolve().parents[4] / "skills"
# The store's identity, not the skill's directory name: the visible skills must be
# able to point at `homedepot-catalogue/scripts/homedepot_adapter.py`, so the bare
# skill slug is deliberately not a banned token. The store's own names are.
STORE_WORDS = ("Home Depot", "homedepot.ca", "homedepot.com", "hd_search",
               "hd_product", "HD_DEFAULT_STORE", "MicroPro")
STORE_OWNER = "homedepot-catalogue"
# The six visible skills this split owns. Every one of them must name the engine it
# uses. The two pre-existing FreeCAD skills are deliberately absent: they use no
# engine, they are only scanned for store knowledge.
ENGINE_USERS = {"building-from-reference", "wood-framing", "sheet-and-board-nesting",
                "build-pricing", "homedepot-catalogue", "freecad-model-to-spec"}
# The two files whose job is to name the store in order to check the seam. Their
# names are the whole exemption: any other file naming it is a regression.
STORE_NAMING_ALLOWED = {"test_boundaries.py", "test_adapters.py"}


def skill_dirs():
    return sorted(p for p in SKILLS.rglob("SKILL.md"))


class TestStoreKnowledgeIsContained(unittest.TestCase):
    def test_no_other_skill_or_engine_file_names_the_store(self):
        offenders = []
        for path in SKILLS.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md"):
                continue
            if STORE_OWNER in path.parts or path.name in STORE_NAMING_ALLOWED:
                continue
            text = path.read_text(errors="ignore")
            for word in STORE_WORDS:
                if word in text:
                    offenders.append("%s contains %r" % (path, word))
        self.assertEqual(offenders, [], "store knowledge escaped its skill")

    def test_only_the_two_seam_tests_are_exempt(self):
        exempt = sorted(p.name for p in SKILLS.rglob("*") if p.name in STORE_NAMING_ALLOWED)
        self.assertEqual(exempt, ["test_adapters.py", "test_boundaries.py"])

    def test_the_engine_has_no_tax_numbers(self):
        engine = SKILLS / "woodbuild-engine" / "scripts" / "woodbuild"
        offenders = []
        for path in engine.rglob("*.py"):
            text = path.read_text(errors="ignore")
            if "TAX_RATES" in text or "tax_rate_for" in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [], "the engine must not carry a tax table")

    def test_the_store_adapter_is_loadable_and_offline_safe(self):
        path = SKILLS / STORE_OWNER / "scripts" / "homedepot_adapter.py"
        adapter = load_adapter(str(path))
        self.assertFalse(adapter.is_candidate(adapter.source_product))
        self.assertGreater(adapter.tax_rate("ON"), 0.0)


class TestSkillsAreWellFormed(unittest.TestCase):
    def test_every_skill_declares_its_own_name_and_a_usable_description(self):
        for path in skill_dirs():
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                front = re.search(r"^---\n(.*?)\n---\n", text, re.S)
                self.assertIsNotNone(front, "%s has no frontmatter" % path)
                front = front.group(1)
                name = re.search(r"^name: (.+)$", front, re.M)
                desc = re.search(r"^description: (.+)$", front, re.M)
                self.assertIsNotNone(name, "%s has no name" % path)
                self.assertIsNotNone(desc, "%s has no description" % path)
                self.assertEqual(name.group(1).strip(), path.parent.name)
                self.assertGreater(len(desc.group(1).strip()), 20)
                self.assertLessEqual(len(desc.group(1).strip()), 1024)

    def test_only_the_engine_is_hidden(self):
        hidden = set()
        for path in skill_dirs():
            if "disable-model-invocation: true" in path.read_text():
                hidden.add(path.parent.name)
        self.assertEqual(hidden, {"woodbuild-engine"})

    def test_every_skill_this_split_owns_points_at_the_engine(self):
        for name in sorted(ENGINE_USERS):
            path = SKILLS / name / "SKILL.md"
            with self.subTest(skill=name):
                self.assertTrue(path.exists(), "missing skill %s" % name)
                self.assertIn("woodbuild-engine", path.read_text(),
                              "%s does not name the engine it depends on" % path)

    def test_the_unrelated_freecad_skills_are_left_out_of_the_engine_rule(self):
        # They predate this split and use no engine; they are inside the store scan
        # above, and they hold no store tokens.
        for name in ("freecad-model-hygiene", "freecad-render-views"):
            self.assertTrue((SKILLS / name / "SKILL.md").exists())
            self.assertNotIn(name, ENGINE_USERS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)|^(FAIL|ERROR):"
```

Expected: `Ran 150 tests`, `OK (skipped=9)`. Any failure names the file that broke the
split — fix that file, not the test.

- [ ] **Step 3: Commit**

```bash
cd /Users/eric/pi-config
git add skills/woodbuild-engine/scripts/tests/test_boundaries.py
git commit -m "engine: enforce the skill boundaries with a test"
```

---

### Task 10: Update the README and verify the whole thing by hand

**Files:**
- Modify: `README.md:50-63` (the MCP and Skills sections)

**Interfaces:**
- Consumes: the final roster and paths.
- Produces: documentation a human can follow on a fresh machine.

- [ ] **Step 1: Replace the Skills paragraph**

Replace the single "Skills" bullet (`README.md`, the bullet beginning
`- **Skills**: three skills live in \`skills/\``) with:

```markdown
- **Skills**: seven skills live in `skills/` and sync with this repo. Together they
  turn a reference structure (product page, photo, drawing, CAD model) into a
  buildable wood version with a cutlist, an optimised cart and a deviations table.
  They are single-purpose by design, and a test enforces it
  (`tests/test_boundaries.py`: no store name outside `homedepot-catalogue`):
  - `building-from-reference` — orchestration: intake, invariants, translation, spec,
    verification. Owns the workspace convention (`~/Documents/woodbuild/<slug>/`).
  - `wood-framing` — studs, plates, corners, headers, rafters, blocking, panelisation.
  - `sheet-and-board-nesting` — kerf, offcuts, grain locking, sheet and board choice.
  - `build-pricing` — the store-agnostic pricing method: judge, verify, provenance,
    staleness, honest `unpriced`.
  - `homedepot-catalogue` — the only store-specific skill: MCP wiring, store ids,
    provincial tax, availability traps, and the `homedepot_adapter.py` the engine takes.
  - `freecad-model-to-spec` — generic FreeCAD ingestion: envelope from the model,
    door and band cutters, envelope drift checks.
  - `woodbuild-engine` — the stdlib-only engine itself, hidden from the model prompt
    (`disable-model-invocation`), shared by the other six by relative path.
  `freecad-render-views` covers FreeCAD 1.1's view API limits (per-document ActiveView,
  read-only viewPosition, late/stale captures, TechDraw pages breaking the MCP
  screenshot path). `freecad-model-hygiene` covers disjoint-part modelling, the silent
  boolean failures, and the DAG-root overlap audit.
```

Then add, immediately after that bullet:

```markdown
  Engine tests (run from the repo root; the top-level dir matters):

  ```bash
  python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests \
    -t skills/woodbuild-engine/scripts
  ```
```

- [ ] **Step 2: Note the adapter in the MCP bullet**

In the `- **MCP servers**` bullet (`README.md`, the one listing `freecad` and
`homedepot`), append:

```markdown
  `homedepot` is reached by the engine through
  `skills/homedepot-catalogue/scripts/homedepot_adapter.py` (`--adapter`); without it
  the engine prices from the cache only and reports tax as zero.
```

- [ ] **Step 3: Verify the documented command works exactly as written**

```bash
cd /Users/eric/pi-config
python3 -m unittest discover -s skills/woodbuild-engine/scripts/tests -t skills/woodbuild-engine/scripts 2>&1 | grep -E "^(Ran|OK|FAILED)"
```

Expected: `Ran 150 tests`, `OK (skipped=9)`.

- [ ] **Step 4: End-to-end offline run against a fresh workspace**

```bash
cd /tmp && rm -rf wb-check && mkdir wb-check && cd wb-check
cp /Users/eric/pi-config/skills/woodbuild-engine/scripts/tests/woodbuild_spec_fixture.py .
python3 - <<'PY'
import json
import woodbuild_spec_fixture as f
json.dump(f.SPEC, open("spec.json", "w"), indent=2)
PY
python3 /Users/eric/pi-config/skills/woodbuild-engine/scripts/woodbuild.py \
  --spec spec.json --prices prices.json --out out --today 2026-09-13
ls out
```

Expected: exit 0, the four output files listed, and a `note: no province ... tax
reported as 0.0%` line. Then confirm the adapter changes that:

```bash
python3 /Users/eric/pi-config/skills/woodbuild-engine/scripts/woodbuild.py \
  --spec spec.json --prices prices.json --out out --today 2026-09-13 \
  --adapter /Users/eric/pi-config/skills/homedepot-catalogue/scripts/homedepot_adapter.py
grep -o "tax [0-9.]*%" out/budget.html
```

Expected: `tax 13.0%` (the fixture spec declares province ON).

- [ ] **Step 5: Commit**

```bash
cd /Users/eric/pi-config
git add README.md
git commit -m "docs: describe the split skill roster and the correct test command"
```

---

## Self-Review

**Spec coverage**

| spec item | task |
|---|---|
| D1 layout, seven dirs | Tasks 1, 6, 7, 8 |
| D2 engine as hidden skill | Task 8 (`SKILL.md`, `disable-model-invocation`), Task 9 (test) |
| D3 adapter protocol + injected tax | Tasks 2, 3, 4, 6 |
| D4 generic ingestion, project numbers deleted | Task 5 |
| D5 `freecad-model-to-spec` | Task 8 |
| D6 workspace outside the repo | Task 7 (orchestrator), Task 5 (`test_real_build` retarget), Task 10 (end-to-end) |
| D7 ownership table | Tasks 6-8; enforced by Task 9 |
| D8 boundary test | Task 9 |
| Migration steps 1-8 | Tasks 1-10 in order |
| README update | Task 10 |

**Placeholder scan:** no TBD/TODO; every code step carries real code; prose steps carry
the full file content; the two `git mv` steps preserve content rather than retyping it.

**Type consistency:** `adapter` is threaded as a keyword in the same spelling through
`candidates`, `set_price`, `resolve`, `render_html`, `write_report` and `cli_main`;
`source_search`/`source_product`/`candidate_sources`/`default_store`/`server_path`/
`tax_rate`/`env`/`is_candidate` are used identically in Tasks 2, 3, 4, 6 and 9;
`from_model`'s `bounds_from_shapes`/`envelope_from_bounds`/`wall_bounds`/`band_opening`/
`openings_from_cutters`/`check_envelope` are the names Task 8's skill prose uses.
