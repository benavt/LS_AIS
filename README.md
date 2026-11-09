# HSPH1 construct 12757 structure atlas

Independent scientific project for the exact HSPH1 construct 12757 homodimer:
two copies of the supplied 117-residue chain, including its supplied tag.
Organism and UniProt accession are unverified; the user selected this construct
label without adding a database assignment.

The read-only intake verified 4,000 distinct native coordinate hashes: 1,000 each
from AFsample2, AFcluster, SPEACH_AF and OpenDDE. Original native coordinates,
confidence sidecars, failed attempts and generation records remain on their
owning compute host. No generated models are stored in this Git repository.

An additional 1,000 AFsample3 models and 1,000 BioEmu2 samples were requested on
2026-11-09. Their replacement run preparation is tracked separately. The intended
atlas cohort is 6,000 models only after every arm passes scientific acceptance.

## Current delivery status

- Project source and the initial 4,000-model hash roster are prepared.
- Missing-arm recovery and the clustering execution plan require exact approval.
- Clustering, atlas assets, a public Pages deployment and a Zenodo record have
  not been created. There is no dataset DOI yet.

Run `python3 scripts/status.py` for a source-only integrity check. The eventual
site uses the pinned library's shared AIS explorer and saved publication exporter.
`scripts/build_site.py` refuses to build until a real hash-bound publication
manifest and saved input files exist. No installation or CI event starts science.

The compact Zenodo delivery will contain `sequence.fasta`, `README.md`,
`scores.csv`, and `models.tar.gz`, preserving native coordinate bytes and every
verified available scalar score. Production metadata and data licensing will be
reviewed with the completed package. Source and dataset reuse rights are separate.

See `docs/intake.md`, `config/study.json` and `config/target-spec.json`.

