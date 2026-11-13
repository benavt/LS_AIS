# CDK2–DOC1 monomer cohorts

`CDK2_DOC1` and `CDK2_DOC1t` each have a saved AFsample3 atlas cohort and a
joint AFsample2/3 + BioEMU2 cohort. The 4,000-model AFsample2 + BioEMU2 fit is
an accepted precursor to the joint 5,000-model fit; it is not a separate atlas
menu choice. The Model cohort dropdown enables a joint view only when its
verified private export is present.

| Cohort | Models per target | Current evidence |
| --- | ---: | --- |
| Saved AFsample3 | 1,000 | Transferred into LS_AIS from the immutable [AFsample3 publication](https://benavt.github.io/cdk2-doc1-afs3/) at commit `d672ba45d8a7723ac07041f41410b1150a2b33e6`; all transferred assets match the published manifest. ProteinEBM tables also match the accepted local hashes. |
| AFsample2 + BioEMU2 precursor | 4,000 | 3,000 AFsample2 models (1,000 each from multimer weights v1/v2/v3) and 1,000 BioEMU2 frames. Its accepted geometry and sketches feed the joint fit. |
| Joint AFsample2 + AFsample3 + BioEMU2 | 5,000 | The accepted full-construct fit adds the 1,000 saved AFsample3 models to the precursor. UMAP KNN, HDBSCAN leaf/EOM, PCA, t-SNE, median/variance maps, energy-selected representatives, Bonsai, representative TM, state discovery, and MCMC50/DISCO50 are accepted. |

The new cohort must be fit and displayed separately from the transferred AFsample3
cohort, using complete two-chain scopes `A1-298+B1-115` and `A1-298+B1-55`.
The full-length target retains 999 BioEMU2 frames flagged by native physicality;
the truncated target's 1,000 BioEMU2 frames passed that check. Show those labels
in the model browser, downloads and clustering diagnostics. Do not present the
flagged frames as validated native structures.

## Joint 5,000-model successor

The user selected AFsample2/3 + BioEMU2 after the inventory found no verified
1:1 AFsample1 cohort. The joint fit is recorded under Mimas run
`2026-11-13_cdk2-doc1-monomer-joint-full-clustering_001`, exact plan SHA-256
`7b824af271fe9b31e4aa0cba4559e447d2f405a7b53e00096f49980f46b0377c`.
Both targets have 5,000 unique models: 1,000 each from AFsample2 weights v1,
v2, and v3, 1,000 AFsample3, and 1,000 BioEMU2. All 5,000 have accepted
ProteinEBM Model 6 t=0.10 energy. The fit has 2-D/10-D UMAP, UMAP KNN, and
HDBSCAN leaf/EOM labels with seed diagnostics. The full DOC1 leaf view has 51
assigned clusters and 2,696 unassigned models; DOC1t has 59 and 2,070.
DOC1t EOM varies across diagnostic seeds and needs a visible stability note.

The saved AFsample3-only views remain separate. The joint private view uses
its own 5,000-model analyses; it does not relabel 1,000-model supplements.
The joint supplement ledger currently reads:

| Asset | CDK2_DOC1 | CDK2_DOC1t |
| --- | --- | --- |
| Native roster, ProteinEBM, UMAP, KNN/HDBSCAN | Accepted | Accepted |
| Joint PCA/t-SNE and Cα median/variance maps | Accepted, plan `66750dcf…` | Accepted, plan `66750dcf…` |
| Energy-selected representatives and verified native coordinates | Accepted; physicality flags shown | Accepted |
| Native Bonsai | Accepted in `2026-11-13_cdk2-doc1-monomer-joint-energy-bonsai_003`; leaf/EOM/KNN viewer exports and selected coordinates verified | Accepted from the same run; leaf/EOM/KNN viewer exports and selected coordinates verified |
| Representative TM grid | Accepted in `2026-11-13_cdk2-doc1-monomer-joint-representative-tm-grid_001`; 51×51 leaf plus EOM/KNN | Accepted from the same run; 59×59 leaf plus EOM/KNN |
| State discovery, MCMC50/DISCO50 | Accepted; two supported states, four MCMC50/DISCO50 conditions | Accepted; one supported state, two MCMC50/DISCO50 conditions |
| Private atlas view and browser validation | Verified 5,000-model joint view, AFsample3 cohort switch, three clustering views, AFsample2 structure, Bonsai selection, TM map, and downloads | Verified 5,000-model joint view, Bonsai structure, and supplemental maps |

The atlas export must label the full DOC1 BioEMU2 physicality failures and
AFsample2 weight versions, and omit optional 3-D box and residue-pair detail
plots. Sampling panels are exploratory. Their accepted diagnostics report
panel-mean-energy R-hat, bulk ESS, 20 exact controls and inclusion RMSE per
condition; task completion does not establish convergence.

The private `CDK2_DOC1` state-discovery receipt
`54c0f8f9a61850717c9f1314e099d53353f0e7b6c6b7780619fcb047858bada3`
is accepted for the fixed-chain 1:1 complex. The three discovered anchors cover
2,103 of 2,304 **leaf-cluster proxy-weighted models** (91.3%) at TM ≥ 0.70;
that proxy measures anchor-discovery coverage, not full-cohort state membership.
Scoring all 5,000 models against those anchors at the same cutoff assigned
3,068 to supported S1, 881 to supported S2, and 9 to unsupported S3; 1,042
fell below cutoff. With the same anchors, the sensitivity check assigned 4,998
models at TM ≥ 0.60, but only 20 at TM ≥ 0.80, with no supported state at the
stricter cutoff. These are private accepted calculations, not a publication
claim. The accepted `CDK2_DOC1t` receipt
`ee3bf890c7c366e642cf1243043176d62426dcde0c9f8bebefa8510b171e3f73`
finds one supported state containing 4,999 models at TM ≥ 0.70; one model
falls below cutoff. The sensitivity check assigns 5,000 at TM ≥ 0.60 and
3,122 at TM ≥ 0.80. The accepted sampling receipts are
`94b856f313ee0ab974452a7b61fce0e8d52c480c78a1990ec306acd476470c3f`
for `CDK2_DOC1` and
`2409dc8508d5c8f4bb15cf86afbda8b0ed832afdcb033829308d9f2603810d74`
for `CDK2_DOC1t`: 240,000 proposals, 120 exact controls, and 600 saved
coordinate instances across six conditions.

The geometry, projection, UMAP KNN/HDBSCAN, Bonsai, and representative TM
plans were approved and accepted on Mimas. The earlier private bundle has
manifest SHA-256 `06f87aeb65bb7b4c06b120fd7ff4b2cac374394182481815386fe4a0c5d167ba`
and predates accepted DOC1t states and sampling. The complete successor shows
PCA, UMAP and t-SNE, ProteinEBM color and downloads, separate
AFsample2 v1/v2/v3 labels, BioEMU2 physicality labels, per-cluster low-energy
representatives, Cα distance and variance maps, Bonsai, representative TM
similarities, and the approved MCMC/DISCO sampling results. The existing
AFsample3 publication remains an immutable saved source.

## 0865 DockQ metric

DockQ v2.1.4 scored all 9,999 other 1:1 models against
`CDK2_DOC1__afsample3__0865`; the reference has a self-score of 1.0.
The accepted full table has SHA-256
`fc321f809ab9977948bf49a70bd6abfd3334ce3a681ad8ca531293f28be2b62f`.
The comparison uses fixed CDK2/DOC1 chain mapping and native residue numbers.
Full DOC1 uses the 115-residue reference arm; DOC1t uses its corresponding
55-residue reference scope (full DOC1 residues 61–115). Those scores must be
labeled separately. The AFsample3 views expose DockQ as a color metric; the
target downloads include every model, including AFsample2 weights v1/v2/v3
and BioEMU2 physicality labels. The private joint 5,000-model export exposes
the same receipt-backed scores as a color metric, with
separate reference scopes and native-coordinate hashes checked against the
accepted joint rosters.
The accepted 4,000-model precursor remains a
scientific input to the separate joint 5,000-model view; it is not an extra menu entry.

## Complete private review bundle

The privacy-checked static export at
`local/previews/2026-11-13_joint_5000_private_006/site` has export-manifest
SHA-256 `4dd3ee42c62b46f3416270af3d8a3012c1582fc8d794a802b94ebea2a797a487`.
The live private Tailscale preview is available through 12:45 PM ET on
2026-11-13. Browser QA covered both direct target links, all three saved
clustering views, the cohort dropdown, ProteinEBM and DockQ colors, supported
state and MCMC50/DISCO50 controls, representative structure CPU/SVG rendering,
PCA/t-SNE/Bonsai, TM and Cα heatmaps, downloads, responsive layout, and a clean
browser error log. This is a private preview, not a public release.
