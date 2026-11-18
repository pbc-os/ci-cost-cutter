# Test selection, stages and sharding

Read this before any change that makes a check run fewer tests, run later, or run in a different shape. All of these are gated (SKILL.md): propose with numbers, get approval, verify in shadow mode first.

## Is it worth it?

Do the cheaper levers first (setup, waits, start-up, retries). Then estimate the remaining saving: the share of runs whose diff touches only part of the suite × the time of the part that would be skipped. In the case study, after the other levers, half of all changes touched the Go inputs and the Go gate cost ~45 s, so gate-level selection for it was not worth its risk.

## Rules for a selector

1. **Deterministic.** The same diff and rules give the same selection. No model may skip a test on its own confidence.
2. **Inspectable.** Every selected test has a reason (owner, import, fixture, policy, smoke).
3. **Widen when unsure.** Missing dependency data, a deleted or renamed file, a shared helper, config, lockfiles, CI files, fixtures read from disk, or anything unmapped → run the full set. A missing record is a reason to run more, never evidence that nothing can break.
4. **Keep what the diff cannot remove.** Smoke tests, policy checks and required checks always run.
5. **Full suite somewhere.** Main, a schedule, or the release gate runs everything on the revision that ships, and failures reach a person.
6. **An off switch.** One setting returns to full runs without code changes.

## Building it

1. Start from the exact diff: additions, deletions, renames, and the base revision.
2. Map changed files to tests: owner rules, sibling tests, reverse imports (follow package aliases), and declared file inputs (fixtures, JSON, SQL). An import graph does not see files read from disk; record them (Go's test log lists opened files; Vitest has `addWatchFile`; otherwise declare them).
3. Language boundaries are a cheap first selector: a TypeScript-only diff need not start the Rust or Go job, *if* the input lists of each language are exact and shared or unknown files keep both.
4. Hand the selection to the existing runner; reject the plan (run full) if a selected file has no runner configuration.

## Proving it

- Shadow mode: run everything, record what the selector would have run, count misses (`verification.md`).
- Backtest: replay past failing changes; the failing test must be selected.
- Planted fault: break a fixture a test reads from disk; the test must be selected and fail.

## Stages

- Before merge: what this change needs to be safe (selected tests, lint, types, security, review).
- On each push to main: small guards that catch immediate breakage.
- Scheduled: broad validation of a named revision (full matrix, long E2E), with results kept and failures routed to an owner.
- Release: the full required set on the exact revision being shipped.

Moving a check between stages changes when its answer arrives, not whether it is required. Make the stage explicit in the ledger and in the repo's docs.

## Sharding

Sharding splits work; parallelism decides how much runs at once. Pack enough work per shard to pay for its setup, balance by measured time, and keep one shard per known-heavy item. Re-measure after other fixes: shard plans go stale.
