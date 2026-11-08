"""Revision 21 candidate geometry tests; authoritative LGRS comparison is still required."""
import unittest
from math import atan, degrees, tan, radians
from src.grid import (
    Zone, classify_square, projected_key_to_tile,
    boundary_walk, LPS_FALSE_ORIGIN, _polar_radius_m,
)


class TestGrid(unittest.TestCase):
    def test_key_nesting(self):
        self.assertEqual(projected_key_to_tile(25, 0), (1, 0, 0))
        self.assertEqual(projected_key_to_tile(24, 24), (0, 0, 624))
        self.assertEqual(projected_key_to_tile(-1, -1), (-1, -1, 624))

    def test_ltm_equator_central_meridian(self):
        north = Zone("ltm", "n")
        south = Zone("ltm", "s")
        # North LTM central meridian at 250 km easting, equator at 0.
        self.assertEqual(classify_square(north, 250, 0), (True, True))
        self.assertEqual(classify_square(north, 250, -1), (False, False))
        # South LTM equator is at 2,500 km false northing.
        self.assertEqual(classify_square(south, 250, 2499), (True, True))
        self.assertEqual(classify_square(south, 250, 2500), (False, False))

    def test_ltm_outside_longitude_strip(self):
        north = Zone("ltm", "n")
        self.assertEqual(classify_square(north, 500, 100), (False, False))
        self.assertEqual(classify_square(north, 250, 100), (True, True))

    def test_lps_disc_and_tangent_cells(self):
        polar=Zone("lps","n")
        self.assertEqual(classify_square(polar, 500, 500), (True, True))
        self.assertEqual(classify_square(polar, 0, 0), (False, False))
        # 1 km square crossing theoretical circular boundary.
        radius=_polar_radius_m()
        e=int((LPS_FALSE_ORIGIN+radius)/1000)
        whole,inzone=classify_square(polar,e,500)
        self.assertFalse(whole)
        self.assertTrue(inzone)
        self.assertEqual(classify_square(polar,e+2,500),(False,False))

    def test_reference_grid_sample(self):
        for hemisphere in ("n","s"):
            zone=Zone("ltm",hemisphere)
            n_center=100 if hemisphere=="n" else 2400
            for e in (50,150,220,250,270,350,450):
                for n in (n_center-1,n_center,n_center+1):
                    self.assertEqual(
                        classify_square(zone,e,n),
                        boundary_walk(zone,e,n,step_m=10),
                        (zone,e,n),
                    )
        for e in (190,195,200,500,800,805,810):
            for n in (190,500,810):
                zone=Zone("lps","n")
                self.assertEqual(
                    classify_square(zone,e,n),
                    boundary_walk(zone,e,n,step_m=10),
                    (zone,e,n),
                )


if __name__=="__main__":
    unittest.main()
