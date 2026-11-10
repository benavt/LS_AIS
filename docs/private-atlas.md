# Private atlas delivery

This repository is private. Atlas files are served on loopback for local QA or the explicitly approved private Tailscale IPv4 address, at `/LS_AIS/`, using the shared hash-verifying allowlist handler. A two-hour preview is the current delivery mode; it requires the Pax host and Tailscale to remain online. Access controls are inherited from the existing tailnet. Collaborators need authorized tailnet access; no public link or access change is created automatically.

Scientific results are serialized from accepted saved assets. The first target retains all 4006 originals and both full117-residue chains. The HDBSCAN view has68 clusters plus1386 Unassigned models; UMAP KNN has27 clusters. Each has its own medoids, comparison ensembles, TM matrix and Bonsai. Three full-dimer TM0.70 states contain1280,563,341 models, with1822 outside supported states. Each fine-view prior has three MCMC50 and three DISCO50 native panels, with seeds, exact controls, trace arrays and diagnostics.

The pinned state viewer originally validates a single-chain scope. The target adapter adds only the explicit `A,B`,234-position case with two117-residue chains and an exact native model-SHA match. It retains every state, mask, view-source, model-order, panel and artifact hash check. No coordinates, labels, priors, chains or scientific outputs are recalculated.

For browser downloads, NPZ traces are losslessly serialized as typed JSON arrays, retaining native source SHA256, dtype and shape and checked by round-trip. The unchanged pinned privacy checker scans their gzip-decoded text. Native NPZ originals remain private and unchanged in the accepted intake; this avoids treating arbitrary numeric bytes as embedded text while retaining a blocking content check.

Start with the exact runtime and Fleet local resource front door. `scripts/serve_private_atlas.py --site /absolute/site --bind PRIVATE_TAILSCALE_IP --port 18782 --duration 7200` records the bound manifest and expiry in ignored local output. All operational paths and directory listings return404. Unrecorded files are not served. Public publication and Zenodo remain separate decisions.

Run `node tests/check_private_payloads.cjs /absolute/site` to validate both saved views, exact state-panel hashes and cardinalities, energy coverage, and rejection of mismatched homodimer definitions. Browser review remains mandatory for the final private URL.

The current 4,006-model bundle passed the shared export privacy gate, exact-byte download checks, both-view browser review, CPU ensemble rendering and a 390-pixel responsive check. See `config/private-atlas-review.json` for the bound export hash and evidence. Tests use tiny saved fixtures; no scientific calculations run. Historical operational source metadata is retained in this private repository and is not a public-source release.
