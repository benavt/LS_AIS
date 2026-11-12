# LS AIS structure atlas

Public, extensible structure atlas for LS AIS targets: [open the atlas](https://benavt.github.io/LS_AIS/). HSPH1 construct 12757 is the first target: 4,006 native homodimers with complete 117-residue chains, ProteinEBM energies, UMAP KNN and HDBSCAN clustering, native comparison ensembles, medoid TM grids, Bonsai, and saved MCMC50/DISCO50 panels. DOC1R and DOC1 dimer–CDK2 share the same atlas menu: 133,263 accepted models with full and A/B-core geometry, full-complex ProteinEBM scores, PCA, t-SNE, Cα maps, energy-selected cluster representatives, and native Bonsai trees for all 12 clustering views.

The linked target menus keep HSPH1 and DOC1/CDK2 within one GitHub Pages atlas. Each target has independent residue-range and clustering menus. The HSPH1 cohort retains 1,386 HDBSCAN unassigned models and 1,822 models outside the three supported structural states. Library counts are not biological populations; fixed-budget sampling diagnostics do not establish convergence. DOC1/CDK2 clusters are exploratory; their energy-selected representatives are not structural medoids. The deferred large TM grid and reference-state comparisons, as well as DOC1/CDK2 MCMC/DISCO panels, are not included.

## Layout

- `config/targets.json`: ordered target menus and target metadata pointers.
- `targets/<slug>/`: target-specific configuration and future adapters.
- `scripts/build_private_atlas.py`: compose one verified saved delivery per registered target and export through the pinned blocking privacy gate.
- `scripts/assemble_hsph1_private.py`: serialize the accepted HSPH1 saved results; no fitting, scoring or sampling.
- `scripts/serve_private_atlas.py`: bounded, allowlisted private Tailscale preview at `/LS_AIS/`.
- `scripts/doc1_cdk2/package_public_standard_atlas.py`: hash-bind and privacy-check the reviewed combined atlas, with lossless coordinate compression for Pages.
- `site/`: small presentation adapters; generated atlases remain in ignored `local/`.
- Existing HSPH1 `config/`, `scripts/completion/`, and historical docs preserve the source paths of frozen plans.

Native coordinates, arrays, run outputs and private host bindings stay out of the source branch. The public atlas is deployed from the `gh-pages` branch. The original HSPH1 repository and scientific runs remain intact; a private backup preserves the pre-publication LS AIS history. The public source history redacts one old cluster filesystem path.

## Build and review a saved atlas

Use the exact dependency in `pyproject.toml` and the configured Fleet local resource front door. Prepare each target's accepted saved delivery, then run:

```bash
python scripts/build_private_atlas.py \
  --target-source HSPH1_12757_homodimer=/absolute/verified/delivery \
  --output local/atlas/NEW_RUN/site
```

The builder verifies every size and SHA256, rejects colliding target artifacts and incompatible shared renderer bytes, merges target catalogs, and calls the shared saved-file exporter. It never starts science or deploys a public site. See [adding targets](docs/adding-targets.md) and [private preview workflow](docs/private-atlas.md).

GitHub Pages publishes the reviewed HSPH1 and DOC1/CDK2 static exports. Saved model PDB/CIF downloads use lossless gzip transport and retain the native-coordinate SHA-256 in the atlas. Zenodo has no published record or DOI for this project, and the data license remains unresolved. The private Tailscale server remains available for bounded prepublication reviews.
