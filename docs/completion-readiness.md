# Completion execution repair

The user approved the current 4,006-model Mimas plan with SHA-256
b887c9c362f8dad0cc6211f83d0a33208cd69e8d05faf23594b86cfa58a067b6,
then explicitly requested rechecking, repair and resubmission. The original
administrator-dependency conclusion was incorrect. The account already has
a writable systemd delegation supporting private memory, swap and task limits.
No administrator action, global configuration change or message was needed.

The approved planning snapshot is preserved byte-for-byte, including its now
superseded admission assumption. This execution record and
[execution status](../config/completion-execution-status.json) correct that
assumption and retain all failed attempts.

| Job | Stage | Observed result |
| --- | --- | --- |
|25455|Original P0|Rejected unlimited task memory/pids/swap before science;original report preserved|
|25458|Repaired P0|Passed exact 2 GiB memory,64-task and zero-swap limits;preserved Slurm affinity on one physical core|
|25460|P1|All 31 locked packages installed;validation caught a missing pinned Bonsai source directory|
|25461|Repaired P1|Bonsai and synthetic analysis passed;USalign loader required its matching C++ libraries|
|25462|P1 validation repair|Passed using the exact installed environment and matching native libraries;no further installation|

Every submission used the frozen Fleet front door, a fresh submission intent,
an immutable batch body and stored scheduler-script verification. Each repair
followed an observed failure and a specific diagnosis; no automatic retry was
enabled. The previous source, environments, logs and receipts remain intact.

Slurm owns placement. Each job launches one private transient user service
with its saved allocation CPU affinity, a finite runtime, hard memory limit,
64-task limit, zero swap and control-group cleanup. A launcher identity watcher
ends the workload if the original Slurm launcher disappears. The delegated
hierarchy's wider inherited cpuset is recorded honestly; CPU affinity preserves
the job allocation. P0 accepts SMT siblings on one physical core.

Both accepted jobs passed native exit-code checks, separate finished inner and
outer whole-job monitoring checks, and cleanup verification: their services were
inactive and no longer loaded after exit. P1 used two allocated cores, 16 GiB and a
60-minute wall limit. Added staging was 1,191,283,123 bytes and runtime content
1,736,428,136 bytes, within the approved 2 GiB and 8 GiB ceilings; the free reserve
exceeded 50 GiB. No GPU allocation or target-model calculation occurred.

The CPU environment uses 31 exact binary wheel hashes. The original Narwhals
pin 2.27.0 is retained; its upstream yanked flag and stated Pointblank breakage
are recorded in the artifact lock. Pointblank is outside this environment.
No Bonsai dependency installer, shared ProteinEBM environment modification, source
build or external paid API was used.

P1 verified exact installed versions, pinned library/density/Bonsai imports,
32-point synthetic UMAP, two-group synthetic HDBSCAN, finite-pool prior and
fixed-cardinality subset fixtures, and the pinned USalign help. The executable
retains its original relative RPATH and uses hash-bound copies of its matching
Pax C++ libraries; system libraries were unchanged. These checks establish
preparation readiness and do not constitute target scientific acceptance.

Next come P2 native-input and saved-artifact binding, the remaining project
worker adapters and exact execution manifests, then E0 through X0. Target
ProteinEBM coverage, density and MCMC/DISCO remain incomplete. The two held
generation arrays remain held, their finalizer remains dependency-blocked,
and the accepted native dataset and partial atlas are unchanged. Publication
remains held until the complete successor is reviewed.
