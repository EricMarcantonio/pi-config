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
