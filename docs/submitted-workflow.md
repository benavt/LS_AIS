# Submitted current 4,006 completion workflow

All remaining Mimas stages were submitted on November10,2026 after the user's
explicit instruction to submit. Every stored scheduler script was verified by
the frozen Fleet front door. Exact script, batch and executable-plan hashes are
in [the submission ledger](../config/mimas-submissions.json). Scientific inputs,
methods and numeric settings remain within the approved current 4,006 plan.

| Stage | Job | Status at verified check |
| --- | --- | --- |
|P2_002|25683|Passed|
|E0|25685|Passed|
|E1|25687|Passed|
|E2|25688|Passed|
|E3|25689|Passed|
|E4|25690|Passed|
|E5|25691|Passed|
|R0 Native export runtime repair|25885|passed|
|D0 Geometry-only HDBSCAN|25888|running|
|D1 Density medoids/ensembles|25889|pending_dependency|
|D2 Own medoid TM grid|25890|pending_dependency|
|D3 Own native Bonsai|25892|pending_dependency|
|S0 Full-dimer protocol fixtures|25893|pending_dependency|
|S1 Geometry-guided structural states|25894|pending_dependency|
|S2 MCMC50 and DISCO50|25895|pending_dependency|
|S3 Scientific acceptance|25896|pending_dependency|
|X0 Selected delivery/privacy audit|25897|pending_dependency|

Checked 2026-11-10T15:38:33.161475-05:00. ProteinEBM accepted all 4,006 models,64,096 energies,14,998,464 per-residue values and4,496 native GPU batch calls. The full grid hash and E5 own finished inner/outer resource logs passed. All 41 GPU tasks completed;the CPU repair requests zero additional GPU work.

The first P2 attempt25679 stopped before reading target models because the new
adapter used Fleet's initial intent record. The diagnosed repair reads its
final submission receipt;25683 passed with unchanged inputs. Both attempts are
preserved. The final producer gate also binds array resource logs to their
submitted scheduler identity.

R0 job 25722 failed because the offline PyTables wheel required blosc2, which was absent from the 37-package lock. The repair retains all 37 versions and adds 20 hash-verified binary dependency pins. The failed dependency check was reproduced before the repaired 57-package bundle resolved and installed offline. Fresh local native Bonsai imports and a two-row HDF roundtrip passed.

The first repair attempt25874 omitted the existing containment helper and stopped before worker execution. Its exact launcher import was reproduced, then passed with the helper restored. The final fresh runtime job 25885 passed the same native fixtures and both own finished monitoring checks. Failed attempts, original environments and all accepted scoring results remain intact. The nine unstarted CPU stages were resubmitted with success dependencies and unchanged scientific workers, inputs, seeds, settings and resource ceilings.

HDBSCAN uses the same27261 saved distance features,three10D seeded UMAP fits
and six leaf/EOM extractions. Scores are verified before this work and excluded
from geometry. Each partition owns its actual selection,grid and native tree.
The full-dimer state protocol preserves chain identity at all234 positions.
Sampling streams were frozen before state outcomes in
[the stream ledger](../config/sampling-streams.json). Each eligible state/prior
condition uses four10000-proposal chains,1000 burn-in,the prespecified chain0
final panel,20 exact controls,and a real DISCO50 panel. Noise,unsupported states,
uncovered models and diagnostic limitations remain explicit. There is no
automatic extension,retry,tuning or forced biological state count.

23 source tests passed before submission. Native scoring and acceptance checks now cover all 4,006
models and all 41 GPU allocations. The repaired runtime also passed its native
fixtures and both finished monitor checks. Later analysis results remain pending;
successful submission is not scientific acceptance. X0's own finished log must be checked externally before collection.

The original partial atlas and native archive remain preserved. The future
AFsample3/BioEmu2 production arms remain outside this frozen cohort. BioEmu2
production was observed running separately;this repair did not change generation jobs. Public
GitHub Pages and Zenodo publication remain held for a complete private successor,
browser review,final metadata/file checks and data-license resolution.
