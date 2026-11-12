# DOC1/CDK2 standard atlas view completion

The published DOC1/CDK2 pages are preliminary. The accepted 57,463-model
DOC1R and 75,800-model DOC1 cohorts, their full-construct and A/B-core geometry
fits, and full-complex ProteinEBM scores are fixed. This document tracks the
figures and native assets required to make each view follow the established
HSPH1 atlas format. It does not authorize a scientific job or public update.

| Asset | Full construct | A/B core | Required presentation |
| --- | --- | --- | --- |
| UMAP, PCA, t-SNE | Accepted and displayed | Accepted and displayed in the private preview | Projection tabs retain the active target, residue mask, membership, and color. |
| Cα median-distance map | Accepted; 5,000 fixed sampled models | Accepted and displayed in the private preview | Matrix subset of the accepted full-construct map; preserve chain C and the sampled-model disclosure. |
| Cα distance-variance map | Accepted; every accepted model | Accepted and displayed in the private preview | Matrix subset of the accepted full-cohort population variance; preserve Å² units and chain boundaries. |
| Energy-selected cluster representatives and aligned ensembles | Selection accepted; ensembles missing | Selection accepted; ensembles missing | The lowest accepted ProteinEBM Model 6 t=0.10 full-complex score selects each assigned cluster's representative. Label these “energy-selected representatives,” never medoids. |
| Medoid-to-medoid TM similarity heatmap | Deferred for HDBSCAN | Deferred for HDBSCAN | The user asked to skip large HDBSCAN cluster TM grids for now. No full-grid jobs were submitted. Small KNN grids remain a separate later decision. |
| Native Bonsai | Missing | Missing | Each displayed partition has a tree from its own documented, hash-verified selected model IDs and matching geometry mask. |
| MCMC/DISCO panels | Missing | Missing | Follow the separate accepted-scores/state/sampling protocol before claiming a complete atlas. |

The three displayed partitions are HDBSCAN leaf, HDBSCAN EOM, and UMAP KNN.
The four leaf partitions contain 391, 476, 576, and 707 assigned clusters,
respectively. The previously approved exact-medoid method called for
2,992,818,820 unordered RMSD comparisons across all 12 views, mainly because
large EOM and UMAP KNN groups contain up to 20,153 and 46,592 models. The
user replaced this method with ProteinEBM energy selection. The replacement
requires zero RMSD comparisons and yields 3,173 representatives across all
assigned clusters and views. Energy minima need not be geometrically central;
do not label them medoids, reuse a grid under another partition, or silently
omit an offered view. Full-complex energy is reused for the core geometry
views with that scope disclosed.

The frozen pilot plan at
`local/plans/2026-11-11_doc1-cdk2-supplement-pilot_001/plan.json` has SHA-256
`dce4b2783e971b9f3bf8947551ffb8c6ad5d6bbbecbd0799d26806957da9c208`.
It verifies the accepted roster, model-index, and leaf-label bytes; selects the
five largest leaf clusters from each target/range; calculates their exact
all-member fixed-chain Cα medoids on that range; and times 80 directional
three-chain US-align comparisons. The four monitored Mimas tasks run serially,
one CPU and 16 GiB each, with two hours per task (eight CPU-core-hours
maximum), zero GPUs, zero paid external calls, and no public export. The
execution source is `scripts/doc1_cdk2/atlas_supplement_pilot.py` at SHA-256
`4589f78235d63b10d448dcced51d36741196c4338e003d32753e319949b9ed52`.
The user approved this exact plan. Fleet accepted monitored Mimas array `26147`;
all four tasks finished with exit code zero and their finished resource logs
passed. The four pilot receipt SHA-256 values, in DOC1R full/core and DOC1
full/core order, are `d6a64f8f3214d8917149e33236a530acfaf518094e084766751e756fecc8cca1`,
`af9c03be961aead5c90d7118c6eb1f23a8f0d49a6321b2a3145d25f41d1e13eb`,
`af82fc26656fb298a0b9a8ef4e990a22ff698bcb0763bc6fb4df900ff5dbc0d0`,
and `03db727cce227553767791a8bd3c6a95620ff2d14abc9893f6d2ee198400aa9b`.
The mean directional US-align times were 0.393, 0.557, 0.419, and 0.656
seconds, respectively; the slowest of 80 calls took 0.896 seconds. Exact
medoid computation took under one second per five-cluster task, exclusive of
native PDB hash/parse time. These are pilot measurements, not accepted full
matrices or Bonsai trees.

The A/B-core figure plan at
`local/plans/2026-11-11_doc1-cdk2-core-figures_001/plan.json` has SHA-256
`529d51d620cc83646233e871b6d76aabe8a328feae245a64ee9e56c926f8bdd3`.
It refits PCA and t-SNE on the accepted core sketch for all models and slices
the accepted full-construct numeric median/variance matrices to the exact
retained A/B-core+C indices. It preserves the original 5,000-model median
sample and all-model variance. The two serial monitored Mimas tasks are each
capped at eight CPUs, 32 GiB and one hour (16 CPU-core-hours total), with zero
GPUs and paid external calls. The code and ten small accepted input hashes have
been checked; the script also checks the saved core sketch bytes on the worker.
The user approved the exact plan, and Fleet array `26153` finished both tasks
with accepted receipts (`436c489bcbf3350ddb0ae241e539449a95a4965ef6454fbfb6233108d46c059e`
for DOC1R and
`e03b97293161b47e06c533af44f8c4eeadf994dfb9100fbff0295ef6a9f25e89`
for DOC1). The private preview export has manifest SHA-256
`ecfc493e5e0e71dd456bc0f3b334951c183a00bb6f6ea3f41d7e19336ba9c20a`.
Browser checks confirmed the core PCA and t-SNE tabs and loaded median and
variance images for both targets. This private preview has not been published.

The all-partition exact-medoid plan at
`local/plans/2026-11-11_doc1-cdk2-medoids_001/plan.json` has SHA-256
`39a9a7f2afb954535adbfe657b04dfbcb872e112080a3c67f01f621f2f4f045b`.
It first validates each native PDB against its accepted hash and caches full
A/B/C Cα coordinates, then calculates exact all-member, fixed-chain RMSD
medoids separately for leaf, EOM and UMAP KNN on each full/core mask. It
records up to five nearest comparison members and five explicit unassigned
examples per applicable view. There are 2,992,818,820 unordered medoid pair
comparisons across the 12 partitions; this is a bounded exact calculation,
not a sampled representative selection. Two serial coordinate tasks are capped
at one CPU, 16 GiB and two hours each. Twelve medoid tasks run at most four
concurrently, each capped at one CPU, 16 GiB and 12 hours. The total ceiling
is 148 CPU-core-hours, four concurrent CPUs, four GiB of scratch output,
zero GPUs and zero paid external calls. All 25 distinct accepted inputs and
pinned-code files were verified on Mimas. The plan creates private selection
receipts only; separate approvals are required for full TM grids, Bonsai and
public export. The user approved this exact plan. Fleet array `26155` finished
both native-coordinate validation tasks with accepted receipts; medoid array
`26159` produced 11 selection receipts before the user changed the method.
The remaining DOC1R full KNN task `26159_2` was cancelled at 1:08:04 elapsed
and is off the Slurm queue. Preserve the 11 historical results and logs; they
are not the energy-selected representatives. A receipt is not final until its
worker exit, resource log, and selected-model hashes are checked.

The native Bonsai timing pilot at
`local/plans/2026-11-11_doc1-cdk2-bonsai-pilot_001/plan.json` has SHA-256
`ec6465548d374023f18cd2d5432b2707b14164c6586497e114b36711887a07b9`.
The user approved this exact pilot. It uses the accepted DOC1R full-range leaf
selection of 391 exact medoids and five explicit unassigned examples (396
models), the accepted full-range all-pair sketch, and the pinned native Bonsai
engine. Fleet job `26172` reconstructed a native tree but failed in Scout
preprocessing: the P1 engine snapshot named in the plan did not contain
`bonsai_scout_preprocess.py`. This pilot has no accepted result, and its files
remain intact. The corrected retry at
`local/plans/2026-11-11_doc1-cdk2-bonsai-pilot_002/plan.json` has SHA-256
`eddff65fd868791df027e0d691f0f8b5f6bd8b2110f81f648a7e5bc797ac915b`.
It changes the engine root to the complete pinned R0 snapshot, whose Scout
entrypoint and runtime compatibility guard were checked. The same 396 selected
models, geometry and eight-CPU, 64-GiB, one-hour ceiling apply. The staged
source, plan, and Slurm script hashes match on Mimas. The user approved this
exact retry; Fleet job `26173` finished with exit code zero. Its accepted
receipt SHA-256 is
`a2bebb45cce7f4b3c8827410b2f676710a1e7b58e68172a98922f8576144b5d2`,
with 396 selected models, native tree SHA-256
`debbf6a560a5ebbb4fc5e9eab66dc0b6c75edd15069102d86f619f3e2ad4d9f7`,
and three native layouts. The finished Fleet resource log passed (623.227
elapsed seconds, 3,221.33 observed CPU seconds, 432.97 MiB peak sampled RSS).
The Bonsai pilot validates runtime and layout generation for its historical
exact-medoid selection only. Full Bonsai production requires a new plan and
approval tied to energy-selected representative hashes and revised selection
code; the old medoid-based production draft must not be submitted.

The replacement energy-selection plan is frozen at
`local/plans/2026-11-11_doc1-cdk2-energy-representatives_001/plan.json`,
SHA-256 `539144399567a5bf0ee0411375e3b8259fc0fe3c9aaa0598132f3da4f7246369`.
It verifies accepted native rosters, model order, cluster labels, clustering
receipts and full-complex ProteinEBM Model 6 t=0.10 rankings. For each of the
12 full/core leaf/EOM/KNN partitions, it selects the lowest-score assigned
model per cluster, breaking exact ties by model ID, and records up to five
lowest-score members plus five explicitly unassigned examples where present.
The private output is 12 hash-bearing selection files, a 3,173-row CSV and an
acceptance receipt. It uses one local CPU, at most 2 GiB and 10 minutes;
zero GPUs, RMSD pairs, paid calls or public exports. Its source is
`scripts/doc1_cdk2/atlas_energy_representatives.py`. The user approved this
exact plan. The bounded local process completed successfully with acceptance
receipt SHA-256
`725a890c29843c130f7225134d12c99175a0a3fda1d09976a47ae498a903fa39`.
An independent read of the accepted scores and saved label arrays verified
every minimum, its cluster membership and native model hash across all 3,173
selections. The 13 output hashes and CSV row count passed. A synthetic
tie/noise selection check also passed. No RMSD pair was calculated.

After the pilot, freeze separate production plans with measured ceilings for
all offered partitions, native Bonsai selections and layouts, aligned
ensembles, and core map/projection exports. Keep public Pages figures and
metadata compact; the current static site is already near its 1 GB soft
budget. Verify the complete private page, downloads, browser switching, CPU
fallback, mobile layout, and privacy-checked bundle before replacing the
preliminary public release. The 3-D box summary and residue-pair distribution
detail plots remain omitted unless explicitly requested.

The user subsequently deferred the large HDBSCAN medoid-to-medoid TM grids.
The draft all-12-view TM plan under ignored `local/plans/` has not been
submitted or approved. The user also deferred reference-state TM scoring
against three supplied two-chain CDK2/DOC1 models. Their private intake copies
are preserved, but no similarity calculations or atlas color modes were
created. Sequence checks established reference CDK2 A = cohort C and reference
DOC1 B = either cohort A or B; if resumed, the user chose the higher of the
two arm scores for each reference, with both arm scores in the download.

The energy-representative Bonsai successor is frozen at
`local/plans/2026-11-11_doc1-cdk2-energy-bonsai_002/plan.json`, SHA-256
`8af294897bf37685e8410ffc8cd43a5a2f461b9775526ff5152e5185c3742d47`.
It selects exactly one accepted lowest-energy model for every assigned cluster
in all 12 target/range/partition views (3,173 view representatives), up to five
explicit low-energy unassigned examples per applicable view, and one additional
low-energy member for the two-cluster KNN view so native Bonsai has three leaves.
The active full/core 4,096-dimensional sketch provides the tree geometry; no
RMSD or TM grid is calculated. The plan caps fit and JSON export arrays at 204
CPU-core-hours combined, two concurrent tasks, zero GPUs and zero paid calls.
The initial plan and staged run `_001` failed preflight only because it named
the accepted core sketch `all-pair-sketch.f32`; the actual saved filename is
`subset-pair-sketch.f32`. The fresh `_002` run passed Mimas input/source hash
preflight and Fleet monitored submission preview. The user approved the
corrected exact hash, and fit array `26314` was accepted by Fleet. Publication
remains separate from this private scientific run.

The fit array `26314` and dependent export array `26317` both finished with
zero native exit codes. All twelve fit receipts and native Bonsai JSON exports
passed plan, selection, sketch, tree, layout, representative-ID and role
checks. The exports contain 3,173 energy-selected cluster representatives and
41 documented additional leaves (low-energy unassigned examples and the one
small-tree companion). The private combined atlas manifest SHA-256 is
`b33fcce506e7c019e940b3835d2c99acc1f694bc6c12c80f9815be2226f2aacb`.
Browser review confirmed representative structures, Bonsai plots, target and
full/core/leaf/EOM/KNN switching, and ProteinEBM coloring.

The Pages candidate is a lossless transport of that reviewed atlas: all 6,072
saved model PDB/CIF files are gzip-compressed, referenced by the saved views,
and checked against their original bytes and SHA-256 on decompression. No
science was recalculated. The pinned public privacy checker accepted all
6,656 files; the 919,345,330-byte bundle is under GitHub Pages' 1 GB published
site limit. Its manifest SHA-256 is
`12c5dd08d84c8ba13f8cbbbd2d9c64ad7c051b04e153b1a38ac5202108c85063`.
