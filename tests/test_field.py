import unittest
from src.field import *
class TestField(unittest.TestCase):
 def setUp(self):
  self.tiles=[synthetic_tile(22,10,38),synthetic_tile(22,10,39),synthetic_tile(91,19,19),synthetic_tile(91,19,20),synthetic_tile(91,20,19)]
  self.bytes=[t.encode() for t in self.tiles]
  self.levels=make_tree([H('ld.field.tile.v0',b) for b in self.bytes])
 def test_roundtrip(self):
  for t,b in zip(self.tiles,self.bytes):
   self.assertEqual(len(b),8946);self.assertEqual(Tile.decode(b,(t.zone,t.tile_e,t.tile_n)).encode(),b)
 def test_proofs(self):
  root=self.levels[-1][0].hex()
  for i,b in enumerate(self.bytes):
   p=proof(self.levels,i)
   self.assertTrue(verify_proof(b,i,5,p,root))
   corrupt=bytearray(b);corrupt[-1]^=1
   self.assertFalse(verify_proof(bytes(corrupt),i,5,p,root))
   self.assertFalse(verify_proof(b,(i+1)%5,5,p,root))
   self.assertFalse(verify_proof(b,i,5,p[:-1],root))
 def test_bad_tile(self):
  b=bytearray(self.bytes[0]);b[14]=1
  with self.assertRaises(ValueError):Tile.decode(bytes(b))
  with self.assertRaises(ValueError):Tile.decode(self.bytes[0],(91,10,38))
 def test_domain_hash(self):
  self.assertEqual(len(H('abc',b'xyz')),32)
if __name__=='__main__':unittest.main()
