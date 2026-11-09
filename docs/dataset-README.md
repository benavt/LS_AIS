# HSPH1 construct 12757: native homodimer models

This snapshot contains 4,006 generated models of the user-supplied construct labelled **HSPH1 construct 12757**. Each model has two identical 117-residue chains (234 residues total), including the supplied N-terminal tag. Organism, UniProt accession and biological oligomeric state have not been established from these records. No experimental structure is included. The label identifies this exact construct rather than an inferred full-length protein.

The per-chain sequence is:

```
MGHHHHHHSHMKIGTPVKVRFQEAEERPKMFEELGQRLQHYAKIAADFRNKDEKYNHIDESEMKKVEKSVNEVMEWMNNVMNAQAKKSLDQDPVVRAQEIKTKIKELNNTCEPVVTQ
```

Its SHA-256 is `395f1ee96750b40c96f7de2f655416a768ab8b8a09ccbb9813900351119e86a2`.

## Contents

- `sequence.fasta`: the two identical construct sequences, with canonical chain labels A and B.
- `models.tar.gz`: the original native PDB/mmCIF files, grouped by generating method. Coordinate bytes are unchanged.
- `scores.csv`: one row per archived coordinate file; `model_file` is the exact archive member, and `sha256` verifies its bytes.
- `README.md`: construct identity, cohort, provenance, score definitions and references.

The archive includes AFsample2 (1,000 models), AFcluster (1,000), SPEACH_AF (1,000), OpenDDE (1,000), AFsample3 (5) and BioEmu2 (1). The AFsample3 and BioEmu2 entries are accepted pilot outputs, counted inside their respective planned 1,000-model arms; this snapshot does not claim those larger arms are complete. These method counts are deliberately unequal. Cluster sizes and model frequencies describe the selected generated library, not experimental populations or calibrated equilibrium probabilities.

## Generation and acceptance

AFsample2 [1], AF-Cluster [2] and SPEACH_AF [3] were generated through the native AIS workflow using AlphaFold2/Multimer machinery [4]. OpenDDE is a separate all-atom prediction method [5]. These four complete arms originate in the retained 2026-10-24 HSPH1 native runs, whose scientific adapter source is `50ad85d5cb57695c35f7e9465fe4ea257cc8a6bf`.

The new AFsample3 [6] pilot uses AlphaFold 3 [7], 40% MSA masking, ten recycles and five samples for seed 101. The BioEmu2 pilot uses release `v0.1.0rc0`, native source `621fbe4d4338548ec8d0c74f4f16ea9e1d779232`, native EDM sampling with 200 steps, batch size one, step/noise scale one and mixed bfloat16 precision. Cite the actual BioEmu2 software release [8]; the earlier BioEmu research basis [9] is a distinct model and does not establish the behaviour of this single BioEmu2 sample.

Native files are associated with validated producer manifests and exact coordinate hashes. The selected producers' 271 whole-job resource logs passed their pinned checks with successful native exits. Every deposited model was checked for both complete construct sequences, native residue numbering and 234 finite C-alpha coordinates. The BioEmu2 native physicality record was retained; this dataset adds no new physicality filter, relaxation or experimental validation.

Native AFsample2/AFcluster/SPEACH_AF files name the chains B/C; OpenDDE and the new pilots name them A/B. For joint analysis only, a fixed producer-derived B→A, C→B mapping gives common canonical A/B labels. It does not choose a per-model chain permutation to improve similarity. Native downloads retain their original labels and atom coordinates.

## Scalar scores

Scores join native coordinates by exact model ID and SHA-256. Unavailable values are empty cells, never zeros. The source prediction method remains separate from score annotations.

- `ptm` and `iptm`: native reported prediction confidence on the 0–1 scale; higher indicates greater model confidence. Coverage is 4,005 models, including the five AFsample3 pilots. BioEmu2 has neither value in this snapshot.
- `mean_plddt`: native reported mean pLDDT, on the 0–100 scale; coverage is 3,000 models (AFcluster, SPEACH_AF and OpenDDE). No pLDDT is inferred from ordinary coordinate B factors. The `physical_filter_flag` column preserves the BioEmu2 native model-manifest value `retained`; other methods have empty cells. It is a recorded retention status, not a new physicality score or filter.
- `ranking_confidence`: the saved native value where present, preserved separately from other ranking formulas. Coverage is 1,000 AFsample2 models.
- `ranking_score`: the saved native OpenDDE or AF3 ranking value; coverage is 1,005 models. This is not substituted for the common multimer confidence formula.
- `common_multimer_ranking_confidence`: derived solely as `0.8 * iptm + 0.2 * ptm` where both native values exist; coverage is 4,005. It is used consistently for confidence-eligible comparison ensembles.
- `protein_ebm_energy_t010`: unavailable for every model in this snapshot. Native ProteinEBM Model 6 scoring is planned but has not passed execution admission/acceptance. No ProteinEBM value, rank, probability or physical energy is inferred. Future accepted values would be full-dimer learned scores in arbitrary units, with t=0.10 as the primary conditioning level.

Multidimensional confidence matrices, trajectories, private machine locations and operational receipts are outside this compact package and remain with the scientific run. Native confidence does not establish experimental accuracy or a calibrated conformational population.

## Atlas analysis

The companion analysis uses Structure_Clustering `f3063757460303e1a4a4ba0b3629fe81776c58c4` and research-workflows `fc0e961f1581e93c8dd854ac890f9d300d00f6d5`. It jointly fits these exact 4,006 models using all 234 canonical C-alpha positions and all 27,261 residue-pair distances, including 13,689 inter-chain pairs. No residue trimming, exclusions or experimental controls are introduced.

PCA, UMAP [10] and t-SNE [11] use saved shared-workflow settings and seed 42. The common cluster labels preserve UMAP components; subdivisions require structural-feature silhouette at least 0.15 and agreement of at least 0.80 ARI for repeat seeds 7 and 123. Exact full-cluster, fixed-chain C-alpha rigid-fit medoids are reported separately from up to five confidence-eligible ensemble members per cluster. Clusters lacking confidence use explicitly unscored medoid/nearest examples. Aligned exports are derived visual comparison files and are not the unchanged native coordinates in this package. The companion Bonsai tree [12] uses the union of selected comparison members and full-cluster medoids, all nonzero centered PCA axes of their complete-construct distances, no whitening, kNN=10 and the native seed 42. Its geometry and in-sample exploratory tree groups do not establish evolutionary relationships or transition kinetics. The medoid TM grid [13] uses non-fast US-align in both directions, average-length normalization and the fixed A/B chain mapping. These derived visual analysis files are separate from this compact native-coordinate package.

## References

1. Kalakoti Y, Wallner B. AFsample2 predicts multiple conformations and ensembles with AlphaFold2. *Communications Biology* **8**, 373 (2025). https://doi.org/10.1038/s42003-025-07791-9
2. Wayment-Steele HK, Ojoawo A, Otten R, Apitz JM, Pitsawong W, Hömberger M, Ovchinnikov S, Colwell L, Kern D. Predicting multiple conformations via sequence clustering and AlphaFold2. *Nature* **625**, 832–839 (2024; published online 2023). https://doi.org/10.1038/s41586-023-06832-9
3. Stein RA, Mchaourab HS. SPEACH_AF: Sampling protein ensembles and conformational heterogeneity with Alphafold2. *PLOS Computational Biology* **18**(8), e1010483 (2022). https://doi.org/10.1371/journal.pcbi.1010483
4. Jumper J, Evans R, Pritzel A, et al. Highly accurate protein structure prediction with AlphaFold. *Nature* **596**, 583–589 (2021). https://doi.org/10.1038/s41586-021-03819-2
5. Aureka AI OpenDDE project. Folding, Reasoning, and Scaling with Open-source Drug Discovery Engine. *arXiv* 2607.03787 (2026), preprint. https://doi.org/10.48550/arXiv.2607.03787
6. Kalakoti Y, Wallner B. AFsample3: Generating and selecting multiple conformational states with Alphafold3. *bioRxiv* 2026.01.16.699904 (2026), preprint. https://doi.org/10.64898/2026.01.16.699904
7. Abramson J, Adler J, Dunger J, et al. Accurate structure prediction of biomolecular interactions with AlphaFold 3. *Nature* **630**, 493–500 (2024). https://doi.org/10.1038/s41586-024-07487-w
8. Microsoft Research AI for Science. BioEmu2, release v0.1.0rc0 (2026), software. https://github.com/microsoft/bioemu2/releases/tag/v0.1.0rc0 ; source used: https://github.com/microsoft/bioemu2/tree/621fbe4d4338548ec8d0c74f4f16ea9e1d779232
9. Lewis S, Hempel T, Jiménez-Luna J, et al. Scalable emulation of protein equilibrium ensembles with generative deep learning. *Science* **389**, eadv9817 (2025). https://doi.org/10.1126/science.adv9817

10. McInnes L, Healy J, Melville J. UMAP: Uniform Manifold Approximation and Projection for Dimension Reduction. *arXiv* 1802.03426 (2018; revised 2020). https://doi.org/10.48550/arXiv.1802.03426
11. van der Maaten L, Hinton G. Visualizing Data using t-SNE. *Journal of Machine Learning Research* **9**(86), 2579–2605 (2008). https://jmlr.org/papers/v9/vandermaaten08a.html
12. de Groot DH, Morillo Leonardo SX, Pachkov M, van Nimwegen E. Bonsai reconstructs tree representations for distortion-free visualization and exploration of high-dimensional data. *Nature Biotechnology* (2026). https://doi.org/10.1038/s41587-026-03220-2
13. Zhang C, Shine M, Pyle AM, Zhang Y. US-align: universal structure alignments of proteins, nucleic acids, and macromolecular complexes. *Nature Methods* **19**, 1109–1115 (2022). https://doi.org/10.1038/s41592-022-01585-1

This is a review candidate. Production repository visibility, dataset licensing and Zenodo publication metadata require the separate reviewed publication step. No published Zenodo record or DOI is asserted.
