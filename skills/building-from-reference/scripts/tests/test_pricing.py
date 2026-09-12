import json
import os
import tempfile
import unittest

from woodbuild.pricing import (PriceCache, PriceError, PricingTransportError,
                               StdioMCP, compare, resolve)
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

    def test_refresh_only_touches_missing_or_stale_classes(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "7011", "province": "ON", "items": {
            "2x4": {"sku": "1", "price": 4.19, "fetched": "2026-09-11"},      # fresh
            "2x6": {"sku": "2", "price": 9.99, "fetched": "2026-01-01"}}}    # stale
        spec = make_spec({"2x4": "2x4x8 SPF stud", "2x6": "2x6x8 SPF"})
        transport = FakeTransport({"2x4x8 SPF stud": SEARCH_HIT,
                                   "2x6x8 SPF": SEARCH_HIT})
        resolve(spec, cache, transport=transport, refresh=True, today="2026-09-12")
        self.assertEqual([c[1]["query"] for c in transport.calls], ["2x6x8 SPF"])

    def test_transport_error_marks_unpriced_with_its_own_reason(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "7011", "province": "ON", "items": {}}
        spec = make_spec({"2x4": "2x4x8 SPF stud"})

        class Exploding:
            def call(self, tool, arguments):
                raise PricingTransportError("server died")

        prices = resolve(spec, cache, transport=Exploding(), refresh=True,
                         today="2026-09-12")
        self.assertNotIn("2x4", prices)
        self.assertIn("server died", cache.data["unpriced"]["2x4"]["reason"])

    def test_cache_for_another_store_is_a_hard_error(self):
        cache = PriceCache(tmp_path())
        cache.data = {"store": "7001", "province": "ON", "items": {}}
        spec = make_spec({"2x4": "2x4x8 SPF stud"})
        with self.assertRaises(PriceError):
            resolve(spec, cache, transport=None)

    def test_tax_rate_lookup(self):
        from woodbuild.pricing import tax_rate_for
        self.assertEqual(tax_rate_for("ON"), 0.13)
        self.assertEqual(tax_rate_for("AB"), 0.05)


class TestStdioMCP(unittest.TestCase):
    """Drives a real stub server over stdio: the transport is not mocked."""

    STUB = '''
import json, sys

def send(obj):
    sys.stdout.write(json.dumps(obj) + "\\n")
    sys.stdout.flush()

for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("method") == "initialize":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"serverInfo": {"name": "stub"}}})
    elif msg.get("method") == "tools/call":
        # noise first: a notification must not be mistaken for the reply
        send({"jsonrpc": "2.0", "method": "notifications/message", "params": {}})
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [
            {"type": "text", "text": json.dumps({
                "products": [{"sku": "1000123456", "name": "2x4x8 SPF Stud",
                              "price": 2.5, "inStockOnline": True}]})}]}})
'''

    def test_handshake_and_id_matched_call(self):
        import os
        import sys
        import tempfile
        fd, path = tempfile.mkstemp(suffix="-stub-mcp.py")
        with os.fdopen(fd, "w") as fh:
            fh.write(self.STUB)
        client = StdioMCP(sys.executable, [path])
        try:
            payload = client.call("hd_search", {"query": "2x4x8 SPF stud"})
        finally:
            client.close()
            os.unlink(path)
        self.assertEqual(payload["products"][0]["sku"], "1000123456")
        self.assertEqual(payload["products"][0]["price"], 2.5)


if __name__ == "__main__":
    unittest.main()
