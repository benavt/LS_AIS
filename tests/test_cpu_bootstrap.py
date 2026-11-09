import importlib.util
from pathlib import Path
import tempfile
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/completion/cpu_bootstrap.py'
spec=importlib.util.spec_from_file_location('bootstrap',p)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class FrozenFiles(unittest.TestCase):
    def test_detects_modified_wheel_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'wheel.whl';p.write_bytes(b'exact')
            row={'bytes':5,'sha256':module.sha(p)}
            module.verify_files(root,{'wheel.whl':row})
            p.write_bytes(b'other')
            with self.assertRaises(ValueError):module.verify_files(root,{'wheel.whl':row})
            with self.assertRaises(ValueError):module.verify_files(root,{'../wheel.whl':row})
    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data').write_bytes(b'x');(root/'alias').symlink_to(root/'data')
            with self.assertRaises(ValueError):
                module.verify_files(root,{'alias':{'bytes':1,'sha256':module.sha(root/'data')}})
if __name__=='__main__':unittest.main()
