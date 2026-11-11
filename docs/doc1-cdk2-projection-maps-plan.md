# DOC1/CDK2 projection and Cα map plan

The private DOC1/CDK2 preview currently has accepted full-cohort UMAP and
geometry-only cluster memberships. PCA, t-SNE, median Cα distance maps, and
Cα distance variance maps are absent from the accepted run inventory.

The frozen Mimas plan SHA-256 is
`8f2b26e94195a55327cbd3d5d3d341352019eb5cdebe06f3172c6ad4fe78360d`.
It is staged privately with exact input paths, receipt hashes, code hash,
settings, output contract, and resource limits. It has **not been submitted**.

| Target | Accepted models | Full A/B/C Cα positions | Pair features |
| --- | ---: | ---: | ---: |
| DOC1R dimer–CDK2 | 57,463 | 126 + 126 + 298 = 550 | 150,975 |
| DOC1 dimer–CDK2 | 75,800 | 115 + 115 + 298 = 528 | 139,128 |

For each target, the job verifies the accepted roster and the byte hashes of
the complete Cα pair matrix and the validated 4,096-feature all-pair sketch.
It fits a 50-component, unwhitened randomized PCA on **all** accepted models;
the first two coordinates and their explained variance form the PCA plot.
t-SNE fits all accepted models on those same 50 PCA coordinates with perplexity
30, Barnes–Hut, 1,000 iterations, and seed 42. This dimensionality reduction
before t-SNE is explicit because direct nearest-neighbor search in 4,096
dimensions would be impractical for these cohort sizes.

The variance map uses every accepted model, population variance in Å², and all
A/B/C residue pairs. The median distance map uses a reproducible uniform
5,000-model sample per target; it is labeled as sampled rather than a
full-cohort median. Both maps show A/B/C boundaries and retain every residue.
The job creates PCA and t-SNE coordinates, sampled indices, numeric map
matrices, PNG maps, and a hash-bearing acceptance receipt. No ProteinEBM values,
experimental structures, residue trims, 3-D box summaries, or pair-distribution
detail plots are added.

Execution is a monitored serial two-task CPU Slurm array: eight CPU cores and
256 GiB per task, at most 36 hours per task, with a hard request ceiling of
576 CPU-core-hours and zero GPUs. It makes zero paid external calls. After
both tasks finish, accept output hashes and finite full-roster coordinates,
then add PCA and t-SNE to the private atlas explorer and the two map figures
to each target's figure section. The public atlas is unchanged until separately
reviewed and approved for publication.
