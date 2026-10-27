# Architecture decisions

## DuckDB and dbt

DuckDB keeps this single-source analytical workload easy to reproduce without a warehouse account. dbt supplies the dependency graph, model descriptions, tests, and execution artifacts. A distributed platform would add operations without an evidenced workload need.

Raw models preserve the source projection. Silver types values and classifies row quality without dropping records. Golden models serve named metrics. The dashboard filters the accepted silver records so all charts respond to the same selection; golden aggregate models remain independently reconciled outputs.

## Publication and recovery

Each build uses an isolated database and output directory. After validation and export, an immutable run directory is copied into place, then a pointer file is atomically replaced on the same filesystem. A failed acquisition, dbt execution, or export leaves the previous pointer intact. The test suite injects a dbt failure to verify this boundary.

This is a local single-writer workflow. Concurrent builds are unsupported. Immutable runs consume disk until manually removed; do not remove the current run. A production deployment would need retention, access controls, scheduling, monitoring, and a cloud-specific publication mechanism.

## Data interpretation

The current source is a population snapshot. Grouping by model year does not establish historical registrations or sales. Dated snapshots could support changes in the observed population, but those changes would still need interpretation: moves, corrections, and removals can affect totals.

The source projection omits vehicle IDs. We count records without claiming deduplication. Missing location is not grounds to exclude an otherwise usable vehicle. Zero range is classified as unreported/unknown rather than a claim of zero capability.

## Reproducibility and dependencies

The synthetic fixture is small, deterministic, and visibly labeled. CI builds it without secrets or live-source availability. `requirements.txt` declares direct dependency bounds; `requirements.lock` pins the tested transitive environment for installs, CI, and Docker. The lock was generated on Python 3.13 and CI checks Python 3.12. Refresh it deliberately and rerun validation when upgrading. Source HTTP requests have timeouts and fail on unsuccessful status codes. No automatic retry policy or source-snapshot scheduling is implemented.

## Deployment status

The repository's prior AWS push workflow is replaced by PR validation. Optional raw S3 upload and the dbt S3 profile remain available, but the new dashboard consumes local validated runs. No live AWS resources or Streamlit deployment are changed by this PR.
