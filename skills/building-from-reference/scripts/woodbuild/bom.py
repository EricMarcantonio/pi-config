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
