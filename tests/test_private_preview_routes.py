"""The private preview serves exported placeholder directories as pages."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ls_private_preview', ROOT / 'scripts/serve_private_atlas.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class PrivatePreviewRoutes(unittest.TestCase):
    def test_registered_atlas_path_and_placeholder_directory(self):
        self.assertEqual(module.private_route('/LS_AIS/'), '/')
        self.assertEqual(module.private_route('/LS_AIS/targets/cdk2-doc1-monomer/'),
                         '/targets/cdk2-doc1-monomer/index.html')
        self.assertEqual(module.private_route('/LS_AIS/targets/cdk2-doc1t-monomer/?cohort=afs3'),
                         '/targets/cdk2-doc1t-monomer/index.html?cohort=afs3')
        self.assertIsNone(module.private_route('/other/targets/cdk2-doc1-monomer/'))


if __name__ == '__main__':
    unittest.main()
