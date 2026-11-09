# Required atlas workflow

Publication is held. The existing 4,006-model bundle is an incomplete private
preview with accepted Primary geometry, not a completed atlas. Its frozen
scientific files, candidate manifest and four-file Zenodo package remain intact.

The authoritative [project-pinned skill](https://github.com/benavt/Structure_Clustering/blob/f3063757460303e1a4a4ba0b3629fe81776c58c4/.agents/skills/structure-atlas-page/SKILL.md)
says: “Default to verified ProteinEBM scores, UMAP KNN and geometry-based HDBSCAN
for each requested residue range.” It also requires HDBSCAN-guided state and
representative selection, documented MCMC outputs, and native Bonsai from each
view's own selection. The installed global copy omitted these defaults; the
previous project specification consequently omitted required density/sampling
work. No narrower scope was requested by the user.

## Coverage

| Required result | Current evidence |
| --- | --- |
| Exact model cohort and full dimer scope | Verified 4,006 native models, both complete 117-residue chains |
| Primary PCA/UMAP/t-SNE and UMAP KNN | Verified saved coordinates and 27 clusters |
| Primary structures, ensembles, TM grid, Bonsai | Verified saved Primary outputs |
| ProteinEBM Model 6 at t=0.10 | Zero accepted values; remote execution prerequisite unresolved |
| Geometry-based HDBSCAN and membership strengths | Missing |
| HDBSCAN representatives, ensembles, medoid TM grid, own native Bonsai | Missing |
| HDBSCAN-guided structural states and membership | Missing |
| MCMC and DISCO selections, diagnostics and exports | Missing |
| Successor browser acceptance for the complete workflow | Missing |

The machine-readable record is [workflow-coverage.json](../config/workflow-coverage.json).
“Verified” applies only to the named saved result; the workflow is incomplete.

## Completion order

1. Reuse exact matching accepted energies or finish the already requested
   full-dimer Model 6 scoring after the required execution containment is
   established. Join by exact model ID, original-coordinate hash and scoring
   identity. Include all six current pilots; their old scoring dependency waits
   for later complete arms and does not provide current score coverage. Keep
   the approved maximum at 6,000 unique models, with pilots counted within their
   1,000-model arms. Do not rescore accepted matches or insert missing energies.
2. After verified score coverage, fit a separately approved geometry-only
   HDBSCAN successor on the same 4,006-model/full-234-residue feature population.
   Reuse the accepted 2D display projections. The existing complex recipe uses
   10D UMAP, seeds 42/7/123, 30 neighbors, min_dist=0, min_cluster_size=15 and
   min_samples=11, with seed-42 leaf labels and EOM/other-seed diagnostics.
   Freeze actual compatible source/runtime/settings before execution; the
   old complex wrapper hardcodes 1,000 rows and is not directly runnable here.
3. Select density representatives and real comparison ensembles, calculate
   that partition's medoid grid, and build native Bonsai from its own selection.
   Preserve unassigned models. Share truly same-scope figures across the two
   view menus; each TM grid must switch to its active partition's medoids.
4. Adapt the documented saved-energy state/subset workflow to this exact
   homodimer. Bind density assignments, original full-cohort priors, fixed-chain
   structural membership, energies, proposal/acceptance rules, seeds and output
   hashes. The existing CASP17 state runner has target/cohort-specific guards
   and a monomer comparison representation. It must not silently collapse the
   dimer into one chain or import a different target's masks and approvals.
   The reusable subset protocol provides four 10,000-proposal chains, 1,000
   burn-in proposals, a preselected chain-0 final panel of 50 distinct models,
   exact subset controls and DISCO50 coverage controls. Unsupported states,
   uncovered models, noise, mixing limitations and actual cardinalities stay
   explicit; no forced state count, duplicate padding or automatic extension.
5. Export a fresh private successor and verify energy colors, both clustering
   views, their own structures/ensembles/Bonsai/TM grids, sampling panels,
   downloads, mobile and CPU rendering. Review that successor before release.

## Current execution boundary

A fresh read-only queue check confirmed AFsample3 job 25423 and BioEmu2 job
25426 remain held; final acceptance 25427 waits on dependencies. It found no
HSPH1 ProteinEBM job. Read-only login cgroup observations do not establish
compute-job containment; they also supplied no writable delegated execution
route. The saved approved scoring plan requires finite task memory/process
caps and zero swap before launch. Do not replace those requirements with a
watchdog or unhold production under the old plan. Resolve a supported route and
freeze any changed execution mechanism in a reviewed successor.

The old approval covers its exact scoring scope, not a newly adapted density
or sampling runner. No new scientific jobs, native alignments, probability
calculations, samplers, coordinate exports or paid calls were performed while
correcting this scope. The missing native inputs and executable adapter must be
verified before an exact execution plan can be presented for approval.
