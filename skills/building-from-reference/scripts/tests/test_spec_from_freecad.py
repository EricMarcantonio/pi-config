# tests/test_spec_from_freecad.py
import unittest

from woodbuild.spec_from_freecad import (band_opening, envelope_from_bounds_list,
                                         envelope_from_shape_bounds, spec_skeleton)


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

    def test_envelope_from_bounds_list_unions_panels(self):
        # no FreeCAD needed: the wall fallback is two cut panels whose union is
        # the product envelope (2788.92 x 2179.32 x 2258.06 mm)
        bounds = [[0.0, 2788.92, 0.0, 2179.32, 2178.06],
                  [0.0, 2788.92, 0.0, 2179.32, 2100.0]]
        env = envelope_from_bounds_list(bounds, model_roof_t=80.0, roof_fall=200.0)
        self.assertAlmostEqual(env["width"], 2788.92)
        self.assertAlmostEqual(env["depth"], 2179.32)
        self.assertAlmostEqual(env["height_tall"], 2258.06)

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
