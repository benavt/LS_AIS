# CDK2–DOC1 monomer cohorts

`CDK2_DOC1` and `CDK2_DOC1t` each have two distinct atlas cohorts. The saved
AFsample3 cohort is transferred into the LS_AIS explorer. The second cohort
appears as a disabled, clearly labeled choice in each target's Model cohort
dropdown until its own analyses pass.

| Cohort | Models per target | Current evidence |
| --- | ---: | --- |
| Saved AFsample3 | 1,000 | Transferred into LS_AIS from the immutable [AFsample3 publication](https://benavt.github.io/cdk2-doc1-afs3/) at commit `d672ba45d8a7723ac07041f41410b1150a2b33e6`; all transferred assets match the published manifest. ProteinEBM tables also match the accepted local hashes. |
| New AFsample2 + BioEMU2 | 4,000 | 3,000 AFsample2 models (1,000 each from multimer weights v1/v2/v3) and 1,000 BioEMU2 frames. All 8,000 missing ProteinEBM scores across both targets are submitted on Mimas. Clustering is not yet calculated or displayed. |

The new cohort must be fit and displayed separately from the transferred AFsample3
cohort, using complete two-chain scopes `A1-298+B1-115` and `A1-298+B1-55`.
The full-length target retains 999 BioEMU2 frames flagged by native physicality;
the truncated target's 1,000 BioEMU2 frames passed that check. Show those labels
in the model browser, downloads and clustering diagnostics. Do not present the
flagged frames as validated native structures.

After accepted scoring outputs are hash-inventoried, freeze the new cohort's
geometry, projection and UMAP KNN/HDBSCAN plan under the pinned
`structure-atlas-page` contract and obtain its exact-plan approval. Add the
resulting views only after assignments, representative structures, diagnostics,
and required atlas supplements pass their own acceptance checks. The successor
delivery must show PCA, UMAP and t-SNE, ProteinEBM color and downloads, separate
AFsample2 v1/v2/v3 labels, BioEMU2 physicality labels, per-cluster low-energy
representatives, Cα distance and variance maps, Bonsai, representative TM
similarities, and the approved MCMC/DISCO sampling results. Record each item as
accepted or missing in the target/view ledger; a placeholder cannot imply it
has been calculated. The existing AFsample3 publication remains an immutable
saved source.

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
and BioEMU2 physicality labels. The pending 4,000-model cohort remains a
separate view and is not represented as a completed atlas.
