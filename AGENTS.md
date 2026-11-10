# LS AIS atlas

Owns an extensible private atlas and target choices. Use `config/targets.json` for menu order and `targets/<slug>/` for target-specific settings. HSPH1 inherited settings and controllers stay at their historical root paths; do not move frozen paths or alter run provenance. Preserve original source history, native files, failed attempts and current selections.

Use the exact Structure_Clustering dependency in pyproject.toml and pinned external/research-workflows policy. Use structure-atlas-page and its contracts from that exact library Git pin. Fleet owns machine/runtime/access bindings. Native data, credentials and private machine paths stay in ignored local/ or existing remote runs. Source setup and CI never run scientific work.

Build saved assets with scripts/build_private_atlas.py; serve only verified allowlisted files through scripts/serve_private_atlas.py and the existing private Tailscale boundary. Test the real browser URL, both clustering views, structures, downloads, CPU fallback and responsive layout. Keep public publication separate. New targets require explicit construct, cohort, residue scope, accepted results and hash inventory; never infer scientific defaults or start calculations from adding a menu.

For HSPH1 preserve both exact 117-residue chains and supplied tag, current label, 4,006-model snapshot, accepted ProteinEBM/HDBSCAN/state/sampling artifacts and diagnostics. Do not infer organism/accession or mix future generation cohorts. Energy is separate from confidence. Request approval for reviewed source merges and public publication. Use codex/<task> branches from fetched origin/main after initial repository setup.

Source checks: python3 scripts/status.py; python -m unittest discover -s tests. Keep the homodimer presentation adapter narrow and retain exact model/hash and two-chain validation.
