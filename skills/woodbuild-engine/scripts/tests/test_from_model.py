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
