# Mimas plan for the complete current HSPH1 atlas

Complete the full atlas workflow for **4,006 currently accepted models** of
HSPH1 construct 12757, with both complete 117-residue chains and the supplied tag.
The user selected this publication cohort on November 9, 2026. The remaining
1,994 queued models do not delay it. Their jobs and the existing partial atlas
remain intact. No jobs were submitted while preparing this plan.

This is a reviewable submission design, **not an executable approval manifest**.
Its [machine-readable specification](../config/mimas-completion-plan.json) binds
the cohort, proposed scientific settings, dependency graph and resource ceilings.
Private native-input and saved-artifact inventories bind original paths and
hashes. Exact new worker commits, platform-specific environment locks, batch
bodies and successful containment evidence must be added before submission.

## Admission comes first

The read-only Mimas audit found the two HSPH1 production arrays still held,
final acceptance dependency-blocked, and no HSPH1 ProteinEBM job. Slurm reports
`SelectTypeParameters=CR_CORE`, unlimited default/max node memory, and disabled
accounting. These configuration observations alone do not certify allocation
limits; the previous HSPH1 pilot evidence also failed the required containment.
The audit observed other active CPU/GPU jobs, so no free-device or calendar ETA
is assumed.

A cluster administrator must supply or verify supported job/step memory and
process enforcement. This plan does not change Slurm, global cgroups, node
state, other projects or held jobs. P0 is a single monitored allocation canary:
read the **actual execution-node** cgroup hierarchy and allocated CPU set,
require a finite effective memory cap within its request, finite descendant
limit at most 64 and zero swap. It exits before scientific work on any failure.
No host-wide process limit or watchdog substitutes for enforcement. A controlled
failure test may run only inside an independently bounded, supported delegated
child; otherwise require administrator evidence, never stress the node.

The existing ProteinEBM interpreter lacks scikit-learn, UMAP and Numba. P1
therefore provisions a separate project-local CPU analysis environment from a
resolved hash lock, starting with the accepted Pax version constraints in the
JSON plan. It stages the exact library, density helper, Bonsai and USalign.
Do not mutate the working ProteinEBM environment or run Bonsai's dependency
installer. Do not install packages until the exact bootstrap is reviewed and
approved. Installer caches and temporary files stay inside the bounded new run.
CPU imports and synthetic source fixtures must pass before science.

## Job graph and finite requests

All jobs use one node and one Slurm task. Arrays have `%1` concurrency, and
whole-array `afterok` barriers serialize the phases. The project has at most
one GPU, eight CPU cores, 64 GiB host RAM and 64 processes/threads under its
active task cgroup. Numeric libraries use one thread per worker; HDBSCAN may
use its allocated eight workers, and native TM work has at most four local
workers. Slurm owns placement; do not reserve resources by changing other jobs.

Every row uses the pinned whole-job monitor. Wall limits include setup,
workload, validation and cleanup; they are ceilings, not duration predictions.

| ID | After successful | Tasks / array | CPU/task | RAM GiB | GPU/task | Wall/task | Work |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| P0 | containment prerequisite | 1 | 1 | 2 | 0 | 10 min | Monitored allocation canary:verify actual memory,pids,swap and cpuset;require administrative containment prerequisite first |
| P1 | P0 | 1 | 2 | 16 | 0 | 60 min | Create separate locked CPU analysis environment;stage pinned library,native density code,Bonsai and USalign;run source/fixture checks |
| P2 | P1 | 1 | 2 | 16 | 0 | 45 min | Bind all4006 native hashes and producer acceptance;stage only verified saved features/projections/Primary artifacts;freeze portable input manifest |
| E0 | P2 | 5 (`0-4%1`) | 2 | 16 | 0 | 45 min | CPU preparation per scoring group;strict native checkpoint load;complete chain-aware cache and lossless roundtrip |
| E1 | E0 | 5 (`0-4%1`) | 4 | 64 | 1 | 10 min | Counted GPU pilot per group:100 each original arm and exact six current pilots |
| E2 | E1 | 5 (`0-4%1`) | 1 | 4 | 0 | 10 min | Accept each counted pilot,finite total/per-residue energies,two-chain invariance and finished producer telemetry |
| E3 | E2 | 36 (`0-35%1`) | 4 | 64 | 1 | 10 min | Fresh native GPU process for each remaining100-model chunk;four original methods times nine chunks |
| E4 | E3 | 5 (`0-4%1`) | 2 | 8 | 0 | 20 min | Accept complete group grids and exact identities,CPU/GPU/native receipts;final six-pilot group reuses its accepted E1 result |
| E5 | E4 | 1 | 2 | 8 | 0 | 20 min | Join exact4006x16 energy grid;verify E4 finalizer logs;rank full construct;issue score-coverage acceptance |
| D0 | E5 | 1 | 8 | 32 | 0 | 240 min | Three fresh10D geometry UMAP fits and six HDBSCAN extractions;seed42 leaf partition;save strengths/noise and diagnostics |
| D1 | D0 | 1 | 8 | 32 | 0 | 720 min | Exact fixed-chain full-cluster density medoids;up-to-five confidence-ranked aligned ensembles;freeze own tree selection and partition hashes |
| D2 | D1 | 1 | 4 | 8 | 0 | 480 min | Density medoid TM heatmap and CSV with existing validated fixed-chain multimer protocol;no remote helper or offload |
| D3 | D2 | 1 | 8 | 32 | 0 | 240 min | One native density-selection Bonsai tree,all nonzero centered PCA axes,no whitening,kNN10,seed42,three layouts |
| S0 | D3 | 1 | 2 | 8 | 0 | 10 min | Counted full-dimer positional-TM protocol verification;at most12 directional native calls;both chains234 positions required |
| S1 | S0 | 1 | 4 | 16 | 0 | 720 min | New positional complex candidate grid,geometry-only state discovery and all4006-member state scores;maximum three states |
| S2 | S1 | 1 | 2 | 8 | 0 | 60 min | Saved-energy MCMC50 and DISCO50 for Primary and HDBSCAN priors;exact controls,diagnostics and selected aligned native-coordinate exports |
| S3 | S2 | 1 | 2 | 8 | 0 | 30 min | Scientific/hash acceptance for all required views and sampling;verify finalizer finished telemetry separately in X0 |
| X0 | S3 | 1 | 2 | 8 | 0 | 30 min | Delivery-manifest and privacy/capacity audit;allowlist selected accepted results for verified collection to Pax |

This is **18 scheduler submissions and 69 tasks: 28 CPU tasks and 41 GPU tasks**.
GPU requests total at most **410 GPU-minutes (6 hours 50 minutes)**. The complete
request envelope totals 287.7 core-hours if every task consumes its full
wall allowance. These are conservative request ceilings; actual runtimes must
be measured. Paid external API calls and API spend are zero. No monetary rate
for Mimas allocation time has been established.

## Frozen scientific scope

### ProteinEBM first: all current models, including six pilots

Use native Model 6 expert source `2abfc58571e6528edf0919daf37a6c74bcf77f67`,
checkpoint SHA-256 `2d3045666c89766f94bf8a6265d64b7086cea9540c8dd5f51230a9ed806abb91`
and expert configuration SHA-256
`de1d1119ff1b793d14a1e235eeeb4f5f74dedbac052a08b937f99b4cbb8584ca`.
Preserve chain identity, native per-chain indices, complete sequences and
unchanged original coordinates. Use 16 native time levels from 0 to 0.15,
primary index 10 at t=0.10, seed 215600, batch size 16, chunks of 100, clean
template self-conditioning, no inference self-conditioning, masking, ensemble
replication or score normalization. No CPU inference fallback.

Prepare five separate groups: the four original 1,000-model methods, and one
exact six-model group containing five accepted AFsample3 plus one BioEmu2 pilot.
The four original group orders and augmentation scopes remain fixed. The
six-model group has no padding and no dependency on future generation. The
existing worker's 1,000-model assumptions must be generalized and tested.

E1 counts the first 100 models of each original group plus all six current
pilots. E3 scores only the remaining 3,600 models. Pilot results are reused in
acceptance. This yields exactly **64,096 total energies**, **14,998,464 per-residue
energies**, and at most **4,496 native GPU batch calls**, with zero duplicate
model evaluations. Join by model ID, original-coordinate hash, checkpoint,
configuration and settings identity. Preserve missing confidence values;
energies are separately labeled learned units, not binding energies.

### HDBSCAN and its own supplements

After E5 verifies complete score coverage, use the same saved 27,261 full-dimer
C-alpha distance features. Exclude energies from the geometry fit. Fit 10D UMAP
at seeds 42, 7 and 123, 30 neighbors and min_dist 0. Extract leaf and EOM
HDBSCAN at each seed, min_cluster_size 15 and min_samples 11. Publish seed-42
leaf labels; keep other results as diagnostics. Preserve all unassigned points
and membership strengths. The three existing 2D display projections and the
27-cluster Primary partition are not refit.

Calculate exact full-cluster fixed-chain C-alpha RMSD medoids with deterministic
ID ties. Align up to five real members per assigned cluster under the existing
common native confidence policy; keep medoids independently. Freeze this
partition's own membership and selection hashes. Create its own medoid TM grid
using the accepted nonfast fixed-chain multimer protocol, and one native Bonsai
tree over the union of its medoids and comparison members. Include up to five
lowest-energy unassigned examples as explicitly unassigned tree leaves, without
inventing a noise cluster. Bonsai uses full 234-residue geometry, all nonzero
centered PCA axes, no whitening, kNN 10, seed 42 and all three native layouts.
The saved Primary tree and grid remain unchanged.

Actual density cluster count K must be reported; min_cluster_size 15 gives
K <= 267. Do not tune settings to obtain a desired count. At most 1,607 unique
Bonsai leaves are selected, including unassigned examples. If a valid selection
or tree is impossible, record the observed reason and stop the release-readiness
check rather than fabricating an output.

### HDBSCAN-guided states and MCMC/DISCO

Use geometry-independent energy-free anchor discovery from the exact union of
Primary and HDBSCAN medoids. State comparisons use the native complex
positional option **`-TMscore 2`**, which matches both chain ID and residue ID,
with canonical A/B chains, all 234 C-alpha positions, one whole-complex pose,
`-mol prot -ter 1 -a T`, nonfast execution and the mean of both directions.
The pinned executable's help documents this mode. S0 must verify full chain and
residue correspondence, self comparison and rigid-transform behavior before
state production. This is a reviewed homodimer adaptation of the reusable
sampler, not direct execution of the CASP17 monomer wrapper. Its score cache
is separate from the multimer-search medoid grid; old grid cells cannot be
substituted as positional membership evidence.

Propose the documented default TM cutoff 0.70, an operational neighborhood
rule. Greedy coverage uses original Primary cluster populations and stops at
90% proxy coverage or three anchors. Assign each model to its highest qualifying
anchor with fixed tie rules. Require 50 members for a supported state. Retain
uncovered and unsupported models; do not force three states. Report fixed-anchor
0.60 and 0.80 membership sensitivities without new native calls or rediscovery.

For both the Primary and HDBSCAN fine priors, use accepted full-dimer Model 6
energies, alpha 0.5 and tau equal to one full-cohort energy IQR. Preserve the
original full-cohort HDBSCAN noise mass and condition the saved prior on a state.
Do not recompute group sizes inside each state. Use the pinned product-weight
law for 50 distinct model IDs, four 10,000-proposal chains, 1,000 burn-in
proposals, the complete Hastings ratio and the preselected chain-0 final panel.
Freeze PCG64 streams from seed 202611090 before any sampling.

For at most six supported state/prior conditions, save up to 240,000 MH
proposals, 120 exact subset control panels, six MCMC50 production panels and
six state-complete DISCO50 controls. Export at most 12 aligned full-dimer
multi-MODEL ensembles (600 coordinate instances). Preserve native originals.
Save replayable swaps/rejections, acceptance rates, energy/cluster/method/noise
count traces, Rhat/ESS where defined and comparisons with exact inclusion
marginals. Exactly-50 pools are deterministic and diagnostic limitations remain
explicit. Poor mixing does not trigger an automatic extension. These selections
are designed coverage panels, not inferred thermodynamic populations.

## Native calculation and storage ceilings

The conservative new native limits are:

- 8,022,015 unique unordered fixed-chain RMSD pairs for exact density medoids.
  The native tiled implementation evaluates both directions and diagonal cells,
  so its computational ceiling is 16,048,036 ordered matrix cells; it never
  allocates the full pair-by-residue workspace.
- 71,022 directional USalign calls for the density medoid grid at K=267.
- 86,142 directional positional-TM calls for at most 294 candidate anchors.
- 24,036 directional member/anchor calls and 12 protocol-test calls.
- **181,212 new directional USalign calls total**, three new inference UMAP fits,
  six HDBSCAN extractions, one new native Bonsai fit, and zero display-projection
  refits or new folding calls.

Actual counts must be emitted before each dependent native stage and may be
lower through exact same-protocol caching. Never exceed the bounds, retry
uncertain calls automatically or reuse mismatched protocols. Run paths and
outputs are new and immutable. Plan storage is at most 30 GiB added on Mimas:
8 GiB environment, 2 GiB selected input staging and 20 GiB scientific/delivery
outputs. Require quota and storage preflight with 50 GiB free reserve. The saved
input inventory selects 4,022 metadata/feature files totaling 242,161,620 bytes;
original native coordinates already remain on Mimas. No bulk retirement,
whole-folder synchronization or source cleanup is part of this plan.

## Submission and acceptance procedure

1. Complete containment and source/runtime prerequisites. Commit the tested
   variable-size scoring, density and fixed-chain state adapters. Bind every
   worker/native dependency, environment/build artifact, monitor/checker,
   original model, cached feature, mask, projection and batch body by SHA-256.
   Keep machine paths and account bindings in ignored private metadata.
2. Materialize concrete immutable stage plans. Later-stage input hashes come
   from accepted, hash-bound predecessor outputs through the approved deterministic
   adapter; no new cohort, source, mask or settings may enter silently. Obtain
   explicit approval of that exact executable plan, its resource envelope and
   scientific exports. This planning document is not submission authorization.
3. Run Bash syntax and the real project/Fleet preview for each concrete job.
   Submit through the monitored front door, CPU or GPU analysis as appropriate,
   with `afterok` barriers and `--kill-on-invalid-dep=yes`. No raw sbatch, srun,
   remote worker, unbounded process pool or hidden install fallback. Register
   one exclusive intent and retain stored scheduler-script verification.
4. Check every active array task's fresh whole-job resource log using the
   isolated pinned checker; verify finished logs, native return codes and
   scientific artifacts separately. Each downstream gate verifies its producers,
   including previous finalizers. Check X0's own final telemetry externally
   before collection. On failure preserve outputs and stop; on ambiguous
   submission reconcile receipts and queue before taking any action.

## Complete private successor, then publication

Collect only allowlisted accepted results to a fresh ignored successor on Pax.
Build from saved outputs under a two-CPU/four-GiB/two-hour envelope, with at most
2 GiB added local disk and a 50 GiB reserve. Serve a fresh private preview for
up to two hours; the earlier preview's availability does not carry over.

Both clustering selectors must expose verified energy colors, their own real
structures/ensembles, medoid grids and native Bonsai. The same-scoped figure
choices must work in both. State controls must load the actual MCMC/DISCO panels
and retain noise, uncovered models, count/selection scope and diagnostic limits.
Verify all 4,006 plotted identities, native/gzip download hashes, desktop/mobile
layouts, CPU rendering, browser errors and privacy. Use supported shared gzip
transport for new derived panels and link medoids to existing native files;
target a site under 900 MiB, checking the actual hosting limit before deployment.

Create a fresh four-file Zenodo package. Reuse the exact 4,006-model native archive
and FASTA; update scores and the scholarly README with verified results. Resolve
the data license and verify the exact final files and metadata. Review the
complete successor bundle before GitHub Pages deployment and Zenodo publication.
No reserved draft DOI is a published record. The publication hold stays in place
throughout this planning and scientific-execution preparation.

The governing [pinned atlas skill](https://github.com/benavt/Structure_Clustering/blob/f3063757460303e1a4a4ba0b3629fe81776c58c4/.agents/skills/structure-atlas-page/SKILL.md)
requires score coverage before new clustering/sampling and exact-plan approval
before scientific execution or exports. Follow the project branch policy and
pinned shared execution contract; neither a source PR nor a successful preview
starts jobs or authorizes a public release.
