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

The approved ProteinEBM Model 6 production plan
(`c8eead144f40b7f9ca972473998e9946c20b986564b87a74153bbdb23c863195`)
is running in 134 monitored GPU chunks. Each accepted model will receive the
same 16-level energy grid. The first 1,000-model DOC1R chunk validated with
16,000 finite energy values and a passing finished GPU log. Full-cohort score
acceptance has not yet run. Clustering, MCMC/DISCO, and atlas exports still
require their own hash-bound plans and accepted outputs. The existing HSPH1
public page does not include either target yet.
