# DOC1/CDK2 A/B-core geometry clustering

The [residue-subset proposal](doc1-cdk2-core-reclustering-proposal.md) uses
A65–126/B65–126/C1–298 for DOC1R and A60–115/B60–115/C1–298 for DOC1.
All 57,463 and 75,800 accepted native models, respectively, remain in the
new fit rosters. ProteinEBM values are separate and are not fit features.

The user approved the exact pilot plan SHA-256
`e896b769379bee8264df6d0d1909faedb96e6f3e3615a141ad1ba9fd7eb545e7`.
Mimas array `26075` finished both tasks with validated receipts, zero-exit
completion events, and finished whole-job CPU resource logs. The pilot tested
three symmetric A/B starts per target on the accepted fixed 5,000-model
samples and measured 256 exact-model comparisons, with C kept complete.
The DOC1R and DOC1 pilot receipt SHA-256 values are
`af1d5cefd1804a57deca109c02161c4657ba0d789a63623d6be61b0d8bf4d176`
and `e5102afd5ea9f49a8f98691bd58b576d1d07b3918551612941ee602b07ac69db`.

| Target | A/B start | 4,096-D sketch 15-neighbor recall | 95th-percentile relative distance error | Exact 15-neighbor overlap with primary |
| --- | ---: | ---: | ---: | ---: |
| DOC1R | 60 | 97.84% | 2.35% | 85.86% |
| DOC1R **primary** | **65** | **98.39%** | **2.13%** | **100%** |
| DOC1R | 70 | 98.20% | 1.69% | 96.15% |
| DOC1 | 55 | 98.28% | 1.89% | 95.05% |
| DOC1 **primary** | **60** | **98.46%** | **1.80%** | **100%** |
| DOC1 | 65 | 98.20% | 2.01% | 97.89% |

The primary masks passed the predeclared 95% neighbor-recall and 3%
95th-percentile distance-error gates. The DOC1R start at 60 alters the exact
neighborhoods more than the start at 70, supporting residue 65 as the cleaner
core boundary. The pilot verified selected condensed-pair columns against
native coordinates in first, middle, and last roster models. It did not fit
full-cohort clusters.

The user approved the full-cohort fit plan SHA-256
`dcec61046f7b836a4ee86e56263ab2d8c2994554cab7edac693c021202222145`.
Mimas array `26077` was submitted with two serial 8-core CPU tasks,
256 GiB and 36 hours maximum per task, zero GPUs, and zero paid external
calls. Its frozen code must reproduce the primary pilot sketch on the exact
5,000 sampled rows before UMAP or HDBSCAN fits. The accepted full-construct
fits remain available as the comparison baseline.

Both array tasks finished with zero-exit completion events. The read-only
acceptance audit verified all 16 referenced output files per target, the
frozen model/geometry/pilot identities, and finished whole-job CPU resource
logs. DOC1R receipt SHA-256:
`b1a1f6c42e55c854e28b7bb869ce38031e6efe297e75c90c3a5f6de933d9577d`;
DOC1 receipt SHA-256:
`d13deb318f13ec6fe3e81ad353900d3c08e39cefcf9d05e258f3a115073adf56`.

| Target and fit | UMAP KNN groups | HDBSCAN leaf groups, seed 42 | Leaf unassigned | HDBSCAN EOM groups, seed 42 | EOM unassigned |
| --- | ---: | ---: | ---: | ---: | ---: |
| DOC1R full A/B/C | 2 | 391 | 35,334 (61.5%) | 182 | 7,193 (12.5%) |
| DOC1R A/B65–126 + C | **15** | **576** | **30,342 (52.8%)** | **406** | **18,623 (32.4%)** |
| DOC1 full A/B/C | 6 | 476 | 50,093 (66.1%) | 150 | 4,324 (5.7%) |
| DOC1 A/B60–115 + C | **10** | **707** | **43,953 (58.0%)** | **252** | **7,405 (9.8%)** |

The core fits reduce leaf unassigned populations, but they increase EOM
unassigned populations. Seed agreement is mixed: DOC1R leaf ARI including
noise is 0.600/0.584 versus 0.618/0.592 for the full fit, and DOC1 leaf is
0.584/0.581 versus 0.617/0.613. EOM agreement falls more sharply,
especially for DOC1 (0.398/0.407 versus 0.965/0.971). These are geometry
partitions, not validated biological states; inspect representatives and
boundary sensitivity before interpreting them. No atlas view or public
export has been changed by this calculation.
