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
