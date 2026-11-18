# Verification

A faster check is only better if it still catches what it caught before. Prove three things for every change.

## 1. Same tests, same results

Compare the set of test IDs and outcomes before and after, not only the pass/fail count.

```bash
# before (old commit or old mode) and after, both with JUnit output:
node --test --test-reporter=junit --test-reporter-destination=before.xml 'test/*.test.ts'
# ... switch to the change ...
node --test --test-reporter=junit --test-reporter-destination=after.xml  'test/*.test.ts'
python3 scripts/junit_compare.py before.xml after.xml          # exit 1 on any difference
python3 scripts/junit_compare.py before.xml after-dir/          # a directory of XML files (shards) is merged
```
The script keys each result by (file, test name). It reports cases only in one side, cases whose outcome differs, and per-file time. Expected differences (tests you added on purpose) should be listed in the commit message.

For Go, compare `go test -json` outputs: the set of (package, test, action) for pass/fail/skip.

## 2. A planted fault still fails

For each guard you rely on, break the thing it guards and watch it fail, then restore:
- A shared fixture: remove one refresh step from the copy → the guard test must fail.
- A changed setup (shared key): make the verifier use a different key → the dependent tests must fail.
- A retry change: a test that fails on its first run only → PASS with a note naming it; a test that always fails → FAIL.
- A packing change: a file that leaks global state into the next → PASS with a note; a file that always fails → FAIL.
- A regression test you add for a bug: run it on the old code → it must fail.

Keep the probe files out of the repo (create, run, delete), and say in the commit message what you planted and what happened.

## 3. A fair performance comparison

- Same machine, same commit apart from the change, same cache state.
- Alternate variants (A1 B1 A2 B2) on shared machines.
- Report compute and wall; say when load made wall time unreliable.
- One or two rounds per variant is usually enough for effects over ~10%; smaller effects need more rounds or are not worth the change.

## Shadow mode (before any selection skips tests)

When a change would run fewer tests (selection, sharding by change, moving to nightly): run the full set anyway, record what the new rule *would* have run, and count misses (a failing test the rule would have skipped). Only after enough independent failures with zero misses may the rule skip anything — and that is a human decision. With zero misses in N independent faulty changes, the 95% upper bound on the miss rate is about 3/N (30 → 10%, 100 → 3%, 300 → 1%).

Backtest too: take past failing runs, replay their diff through the rule, and check the failing test would have been selected.

## Noise and honesty

- Report what you measured, including changes that did not help (in the case study, a UI-gate change cut wall time 28% and compute 0%).
- Do not claim a saving from one run on a noisy machine.
- Keep raw numbers (CSV, JUnit files) until the change is merged.
