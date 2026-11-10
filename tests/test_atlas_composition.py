"""Cross-target isolation and menu composition tests on tiny saved fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ls_compose', ROOT / 'scripts/build_private_atlas.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class TargetComposition(unittest.TestCase):
    def delivery(self, root, target, extra=None):
        source = root / target / 'source'; source.mkdir(parents=True)
        data = dict(target=target, view_id='primary', models=['model1'], methods=['Method'], clusters=['Cluster1'],
                    projections={key: dict(xy=[[0, 0]]) for key in ['pca', 'umap', 'tsne']},
                    schemes=[dict(values=['Cluster1'])], representatives=[], views=[])
        files = {'index.html': '<!doctype html><title>LS AIS</title>',
                 'atlas.json': json.dumps(dict(targets=[dict(id=target, data=target + '/primary.json')])),
                 target + '/primary.json': json.dumps(data),
                 'target-context.json': json.dumps(dict(schema_version=1, targets={target: dict(title=target)}))}
        files.update(extra or {})
        rows = []
        for name, text in files.items():
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
            rows.append(dict(path=name, bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        (source.parent / 'delivery-manifest.json').write_text(json.dumps(dict(files=rows)))
        return source

    def test_two_targets_keep_independent_data_and_share_one_menu(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local") as temp:
            root = Path(temp); (root / 'local').mkdir()
            sources = {target: self.delivery(root, target) for target in ['First', 'Second']}
            registry = dict(targets=[dict(id=target, name=target + ' display') for target in sources])
            with patch.object(module, 'ROOT', root):
                module.compose(registry, sources, root / 'output/site')
            atlas = json.loads((root / 'output/site/atlas.json').read_text())
            self.assertEqual([t['id'] for t in atlas['targets']], ['First', 'Second'])
            self.assertEqual([t['label'] for t in atlas['targets']], ['First display', 'Second display'])
            context = json.loads((root / 'output/site/target-context.json').read_text())
            self.assertEqual(set(context['targets']), set(sources))
            for target in sources:
                self.assertEqual((sources[target] / target / 'primary.json').read_bytes(),
                                 (root / 'output/site' / target / 'primary.json').read_bytes())

    def test_rejects_cross_target_catalog_and_conflicting_artifacts(self):
        cases = [({'target-context.json': '{"schema_version":1,"targets":{"Other":{}}}'}, 'crosses'),
                 ({'index.html': '<!doctype html><title>Conflicting renderer</title>'}, 'collision')]
        for extra, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory(dir=ROOT / 'local') as temp:
                root = Path(temp); (root / 'local').mkdir()
                sources = dict(First=self.delivery(root, 'First'), Second=self.delivery(root, 'Second', extra))
                registry = dict(targets=[dict(id=target, name=target) for target in sources])
                with patch.object(module, 'ROOT', root), self.assertRaisesRegex(ValueError, message):
                    module.compose(registry, sources, root / 'output/site')
                self.assertFalse((root / 'output/site').exists())

    def test_rejects_unregistered_or_missing_target_before_export(self):
        with self.assertRaisesRegex(ValueError, 'every registered target'):
            module.compose(dict(targets=[dict(id='First')]), {}, Path('unused'))


if __name__ == '__main__':
    unittest.main()
