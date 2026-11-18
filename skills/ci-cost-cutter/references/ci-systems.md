# CI system specifics

## GitHub Actions

**Required checks.** Find them before changing anything:
```bash
gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.contexts, .required_status_checks.checks'
gh api repos/OWNER/REPO/rulesets --jq '.[] | {id,name,enforcement}'
gh api repos/OWNER/REPO/rulesets/ID --jq '.rules[] | select(.type=="required_status_checks")'
```
(403/404 means you lack admin rights or there is no protection: say so and ask the human.)

**Traps that break merges or hide failures**
- Renaming a required job, or a matrix that changes its display names, leaves branch protection waiting for a check that never reports. Gate.
- `paths:` / `paths-ignore:` on a workflow with a required check: when the workflow is skipped, the required check never reports and PRs stay blocked. Use a job-level condition that still reports success, or a separate always-on summary job — and ask first.
- `continue-on-error: true` and `|| true` turn failures into passes. Never add them for speed.
- `if: github.event_name == 'push'` on a test job silently removes it from PRs.

**Savings with low risk (still propose before editing workflow files)**
- `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }` on PR workflows (not on main or release workflows without asking).
- Caches: `actions/setup-node` / `setup-go` / `setup-python` built-in caching keyed by lockfile; check the restore hit in the job log ("Cache restored from key").
- `timeout-minutes` on every job (a hung job bills until the 6-hour limit).
- Fetch depth: `fetch-depth: 1` unless the job needs history; a blobless clone (`filter: blob:none`) when it needs the merge base.
- Matrix: does every OS × version cell catch something the others do not? Propose trimming PR matrices and keeping the full matrix on main or a schedule (gated).

**Billing.** Hosted runner minutes are rounded up per job and multiplied by the runner type (larger Linux runners, macOS and Windows cost more per minute). Public repos on standard runners are free; self-hosted runners cost the machine. Check the current price table for the plan; do not guess.

## GitLab CI

- Required checks: merge request approval rules and "Pipelines must succeed"; `rules:changes` has the same skipped-pipeline trap as `paths:`.
- `interruptible: true` plus auto-cancel redundant pipelines replaces superseded runs.
- `cache:key:files:` keyed by lockfiles; `needs:` for DAG ordering instead of stages; `parallel:` for sharding.

## Self-hosted and local runners

- Compute is the machine's time: measure CPU-seconds with `getrusage`, watch slot contention and other workloads on the same host.
- Per-lane or per-branch working copies change absolute paths; toolchain caches keyed by path (Go's test cache, some compilers) then miss across lanes. A stable work path per slot restores hits.
- Two gate runs at once on a small machine double wall time; a slot limit is a queue. Record queue waits.
- Keep the gate commands in the repository (one list), not only on the runner host: they then change with the code and get reviewed.

## Any system

- Find the one place gate commands live before adding another.
- Put per-gate CPU time in the gate output; it makes cost visible in every run.
- Print a short note when a retry or a fallback changed the outcome, so nobody mistakes it for a clean pass.
