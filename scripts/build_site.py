"""Export explicitly selected saved atlas assets; never start scientific work."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    manifest = ROOT / 'config/publication.json'
    if not manifest.exists():
        p.error('A reviewed publication manifest with saved scientific assets is required')
    data = json.loads(manifest.read_text())
    if data.get('project') != 'hsph1-structure-atlas' or not data.get('files'):
        p.error('Missing project identity or saved file inventory')
    from structure_clustering.publication import export
    result = export(manifest, args.source, args.output)
    print(json.dumps(dict(files=len(result['files']), scientific_execution=False)))

if __name__ == '__main__':
    main()

