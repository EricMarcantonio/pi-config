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
    cache.load()                 # a cache handed in cold reads its file first
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
