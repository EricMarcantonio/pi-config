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
