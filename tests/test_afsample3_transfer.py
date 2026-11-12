"""Safety checks for importing immutable saved atlas assets."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from transfer_afsample3_atlas import replace_text, verified_rows


class SavedTransferSafety(unittest.TestCase):
    def test_selected_scientific_file_must_match_published_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);source = root / 'source';source.mkdir()
            selected = source / 'CDK2_DOC1/primary.json';selected.parent.mkdir()
            selected.write_text('{"models":[1]}')
            renderer = source / 'app.js';renderer.write_text('local renderer')
            rows = [dict(path=p.relative_to(source).as_posix(), bytes=p.stat().st_size,
                         sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                    for p in (selected, renderer)]
            rows[1]['sha256'] = '0' * 64  # Renderer is intentionally not transferred.
            manifest = root / 'published.json';manifest.write_text(json.dumps(dict(files=rows)))
            only_target = lambda name: name.startswith('CDK2_DOC1/')
            self.assertEqual(len(verified_rows(source, manifest, only_target)), 1)
            selected.write_text('{"models":[2]}')
            with self.assertRaisesRegex(ValueError, 'Saved file differs'):
                verified_rows(source, manifest, only_target)

    def test_presentation_update_does_not_mutate_hardlinked_saved_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);saved = root / 'saved.json';staged = root / 'staged.json'
            saved.write_text('{"targets":{}}');os.link(saved, staged)
            replace_text(staged, '{"targets":{"CDK2_DOC1":{}}}')
            self.assertEqual(saved.read_text(), '{"targets":{}}')
            self.assertIn('CDK2_DOC1', staged.read_text())


if __name__ == '__main__':
    unittest.main()
