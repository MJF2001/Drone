import importlib.util,unittest,tempfile
from pathlib import Path
p=Path(__file__).with_name('verify_acceptance_range_20261017.py')
s=importlib.util.spec_from_file_location('audit_under_test',p);a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class Fixtures(unittest.TestCase):
 def test_warm_sequence_omission_detected(self):
  expected=a.warm_sequence([(0,0),(1,0),(2,0)],[(0,0),(1,0),(2,0)],[],(0,0))
  self.assertTrue(a.valid_warm_sequence(expected,expected,expected));self.assertFalse(a.valid_warm_sequence(expected[:-1],expected,expected))
 def test_warm_duplicate_detected(self):
  self.assertFalse(a.valid_warm_sequence([(1,0),(1,0)],[(1,0),(2,0)],[(1,0),(2,0)]))
 def test_core_prefix_suffix_change_detected(self):
  old=[(0,0),(1,0),(2,0),(3,0),(4,0)];self.assertTrue(a.check_core(old,1,3,[(2,0)],old[:1]+[(1,0),(2,0),(3,0)]+old[4:],[(1,0),(2,0),(3,0)]));self.assertFalse(a.check_core(old,1,3,[(2,0)],[(9,9)],[(1,0),(2,0),(3,0)]))
 def test_duplicate_success_detected(self):self.assertFalse(a.check_unique_success(['a','b','a']));self.assertTrue(a.check_unique_success(['a','b']))
 def test_hash_corruption_detected(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'evidence';f.write_bytes(b'good');h=a.sha(f);self.assertTrue(a.check_hash(f,h));f.write_bytes(b'bad');self.assertFalse(a.check_hash(f,h))
if __name__=='__main__':unittest.main(verbosity=2)
