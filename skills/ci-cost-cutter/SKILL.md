---
name: ci-cost-cutter
description: Audit a repository's CI, measure a baseline (wall time and compute), find where the time and money go, and cut it in small, verified, reviewable steps without weakening any check. Use this skill whenever someone says CI is slow, expensive or flaky; mentions GitHub Actions minutes, runner bills, queue times, test-suite time, sharding, caching, test selection or "make CI faster/cheaper"; asks to audit or optimize workflows, pipelines or test gates; or shares the OpenClaw CI cost article (vincent.build/openclaw-ci-cost-reduction) — even if they never say "cost". Also use it before deleting, skipping or moving any CI job or test for speed, because it holds the approval rules for that.
---

# CI Cost Cutter

You are auditing someone else's CI and making it cheaper and faster. The method comes from Vincent Koc's write-up of how OpenClaw cut CI runner-hours 86.5% ([article](https://vincent.build/openclaw-ci-cost-reduction/)) and from a later run of the same method on a TypeScript + Go monorepo (see `references/case-study.md`). Their tools and numbers do not transfer as-is; the method does.

The method in one line: **remove work that does not need to run, then make the remaining work cheaper — and prove at every step that the checks still catch what they caught before.**

## Operating principles

Read these first. Each one exists because ignoring it is the usual way this work goes wrong.

1. **Protection is not yours to remove.** A required check, a test, a job or a branch rule protects something the owners care about, even when it looks redundant. You may propose removing or moving it; only a human may approve it (see the gates below). A faster CI that misses a regression is a worse CI.
2. **Measure before you change anything, and measure the same way after.** Record wall time *and* compute (CPU-seconds or runner-minutes) per job. Wall time on shared runners is noisy; compute is more stable. Compare on the same hardware, and alternate before/after runs when the difference matters.
3. **Remove waste before buying speed.** The biggest wins are usually inside the tests (repeated setup, real sleeps, per-process start-up, retries) or in jobs that need not run — not in bigger runners or more shards.
4. **Prove equivalence, not just green.** "It still passes" is not enough. Show the same tests ran with the same results (by test ID), and plant a fault to show a guard still fails when it should.
5. **One lever per commit, with its numbers.** Reviewers must be able to accept or revert each change on its own.
6. **Spend the least agent tokens and CI money that gives a trustworthy answer.** Read history before running anything; profile the top consumer, not everything (see "Budget discipline").

## Human approval gates

Stop and ask before any of these. Explain what you want to change, why, the measured saving, the risk, and how it can be undone. Record the answer in the ledger. "Approve the plan" does not approve a later gate it did not name.

| Gate | Examples |
| --- | --- |
| Remove, skip, disable or weaken a check | delete a job or test, `if:` that skips it, `continue-on-error`, lower a coverage threshold, raise a timeout to hide slowness, add retries |
| Change what a required check means | rename a required job (branch protection then waits forever), change its trigger, move it to nightly or post-merge |
| Select or shard tests by change | any affected-test selection that can run fewer tests than today, even with a fallback |
| Change test semantics | merge tests, change fixtures that tests share, change isolation (processes, DBs), change timeouts or clocks |
| Change runners or spend | runner size/type, self-hosted vs hosted, paid features, caches that cost storage |
| Edit CI configuration at all | `.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`, `buildkite`, branch protection — unless the human already said you may |
| Trigger many CI runs | more than a few runs to measure, or any run on paid runners the human did not expect |
| Push to the default branch, merge, deploy, or touch secrets/permissions | always |

Changes that need no gate: reading anything, measuring locally, profiling, writing the ledger and proposals, and editing test code in a branch when the change keeps every test and its meaning (for example, reusing a fixture that is rebuilt identically each time, or pinning the clock of a test that broke on a date so it checks what it always meant to) — still one commit per lever, still verified.

## When to ask for clarification

Ask (briefly, with your best guess as the default) when:

- The goal is unclear: faster feedback for authors, lower bill, fewer flaky failures, or all three? They pull in different directions (a cheaper runner is often slower).
- You cannot find which checks are required, or who owns a job.
- A job's purpose is unclear (it may guard a release, compliance, or a customer contract).
- Measuring needs money or time the human may not expect.
- Two levers conflict, or a lever needs a policy decision (for example, "full suite only on main").

Do not ask about things you can find yourself in the repo, its docs, or the CI API.

## Budget discipline (time and money)

Your own tokens and the CI runs you start both cost money. Aim each action at the next decision.

**Agent side**
- Read summaries first: workflow files, job lists, durations from the CI API. Grep logs for the lines you need; never read whole logs into context.
- Use history before new runs. Weeks of past runs give a better baseline than one fresh run, at no cost.
- Profile only the top consumers. In most suites 1–5 files or tests hold most of the time; find them (Pareto), then stop.
- Write small scripts for repeated measurement (this skill ships some in `scripts/`) instead of re-deriving numbers by hand.
- Run long measurements in the background and keep working; do not poll in a loop.
- Use subagents only for independent, well-briefed work. Each one starts from zero context.
- Keep a ledger (`assets/CI_LEDGER.template.md`) so a later session resumes without re-measuring.

**Match the effort to the stakes.** For a suite that runs in seconds or a change worth more than 2×, one before/after measurement, the test-ID comparison and one planted fault per guard are enough. Keep A/B alternation, extra rounds and full pipeline runs for small effects, noisy shared runners and changes to gates many people depend on. An audit of a small repo should take minutes, not an hour.

**CI side**
- Measure on the hardware that runs CI. Laptop numbers rank causes; they do not size savings.
- Prefer local or single-job reproductions over full pipeline runs while iterating; run the full pipeline once per batch of changes.
- Cap experiment runs (two alternating runs per variant is usually enough to see a real effect).
- Clean up: temporary branches, caches, artifacts, lane copies, profiling files.

## The workflow

Work through the phases in order. Each phase ends with an output in the ledger. Do not skip ahead to implementation; most wasted effort comes from optimizing the wrong thing.

### Phase 0 — Intake and guardrails

1. Find the CI system and every place CI is defined: workflow files, scripts they call, Makefiles, local runners, pre-commit hooks. **Search for an existing gate or runner script before writing your own** — a second copy of the gate commands is a maintenance trap.
2. List the required checks (for GitHub: branch protection or rulesets via `gh api`; see `references/ci-systems.md`).
3. Ask the human the intake questions you cannot answer yourself: goal, budget for measurement, which branch, whether you may edit CI config, and who must approve gates.
4. Create the ledger from `assets/CI_LEDGER.template.md` and record the answers.

Output: ledger with CI map, required checks, goals and permissions.

### Phase 1 — Baseline

Follow `references/measurement.md`.

1. Pull history: per workflow and job, median and p90 wall time, total runner-minutes (or CPU-seconds), queue time, failure, cancel and rerun rates. `scripts/gha_baseline.py` does this for GitHub Actions. On hosted runners, convert minutes to cost with the runner-type multipliers (macOS and Windows cost more per minute) and the per-job rounding: they often decide where the bill is.
2. If history lacks compute, run the pipeline (or its gates locally) once with CPU accounting (`scripts/measure.sh`).
3. Note the noise: shared runners, other workloads, cold caches. Record the conditions.

Output: baseline table (wall, compute, queue, failure/flake rates) and the top consumers.

### Phase 2 — Diagnose

1. Take the top consumers only. For each, find where its time goes: per test file, per test, per setup step. Language-specific profilers (`go test -json`, `node --test` reporters, `pytest --durations`, CPU profiles) are listed in `references/measurement.md`.
2. Classify each cost with `references/levers.md`: repeated setup, real waits, per-process start-up, retry tax, duplicated work, runner type and matrix, missing cache, wrong stage, work no change needs.
3. Check that every gate covers what its name claims (levers.md 2.6). A gap is a correctness finding: report it first.
4. Check flaky failures: a flake can be a real product bug (see the case study). Read the failure before choosing a fix.

Output: a short list of causes with evidence (numbers, profile lines, file names).

### Phase 3 — Propose

Write the proposal into the ledger: for each lever, the expected saving (wall and compute), the evidence, the risk, the verification plan, and whether it needs a gate. Order by value per risk, not by size alone. Then **stop and get approval** for gated items. Ungated items may proceed, but say what you will do.

### Phase 4 — Implement in reviewable steps

For each lever, in its own branch commit:

1. Make the smallest change that captures the saving.
2. Verify with `references/verification.md`: same test IDs and results before and after; a planted fault still fails; for selection or packing, a fallback that runs the full or isolated set when unsure.
3. Measure the same way as the baseline. Report wall and compute, and say when noise makes wall time unreliable.
4. Commit with the numbers and the verification in the message. Update the ledger.

If a lever does not save what you expected, say so and keep or revert it on its merits. Do not stack unverified changes.

### Phase 5 — Full verification and hand-off

1. Run the full pipeline (or all gates) once on the final commit. Every required check must still run and pass.
2. Write the before/after table, what you did not do and why, and how to maintain the changes (timing files to refresh, isolation lists, notes the gates print). Update the repo's own docs where people will look.
3. Ask before merging or pushing to the default branch.

## Reference map

| Read | When |
| --- | --- |
| `references/levers.md` | Phase 2–4: the catalog of causes and fixes, with detection signals and risks |
| `references/measurement.md` | Phase 1–2: how to measure wall, compute, queue and noise; profilers per language |
| `references/verification.md` | Phase 4: equivalence by test ID, planted faults, A/B alternation, shadow mode |
| `references/test-selection.md` | Before any change-based selection, stage move or sharding |
| `references/ci-systems.md` | GitHub Actions, GitLab CI and self-hosted specifics, required-check traps |
| `references/case-study.md` | A worked example: what was found, the numbers, the mistakes |
| `references/article-notes.md` | The source article's practices in short, and what does not transfer |

## Scripts

| Script | Use |
| --- | --- |
| `scripts/gha_baseline.py` | GitHub Actions history: per workflow and job, median/p90 duration, runner-minutes, queue, failure and cancel rates (needs `gh`) |
| `scripts/measure.sh` | Run commands with wall and CPU accounting; alternate variants A/B for fair comparisons |
| `scripts/junit_compare.py` | Compare two JUnit result sets by file and test name; fails on any difference |
