"""Tests for deterministic rev21 raster ingestion primitives and tile packing."""
import math
import unittest
from src.raster_pipeline import round_even, horn_slope, assemble_tile_layers
from src.field import Tile, NODATA


class TestRasterPipeline(unittest.TestCase):
    def test_round_even(self):
        self.assertEqual(round_even(1.5,1),2)
        self.assertEqual(round_even(2.5,1),2)
        self.assertEqual(round_even(3.5,1),4)
        self.assertEqual(round_even(-2.5,1,low=-32767,high=32767),-2)
        with self.assertRaises(OverflowError):
            round_even(65535,1)
        with self.assertRaises(ValueError):
            round_even(float('nan'),1)

    def test_horn_planar_terrain(self):
        # 1 m of eastward rise per 1 m horizontal grid spacing.
        slope=horn_slope([[0,1,2],[0,1,2],[0,1,2]],1,1)
        self.assertAlmostEqual(slope,45,places=9)
        self.assertIsNone(horn_slope([[0,1,2],[0,None,2],[0,1,2]],1,1))
        with self.assertRaises(ValueError):
            horn_slope([[0,1,2]]*3,0,1)

    def test_assembly_no_data_and_masks(self):
        whole=bytearray(79);inside=bytearray(79)
        inside[0]=3;whole[0]=1
        elevation=[100]*625
        sunlight=[.5]*625
        tile=assemble_tile_layers(22,10,38,bytes(whole),bytes(inside),elevation=elevation,sunlight=sunlight)
        binary=tile.encode()
        decoded=Tile.decode(binary,(22,10,38))
        self.assertEqual(len(binary),8946)
        self.assertEqual(decoded.layers[0][0],100)
        self.assertEqual(decoded.layers[3][0],5000)
        self.assertEqual(decoded.layers[3][1],5000)
        self.assertEqual(decoded.layers[3][2],NODATA)
        self.assertEqual(decoded.layers[4][0],NODATA)
        self.assertEqual(decoded.coarse,(NODATA,)*6)

    def test_layer_overflow_does_not_wrap(self):
        inside=bytearray(79);inside[0]=1
        arr=[None]*625;arr[0]=99999
        with self.assertRaises(OverflowError):
            assemble_tile_layers(22,10,38,bytes(79),bytes(inside),slope=arr)


if __name__=='__main__':
    unittest.main()
