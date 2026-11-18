# CI ledger — <repository>

Kept by the agent running the ci-cost-cutter skill. One file per campaign; a new session reads it before doing anything.
Commit it on the working branch (or keep it beside the repo if the owners prefer).

## 0. Intake

- Date started:
- CI system(s) and where CI is defined (files, scripts, runner hosts):
- Existing gate/runner scripts found (do not duplicate them):
- Required checks (source: branch protection / rulesets / docs):
- Goal (faster feedback / lower bill / fewer flakes — in the human's words):
- Measurement budget (runs and money the human accepts):
- Permissions: may edit tests [yes/no], may edit CI config [yes/no], may trigger CI runs [how many], who approves gates:
- Branch for the work:

## 1. Baseline

Conditions: machine/runner, cores, load, cache state, commit, date.

| Job / gate | runs (n) | wall median | wall p90 | compute | fail % | notes |
| --- | --- | --- | --- | --- | --- | --- |

History window: … runs over … days; queue total …; top consumers: 1. … 2. … 3. …

## 2. Diagnosis

| Consumer | Where the time goes (evidence) | Cause (levers.md) |
| --- | --- | --- |

## 3. Proposal

| # | Lever | Expected saving (wall / compute) | Evidence | Risk | Verification | Gate? | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 4. Approvals

| Date | Gate | What was approved (human's words) | By |
| --- | --- | --- | --- |

## 5. Steps

For each step: commit, change, verification (test IDs compared, planted fault and result), measurement (before / after, conditions).

### Step N — <lever>
- Commit:
- Change:
- Verification:
- Measured:

## 6. Result and hand-off

| Job / gate | before (wall / compute) | after (wall / compute) |
| --- | --- | --- |

- Not done, and why:
- How to maintain (files to refresh, lists to extend, notes the gates print):
- Docs updated:
