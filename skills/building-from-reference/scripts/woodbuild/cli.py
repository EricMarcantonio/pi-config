"""woodbuild CLI: build spec in, workbook + CSVs out."""

import argparse
import os
import sys

from . import bom, frame, optimise, pricing, report, stock
from .optimise import NestError
from .spec import BuildSpec, SpecError

HD_SERVER = os.path.expanduser("~/.pi/agent/mcp-servers/mcp_homedepot/dist/index.js")


def cli_main(argv=None):
    ap = argparse.ArgumentParser(prog="woodbuild")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fetch", action="store_true",
                    help="refresh missing/stale prices over MCP stdio")
    ap.add_argument("--candidates", action="store_true",
                    help="write search candidates for every class needing an agent match")
    ap.add_argument("--set-price", nargs=2, metavar=("CLASS", "SKU"),
                    help="verify an agent-chosen SKU over MCP and record the match")
    ap.add_argument("--why", default=None, help="why the agent chose that product")
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
    uses_transport = args.fetch or args.candidates or args.set_price
    transport = None
    if uses_transport and os.path.exists(args.server):
        if args.server.endswith(".py"):
            command, server_args = sys.executable, [args.server]
        else:
            command, server_args = "node", [args.server]
        transport = pricing.StdioMCP(command, server_args,
                                     env=dict(os.environ, HD_DEFAULT_STORE=str(cache.store or "7011")))
    try:
        if args.set_price:
            cls, sku = args.set_price
            if transport is None:
                print("pricing error: --set-price needs the MCP server at %s" % args.server,
                      file=sys.stderr)
                return 2
            try:
                pricing.set_price(cache, cls, sku, args.why or "", transport,
                                  today=args.today)
            except (pricing.PriceError, pricing.PricingTransportError) as exc:
                print("pricing error: %s" % exc, file=sys.stderr)
                return 2
            cache.save()
            entry = cache.get(cls)
            print("agent-matched %s -> %s %s ($%.2f)" %
                  (cls, entry.get("sku"), entry.get("desc") or "", entry.get("price") or 0.0))
            return 0
        if args.candidates:
            if transport is None:
                print("pricing error: --candidates needs the MCP server at %s" % args.server,
                      file=sys.stderr)
                return 2
            pending = pricing.needs_match(spec, cache, today=args.today)
            found = pricing.candidates(spec, transport, classes=pending)
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
        prices = pricing.resolve(spec, cache, transport=transport, refresh=args.fetch,
                                 today=args.today)
    except pricing.PriceError as exc:
        print("pricing error: %s" % exc, file=sys.stderr)
        return 2
    finally:
        if transport:
            transport.close()
    cache.save()

    parts = frame.derive(spec)
    # the two optimisers each reject foreign stock classes, so partition first
    sheet_parts = [p for p in parts if stock.is_sheet(p.stock)]
    board_parts = [p for p in parts if not stock.is_sheet(p.stock)]
    try:
        sheet_plans, unplaced_sheets = optimise.pack_sheets(sheet_parts)
        board_plans, unplaced_boards = optimise.cut_boards(board_parts, prices=prices)
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
    pending = pricing.needs_match(spec, cache, today=args.today)
    print("agent-matched: %d, unmatched: %d" %
          (len(spec.search_terms()) - len(pending), len(pending)))
    matched = sum(1 for l in lines if l.source == "hd_search")
    if matched:
        print("description-matched lines: %d (verify SKUs before ordering)" % matched)
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
