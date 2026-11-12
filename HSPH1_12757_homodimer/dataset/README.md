# HSPH1 construct 12757 · accepted private atlas

The snapshot contains 4,006 exact native homodimers: 1,000 each AFsample2, AFcluster, SPEACH_AF and OpenDDE; five AFsample3 pilots and one BioEmu2 pilot. Both complete 117-residue chains, including the supplied tag, are retained. Organism and UniProt accession remain unverified. The supplied construct sequence appears in sequence.fasta. Original downloads retain native chain IDs; comparison-only canonical mapping is A/B.

## Geometry and clustering

All 234 Cα positions and 27,261 pair distances are included, without trimming. Saved seed-42 PCA, UMAP and t-SNE coordinates display every model. UMAP KNN has 27 clusters, with subdivisions validated by feature silhouette ≥0.15 and repeat-seed ARI ≥0.80. Geometry-only HDBSCAN uses the saved 10D UMAP seed-42 leaf result: n_neighbors=30, min_dist=0, min_cluster_size=15, min_samples=11. It has 68 clusters and 1,386 Unassigned models. Six seed/leaf/EOM fits are retained in the scientific run.

Each partition has its own exact full-cluster fixed-chain Cα medoids, full-atom comparison ensembles and complete native bidirectional US-align medoid TM grid with average-length normalization. Comparison ensembles use up to five common-native-confidence eligible members, or an explicitly unscored structural fallback. Bonsai uses each view's saved selected ensemble members plus medoids (161 UMAP KNN and 402 HDBSCAN leaves), all nonzero centered PCA axes, no whitening, kNN=10, and three saved layouts. Five explicit HDBSCAN noise examples are included.

## ProteinEBM and native confidence

ProteinEBM model 6 scores all 4,006 exact native coordinate hashes at 16 time indices. The primary score is index 10, t=0.10. The model commit is 2abfc58571e6528edf0919daf37a6c74bcf77f67. Scoring used template sidechains, mask_sequence=false, inference_sidechains=false and normalization=false. Values are learned arbitrary units, not physical binding energy. scores.csv joins the primary energy to native scalar confidence; the energy CSV provides all 16 levels. Native pTM/ipTM cover 4,005 models; native mean pLDDT covers 3,000. Missing values remain blank. Confidence and energy are distinct quantities.

## Structural states, MCMC and DISCO

Fixed-chain, full-dimer positional TM≥0.70 state memberships use the accepted medoid discovery anchors. Three supported states contain 1,280, 563 and 341 models; 1,822 remain outside them. They are representative-relative neighborhoods, not all-pairs certificates or biological populations. Sensitivities at 0.60, 0.70 and 0.80 are retained.

Each Primary/HDBSCAN fine-view prior has one MCMC50 and one DISCO50 panel for each state: 12 panels and 600 coordinate instances, with 50 distinct native models within each panel. Priors retain full-cohort group/noise masses before conditioning on a state, with alpha=0.5 and tau equal to the full-4,006 energy IQR, 78.0931396484375. Fixed-cardinality product-weight MH includes the full Hastings ratio. Each condition has four 10,000-proposal chains, 1,000 burn-in proposals and 20 exact control panels; chain 0's final panel was prespecified. DISCO uses the accepted fine-group energy/coverage control. Seeds, protocols, priors, accepted trace values and diagnostics are linked beside the atlas.

Every full-atom panel uses one native whole-complex pose; chains are not fit independently. Completion and energy-level R̂/ESS do not establish convergence. All group, noise, method and exact-control diagnostics remain available. Library frequencies are not calibrated equilibrium populations.

## Provenance and delivery

The accepted scientific supplement manifest SHA256 is a9b5c44b6a25c0d142c073e624c078c67d99f63826fcaca0f8203e4ac9d4ce13. The pinned analysis/presentation library is f3063757460303e1a4a4ba0b3629fe81776c58c4. Native hashes identify every plotted or downloaded model. Scientific JSON and native results remain preserved. Typed JSON trace downloads retain source NPZ hashes, dtypes, shapes and exact values.

This is a private review atlas. No public Zenodo record or DOI has been issued; data licensing and public release remain separate decisions. Additional queued generation models are outside this frozen cohort.
