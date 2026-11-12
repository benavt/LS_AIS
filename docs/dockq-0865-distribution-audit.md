# 0865 DockQ distribution audit

The accepted 9,999-comparison table has SHA-256
`fc321f809ab9977948bf49a70bd6abfd3334ce3a681ad8ca531293f28be2b62f`.
The separate full-DOC1 reference self-score is 1.0. These scores measure
similarity to **one AFsample3 0865 interface pose**, not general CDK2–DOC1
binding quality. The full-DOC1 and DOC1t reference scopes are different and
must not be pooled into one distribution.

| Target | Comparisons | Median | 90th percentile | Maximum | Zero native-contact recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| CDK2_DOC1 | 4,999 | 0.009 | 0.018 | 0.569 | 4,938 (98.8%) |
| CDK2_DOC1t | 5,000 | 0.023 | 0.033 | 0.184 | 4,892 (97.8%) |

The AFsample3 full-DOC1 median is 0.005, compared with 0.012 for AFsample2
and 0.008 for BioEMU2. The full-DOC1 reference has only 23 heavy-atom
residue-pair contacts at 5 Å, 22 of them within DOC1 residues 61–115. An
independent spatial-hash contact calculation on the three supplied PDB exports
recovers 18/23 contacts for 0867 (`fnat` 0.783) and 17/23 for 0868 (`fnat`
0.739), exactly matching the saved DockQ table after three-decimal rounding.
The test rejects a deliberately shifted DOC1 residue index. A read-only
nine-model audit on the native Mimas files also matched saved `fnat` values
for AFsample3, AFsample2, BioEMU2, full DOC1 and DOC1t cases. It found zero
reference contacts for a low-scoring AFsample3 model in 0865's HDBSCAN
cluster, so cluster membership does not imply the same local interface pose.

DockQ combines native-contact recovery, interface RMSD and ligand RMSD.
For 0867, strong contact recovery (0.783) and small interface RMSD (0.791 Å)
coexist with a 20.767 Å whole-ligand RMSD, yielding DockQ 0.569. For 0868,
the corresponding values are 0.739, 4.639 Å and 53.554 Å, yielding 0.286.
The flexible portion of DOC1 can therefore lower the RMSD component even
when much of the local interface agrees. This does not explain the many
models with zero recovered contacts: their saved poses differ from 0865 at
the residue-pair interface.

The audit found no residue-indexing or score-table join error in the tested
models. The existing scores should be retained; a second 9,999-model run
under the identical protocol would not repair this distribution. The
read-only guard is `scripts/audit_doc1_dockq_contacts.py`, which checks PDB
hashes, chain sequences, residue indices and independently computed `fnat`
against the saved table. Any future revised interface scope or reference
state needs a separately named metric and a small, reviewed pilot before a
full calculation.
