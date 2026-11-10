# Current 4,006-model completion workflow

The approved scientific calculation graph has passed. Scientific input hashes,
both full 117-residue chains, methods, settings and sampling seeds remain frozen.
The original partial atlas and failed attempts remain intact.

Checked 2026-11-10T16:48:56.725047-05:00.

| Stage | Job | Verified status |
| --- | --- | --- |
| P2_002 | 25683 | passed |
| E0 | 25685 | passed |
| E1 | 25687 | passed |
| E2 | 25688 | passed |
| E3 | 25689 | passed |
| E4 | 25690 | passed |
| E5 | 25691 | passed |
| R0 | 25885 | passed |
| D0 | 25888 | passed |
| D1 | 25889 | passed |
| D2 | 25890 | passed |
| D3 | 25892 | passed |
| S0 | 25893 | passed |
| S1 | 25894 | passed |
| S2 | 25915 | passed |
| S3 | 25916 | passed |
| X0 | 25924 | passed |

ProteinEBM accepted 4,006 models at 16 noise levels:64,096 energies and 14,998,464
per-residue values. All 41 GPU allocations completed. No repair reran energy
scoring, structural clustering, state discovery or TM calculations.

HDBSCAN produced 68 assigned clusters and 1,386 Unassigned models. Its own
supplements include 68 exact medoids/comparison ensembles, a 68-by68 TM grid and
a 402-model native Bonsai with three layouts. Three supported state pools contain
1,280, 563 and 341 models;1,822 models remain outside those memberships.

Sampling completed all six state/prior conditions. Each has the prespecified
chain 0 final MCMC50 panel and a real DISCO50 panel:12 panels and 600 exported
conformer instances. There are 240,000 total MH proposals and 120 exact controls.
The repaired job reused 40,000 saved proposals and 20 controls, then ran only the
remaining 200,000 proposals with the original seeds. The serializer now composes
ten validated five-member blocks into each single 50-MODEL panel. Both complete
chains, native identities and one global native pose per conformer passed S3.

The original X0 scan interpreted random numeric NPY bytes as text. The packaging
repair validates complete NumPy headers, dtypes and payload sizes, applies the
unchanged shared privacy rules to headers and every string value, and rejects
object/opaque arrays and malformed payloads. All scientific array bytes remain
unchanged. Its fresh delivery directory preserves the failed partial package.

34 source tests passed. All scientific stages passed separate native-return and
finished inner/outer resource checks. X0 delivery status is recorded above;
only a passed own finished check establishes accepted delivery.

Completion does not establish convergence. Panel-mean-energy Rhat spans
1.0037–1.0147 and bulk ESS spans 311.8–457.7. Full group, method,
noise, rank/folded and exact-control diagnostics remain available for review.
There is no automatic chain extension or selection of a different final panel.

The remaining work is selected collection, private successor assembly/browser
review, and the updated four-file Zenodo package with resolved licensing.
GitHub Pages and Zenodo publication remain held. Future generation arms remain
outside this frozen cohort; these repairs did not change those jobs.
