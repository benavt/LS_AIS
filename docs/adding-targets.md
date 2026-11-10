# Add another target

1. Create `targets/<slug>/config/` and `targets/<slug>/scripts/` for its construct, exact cohort/coordinate hash roster, model-type schema, residue ranges, scientific plan and accepted saved-result adapter. Reuse the pinned library. Do not copy HSPH1 scientific settings to a new target.
2. Freeze and obtain any required scientific execution approval separately; adding source or a menu never authorizes a calculation. Require ProteinEBM, UMAP KNN, geometry HDBSCAN, each view's own medoids/ensembles/TM/Bonsai, and the skill's sampling workflow or an explicit documented decision.
3. Export a fresh saved delivery using the same pinned renderer and presentation adapters. Namespace all target artifacts under its unique target ID (dataset and downloads included). Supply `atlas.json`, source view JSONs, the target's catalogs, and a sibling `delivery-manifest.json` with every file's byte count and SHA256. Catalogs must name only that target. Shared renderer assets must be byte-identical between deliveries.
4. Add one ordered entry in `config/targets.json` with ID, display name, target config and Primary data path. No additional server, page or repository is needed.
5. Run `scripts/build_private_atlas.py` with one `--target-source ID=/absolute/delivery` per registered target. The builder merges catalogs, validates saved views and rejects cross-target collisions. Outputs must be new and ignored.
6. Review the real private target deep link; switch targets, residue ranges and both clustering views, inspect medoids and native downloads, and verify source identities and responsive rendering. Publish a newly reviewed export to `gh-pages` only after its own privacy and content checks.

The current HSPH1 controllers remain at their original paths because frozen plans bind them by hash. That historical layout does not dictate new target layouts.
