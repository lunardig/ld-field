"""Smoke tests for rev21 candidate enumeration, without claiming global validation."""
import tempfile
import unittest
from pathlib import Path
from src.enumerate_grid import zone_from_index, enumerate_zone, projected_bounds


class TestEnumerateGrid(unittest.TestCase):
    def test_official_zone_number_formula(self):
        self.assertEqual(zone_from_index(0).central_meridian_deg,-176)
        self.assertEqual(zone_from_index(22).central_meridian_deg,0)
        self.assertEqual(zone_from_index(44).central_meridian_deg,176)
        self.assertEqual(zone_from_index(45).hemisphere,'s')
        self.assertEqual(zone_from_index(90).kind,'lps')
        with self.assertRaises(ValueError):zone_from_index(92)

    def test_candidate_bounds(self):
        for i in (0,22,45,67,90,91):
            e0,e1,n0,n1=projected_bounds(zone_from_index(i))
            self.assertLess(e0,e1);self.assertLess(n0,n1)
            self.assertLess(e1-e0,1000);self.assertLess(n1-n0,1000)

    def test_sample_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            a=enumerate_zone(90,directory,tile_limit=2)
            self.assertEqual(a['tile_count'],2)
            self.assertTrue(a['provisional'])
            self.assertFalse(a['exhaustive_zone'])
            self.assertTrue(Path(a['grid_inventory']).exists())
            b=enumerate_zone(90,directory,tile_limit=2)
            self.assertEqual(a['inventory_sha256'],b['inventory_sha256'])
            self.assertEqual(a['whole'],b['whole'])
            self.assertEqual(a['partial'],b['partial'])


if __name__=='__main__':unittest.main()
