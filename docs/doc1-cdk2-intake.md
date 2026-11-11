# DOC1 dimer–CDK2 atlas intake

Two separate three-chain targets are staged for LS_AIS. Each uses the complete
native construct for analysis: DOC1R has A126, B126, C298 (550 Cα positions),
and DOC1 has A115, B115, C298 (528 Cα positions). Chain A and B are identical
within each target. Neither a UniProt accession nor organism is verified, so
experimental-reference collection is deferred until the identity is known.

| Target | ZIP SHA-256 | Archive PDB entries | Accepted models | Explicit exclusions |
| --- | --- | ---: | ---: | ---: |
| DOC1R dimer + CDK2 | `c8aa11e9f24f04e5e42f384d7bcddf5a3c075b01394cbf2e7dd418fe4c68ddfa` | 57,464 | 57,463 | 1 |
| DOC1 dimer + CDK2 | `b85ec33499efda84c887f665f0a1487eb0ffc928a4fc3ca6e3b03f4d918960f6` | 75,800 | 75,800 | 0 |

The DOC1R source archive contains one zero-byte member,
`spec_inter_ref_sto_af3_662.pdb` (empty-file SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
It remains in the extraction manifest and has an explicit frozen exclusion in
the target configuration. No other model was silently dropped, and no accepted
model duplicates another native byte hash within its target.

The accepted private roster SHA-256 values on Mimas are
`18115945560c439cecba3c58bc317a3ac5137594746fbaeb9e9d65d963be1bbc`
for DOC1R and
`80ad44512e91a49bf52996ef4b00c46e73ce080f9353741904ca6b9ae3330682`
for DOC1. Every accepted file has exactly one model, complete A/B/C chain
numbering, the target's frozen chain sequence hashes, and finite Cα coordinates.
Private full sequences and original coordinates remain on Mimas.

The approved full-construct Cα geometry plan
(`4a414103f270b2cef731294fc20206e64a3623baebe81adceeb661de53d23764`)
has finished on Mimas. DOC1R has 150,975 pair distances per accepted model;
its validated receipt SHA-256 is
`3d6f284bee585eed54d8fda8cfc3d08b0be76556213db3004b36e495f733b140`,
and the complete distance matrix SHA-256 is
`e1c9711173ef9fcd2ba0170fba33f8dd9a75fa91109a46ac903eefaf5963d465`.
DOC1 has 139,128 pair distances per accepted model; its receipt SHA-256 is
`9a645f4842b1ad16be89be99e9e2b2cdea479bb0e6795b43b5791d578e5c3326`,
and its matrix SHA-256 is
`fac2a461a5f1fce00538b210d40f21133b22edcfbf49295484ac92dd1cb0bd7f`.
Both monitored CPU resource logs passed. These matrices retain every Cα pair
across chains A, B, and C; they are private source data, not atlas downloads.

A bounded direct-UMAP feasibility pilot
(`8911e49577c9403b05bed99acf749bb0edca6ba284e3637cd2aabda6937ec8bd`)
fit 2-D and 10-D projections on a fixed 5,000-model sample of each complete
distance matrix. DOC1R took 1,448 and 1,404 seconds; DOC1 took 1,226 and
1,194 seconds, respectively. Peak observed memory was 13.9 and 12.9 GiB.
Both completion records and finished resource logs passed. The DOC1R and DOC1
pilot receipt SHA-256 values are
`4a9afa76e83e05e573c5d92a4a45f51f968ba36735d48a6b6f4fb9a13ca10bc9`
and `a8e10aeab5aead1b81a61737f25a4825e5bdf117be7a65d36d2474b367435930`.
These are sampled performance measurements, not full-cohort cluster results.

The approved all-pair sketch fidelity pilot
(`db94a219ef1b5d9be81be88105a64035b1b16a6dd35b7e2387264657219fcea0`)
tested the same 5,000-model samples. Each original A/B/C pair feature mapped
once into a signed 2,048- or 4,096-dimensional sketch. On 256 fixed evaluation
models per target, the 4,096-dimensional sketch had median relative pair-distance
errors of 0.80% (DOC1R) and 0.81% (DOC1), 95th-percentile errors of 2.27% and
2.08%, and mean 15-neighbor recalls of 96.9% and 97.1%. The 2,048-dimensional
sketch had median errors of 1.18% and 1.19%, and mean recalls of 95.6% and
96.0%. Acceptance receipt SHA-256 values are
`ba9943fdfb85cce54b1e2ae8589bd4a842968d71a9140850697fd14974f992fb`
and `1db3c89785371e4bfd8d5bf1945c559d6a54c349e12cfd2486d9199ef6cbe617`.
Both completion records reported exit zero and both finished CPU resource logs
passed. This validates sampled fidelity only.

The full-cohort geometry clustering plan
(`76024b0e0cff251ca7b6cc2dfb309e26fa1d92192d860df2dcc7eb33ff99bc6c`)
was explicitly approved and completed on Mimas as monitored Slurm array 26011.
It ran one target at a time, fitting a 2-D UMAP KNN partition and 10-D
HDBSCAN leaf/EOM partitions at seeds 42, 7, and 123 from the validated
4,096-dimensional all-pair sketch. It excludes ProteinEBM energies. Each task
reproduced the accepted 5,000-model sketch exactly and wrote full-cohort
labels, strengths, model identities, and diagnostics. Both acceptance receipts,
all 28 referenced output hashes, zero-exit completion records, and finished
CPU monitors passed. Receipt SHA-256 values are
`24c734481c2e6b42e074983a2a9c8b20ab6d819476f3b917a8385d090465756d`
for DOC1R and
`c6f7be99d0a5edc2d1bd9dc275fd3ae31f0b4d26861ee255450e853bfca687e3`
for DOC1.

| Target | UMAP KNN groups | Seed-42 HDBSCAN leaf groups | Leaf unassigned | EOM groups (diagnostic) | EOM unassigned |
| --- | ---: | ---: | ---: | ---: | ---: |
| DOC1R dimer + CDK2 | 2 | 391 | 35,334 (61.5%) | 182 | 7,193 (12.5%) |
| DOC1 dimer + CDK2 | 6 | 476 | 50,093 (66.1%) | 150 | 4,324 (5.7%) |

The leaf partitions preserve their large unassigned populations; EOM is a
saved alternative diagnostic, not a relabeling of the selected leaf view.
Seed agreement and structural interpretation need review before these cluster
labels are presented as atlas states. The computational outputs are accepted,
but medoids, ensembles, TM grids, Bonsai, and MCMC/DISCO are still missing.

The approved ProteinEBM Model 6 production plan
(`c8eead144f40b7f9ca972473998e9946c20b986564b87a74153bbdb23c863195`)
finished all 134 monitored GPU chunks. Every accepted model received the
same 16-level energy grid. Array 25984 ran up to four concurrent one-GPU
tasks under the explicitly
approved resource-only amendment
(`ee2f5bbfee05bcdf40c0c869d9122f2c92df186eae176558b3b11e53b61e0334`).
All 134 completion events and whole-job GPU logs finished with zero exit codes.
The approved CPU acceptance job 26146 validated exact model ID and native-hash
order, finite 16-level grids, and full-roster coverage: 919,408 DOC1R and
1,212,800 DOC1 energy values, 2,132,208 total. The DOC1R and DOC1 acceptance
receipt SHA-256 values are
`98699db15988dcc07e7021be9cee7d001dfb5c5fafe9d6e0c5b36815af55d4b7`
and `fbb5eb821d15183a7470f4b6670d9025ac73b6e818d5cf080ca9e3dcc790c4f8`.
The primary atlas value is t=0.10 (index 10), with learned arbitrary units;
it is neither binding energy nor confidence. The private preview overlays
these full-complex scores on both full and A/B-core geometry fits without
refitting either clustering. Cluster representatives, Bonsai, and MCMC/DISCO
remain pending. The public HSPH1 page is unchanged.
