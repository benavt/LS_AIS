# DOC1/CDK2 A/B core reclustering proposal

This is a proposed **alternate geometry view** for the two existing DOC1/CDK2
targets. It does not change the accepted model cohorts, native PDBs, current
full-construct fits, or ProteinEBM scoring construct. No job is authorized by
this document.

## Residue selection

Use the accepted native, one-based chain numbering and the same cut in chains
A and B. Keep chain C (CDK2) complete.

| Target | Remove from geometry fit | Retain for geometry fit | Retained Cα positions | Retained unordered Cα pairs |
| --- | --- | --- | ---: | ---: |
| DOC1R dimer + CDK2 | A1–64, B1–64 | **A65–126, B65–126, C1–298** | 422 | 88,831 |
| DOC1 dimer + CDK2 | A1–59, B1–59 | **A60–115, B60–115, C1–298** | 410 | 83,845 |

These are analysis masks, not cropped or altered native structures. The fit and
display populations remain all 57,463 accepted DOC1R models and all 75,800
accepted DOC1 models. Existing full A/B/C clustering remains the baseline.

## Evidence and boundary uncertainty

The accepted Cα variance maps use every accepted model, and the median-distance
maps use the frozen 5,000-model samples. In DOC1R, the median variance of
A/B-to-C pair distances falls sharply across residues 61–65, while the median
A/B-to-core variance falls from about 86 Å² at residues 56–60 to 15 Å² at
61–65 and 1 Å² at 66–70. The local median Cα `i→i+4` distance approaches
6–8 Å around residue 65. In DOC1, the analogous cross-chain variance drop is
around residues 51–60, and the local `i→i+4` distance reaches about 6 Å at
residue 60. The proposed starts keep the compact C-terminal segments and put
the cut just before their onset.

On the full-cohort variance maps, excluding these N-terminal pairs removes
82.4% of the summed pair-distance variance in DOC1R and 78.7% in DOC1. This
does **not** establish that the removed residues are disordered or irrelevant:
the difference may be genuine conformational biology. The full-construct view
and native coordinates must remain available.

Check the cut against neighboring masks before interpreting clusters:
DOC1R starts at 60, 65, or 70 on both A and B; DOC1 starts at 55, 60, or 65.
The central masks above are the proposed atlas views. Neighboring masks are
sensitivity diagnostics, not additional published views by default.

Evidence sources: accepted map-plan SHA-256
`8f2b26e94195a55327cbd3d5d3d341352019eb5cdebe06f3172c6ad4fe78360d`;
DOC1R median/variance array SHA-256
`2d5bf76f5ed2bb0e7464e31ea0db0d97505b0f54ac69855f87aec3ddf87237ff` /
`619fdec7330b290cffdc7f0c1e91006a940c106c29629e7baa351796321e5d3f`;
DOC1 median/variance array SHA-256
`272369b2ddd75cbf2fec9255a746c589021c2e0be8c29fc7bb4431c29415d471` /
`551a3623e6b20aebdaf8af0ab63466a348c2e07aa18b959f8b5b0ec4af64ea03`.

## Reclustering sequence on Mimas

1. Freeze a new hash-bound plan containing the two accepted roster hashes,
   full-distance-matrix hashes, exact one-based masks, code/dependency hashes,
   random seeds, outputs, and resource limits. Derive masked condensed-pair
   columns from the accepted complete pair matrices. Validate the column map
   against direct Cα distances in selected native PDBs and check every model
   ID/hash. Do not rerun ProteinEBM or regenerate the original geometry.
2. Pilot the proposed masks on the existing fixed 5,000-model samples. Build
   a new signed 4,096-dimensional sketch from **every retained pair exactly
   once**. Measure exact-versus-sketched distances and 15-neighbor recall on
   the same fixed 256-model evaluation subsets used for the full-construct
   pilot. Require mean 15-neighbor recall at least 95% and 95th-percentile
   relative distance error at most 3%; if either fails, revise the projection
   in a separately reviewed plan before a full-cohort fit. Run the neighboring
   masks on this sample to check whether the preferred boundary is stable.
3. Fit all accepted models for each target with the successful core sketch,
   following the existing full-construct protocol: 2-D UMAP plus UMAP KNN,
   and 10-D UMAP plus HDBSCAN leaf and EOM at seeds 42, 7, and 123,
   `n_neighbors=30`, `min_dist=0`, `min_cluster_size=15`, and
   `min_samples=11`. Preserve all unassigned models and membership strengths.
   Keep the same raw-distance metric and no new block weighting so differences
   from the full-construct fit can be attributed to the residue mask.
4. Accept only complete hashed receipts and finished resource logs. Compare
   core versus full clusters by model ID: HDBSCAN assigned/noise fractions,
   cluster counts and sizes, seed agreement, UMAP KNN composition, and
   assignment concordance. Inspect medoids/representative native structures
   before claiming that the core mask improves interpretability. Large changes
   under the neighboring masks should keep the result labeled exploratory.
5. Only after the fit passes review, prepare its own atlas range selector,
   fit/display scope ledger, memberships, UMAP, PCA/t-SNE if retained in the
   target page, mask-specific map crops, representatives/ensembles, TM and
   Bonsai assets, and eventual MCMC/DISCO sampling. Show ProteinEBM scores
   only with the explicit label **full-complex energy** when those accepted
   scores are available; the residue mask does not create a new energy value.
   Review the private view and its exact export hash before any public update.

Pilot resource proposal: two serial 4-core CPU tasks, at most 2 hours and
32 GiB each (16 CPU-core-hours requested); full-cohort fit proposal: two
serial 8-core CPU tasks, at most 36 hours and 256 GiB each (576
CPU-core-hours requested). These are ceilings based on the completed
full-construct workflow, not runtime predictions. Both stages use zero GPUs
and zero paid external calls. The pilot, full fit, and subsequent atlas assets
require their own exact plan hashes and explicit approvals under the
structure-atlas-page workflow. No calculations or Slurm submissions are made
by proposing these masks.
