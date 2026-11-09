# HSPH1 construct 12757 structure atlas

Independent project for the exact HSPH1 construct 12757 homodimer: two copies
of the supplied 117-residue sequence, including its supplied tag. Organism,
UniProt accession and biological oligomeric state remain unverified.

The accepted current snapshot contains 4,006 distinct native coordinate hashes:
1,000 each from AFsample2, AFcluster, SPEACH_AF and OpenDDE, five AFsample3
pilots and one BioEmu2 pilot. Every original model passed sequence and assembly
validation for both complete chains. The pilots count inside their planned
1,000-model arms; the remaining 1,994 models are outside this snapshot.

The private atlas fits all 234 C-alpha positions and all 27,261 pair distances,
with no trimming. Its saved PCA, UMAP and t-SNE projections share 27 validated
UMAP cluster labels. Supplements include exact full-cluster structural medoids,
27 aligned five-member comparison ensembles, a 27-by-27 bidirectional fixed-chain
US-align grid, and a native Bonsai tree with 161 selected models and three layouts.
Cluster sizes describe this generated library, not equilibrium populations.

Native pTM/ipTM are available for 4,005 models, mean pLDDT for 3,000, native
AFsample2 ranking confidence for 1,000 and native OpenDDE/AF3 ranking score for
1,005. ProteinEBM energies are unavailable. The completion plan's CPU readiness and environment stages now pass under
existing user-delegated resource controls. Target scoring remains pending.
The two future production arms remain held outside this completion cohort.
The atlas keeps missing scores empty and identifies energy separately from confidence.

## Incomplete workflow and publication hold

The saved atlas is a partial preview. The required full workflow also includes
accepted ProteinEBM coverage, geometry-based HDBSCAN, its own medoids/ensembles,
TM grid and native Bonsai, and HDBSCAN-guided structural states with MCMC/DISCO
selection and diagnostics. None of those missing outputs is claimed complete.
See [the coverage ledger](config/workflow-coverage.json) and
[the completion requirements](docs/workflow-completeness.md).

The user stopped publication pending these additions. The previous exact bundle
and its accepted Primary results remain preserved. `scripts/build_site.py`
refuses a publication build while coverage is incomplete or the hold is set.

## Private preview

The private atlas passed browser checks for the three projections, native model
inspection, method/confidence colors, aligned ensembles, three Bonsai layouts,
variance figures, desktop/narrow layouts and the CPU/SVG structure renderer.
Native download routes matched original coordinate hashes. The in-app browser's
file-save automation timed out; a saved browser download is not asserted.

The exact static review candidate is recorded in
[config/publication-candidate.json](config/publication-candidate.json) and
[config/current-snapshot.json](config/current-snapshot.json). It has 4,230 files
and 720,247,309 payload bytes. Generated files remain in the ignored scientific
run; this Git repository stores source, settings and hash inventories.

The compact Zenodo candidate is exactly `sequence.fasta`, `README.md`,
`scores.csv` and `models.tar.gz` (4,006 unchanged native structures; about 154 MiB).
Its methods, score definitions and references are in
[docs/dataset-README.md](docs/dataset-README.md). Data licensing is unresolved.
Public GitHub Pages and Zenodo publication are held until the missing workflow
is completed and its successor reviewed. There is no public dataset DOI or Pages
deployment yet.

## Mimas completion plan

The publication cohort remains the current 4,006 models. The
[submission plan](docs/mimas-completion-plan.md) specifies the missing energy,
density and MCMC/DISCO stages, their dependencies and finite resource ceilings.
The [machine-readable plan](config/mimas-completion-plan.json) is the approved
planning snapshot. Its original administrator prerequisite is superseded by the
[verified delegated repair](docs/completion-readiness.md). Readiness and CPU
runtime preparation passed; later-stage adapters and exact execution manifests
remain to be completed. Neither held generation array was released.

## Approved execution readiness

The repaired readiness job **25458** and locked CPU environment validation job
**25462** passed. The original administrator-dependency conclusion was incorrect:
an existing private user-service delegation enforces memory, process and swap
limits while preserving the Slurm CPU affinity. Global settings and other jobs
were unchanged. The [readiness result](docs/completion-readiness.md) and
[machine-readable status](config/completion-execution-status.json) retain the
successful evidence and diagnosed failed attempts. Both final monitoring logs
passed and both private services were cleaned up. No target scoring, density,
sampling or GPU job has been submitted; publication remains held.

## Source and execution

Run `python3 scripts/status.py` for a source-only integrity check. The project
pins Structure_Clustering `f3063757460303e1a4a4ba0b3629fe81776c58c4` and
research-workflows `fc0e961f1581e93c8dd854ac890f9d300d00f6d5`.

`scripts/export_saved_atlas.py` is the thin saved-result adapter for this exact
approved cohort; it does not fit projections, generate scores or submit jobs.
`site/ca_fallback.js` and `site/saved-explorer-compatibility.patch` document its
small presentation additions. Native structures and scientific arrays remain
unchanged. `scripts/build_site.py` still requires a separately reviewed
`config/publication.json`; the candidate does not unlock public deployment.
No installation, Git event or CI event starts scientific work.
