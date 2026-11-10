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
1,005. ProteinEBM has accepted coverage for all 4,006 models at 16 noise levels
(64,096 energies). HDBSCAN and its 68-medoid grid, aligned ensembles and 402-model
Bonsai are complete. Three supported state pools contain 1,280, 563 and 341 models;
1,822 remain uncovered. MCMC/DISCO completed all six state/prior conditions with
12 panels of 50 models and saved diagnostics.

## Scientific results and publication hold

All required scientific calculations passed acceptance. The saved site remains
a partial preview until the accepted energies, density supplements, state panels
and diagnostics are assembled into a fresh successor and browser-tested.
See [the current results](config/scientific-completion.json),
[the coverage ledger](config/workflow-coverage.json) and
[the execution record](docs/submitted-workflow.md).

The original exact bundle and its accepted Primary results remain preserved.
Public deployment remains blocked pending successor review and final dataset
metadata, license and file checks. Completion of sampling is not a convergence
claim; the full diagnostics must remain visible in the successor.

## Private preview

The original partial atlas passed browser checks for the three projections, native model
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
runtime preparation passed. The complete calculation graph is now submitted,
with exact executable manifests in the [submission ledger](config/mimas-submissions.json).
This repair did not change generation jobs; BioEmu2 production was observed
running separately and remains outside the frozen 4,006-model cohort.

## Approved execution readiness

The repaired readiness job **25458** and locked CPU environment validation job
**25462** passed. The original administrator-dependency conclusion was incorrect:
an existing private user-service delegation enforces memory, process and swap
limits while preserving the Slurm CPU affinity. Global settings and other jobs
were unchanged. The [readiness result](docs/completion-readiness.md) and
[machine-readable status](config/completion-execution-status.json) retain the
successful evidence and diagnosed failed attempts. Both final monitoring logs
passed and both private services were cleaned up. The current 4,006 completion
workflow has now accepted all 4,006 energy grids, the density supplements,
structural states and all six MCMC/DISCO conditions. The latest native/job status
is in the execution ledger. See [the completed scientific workflow](docs/submitted-workflow.md).
Publication remains held.

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
