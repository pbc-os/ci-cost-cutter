# Case study: a TypeScript + Go monorepo on one self-hosted machine

One afternoon of agent work, November 2026. Names and product details are left out; the numbers are as measured.

## Setting

- A TypeScript service (about 400 Node test files: ~3,500 + ~1,550 tests, built-in `node:test` with type stripping), a browser UI suite (Playwright, 8 files), and a Go service (~2,750 tests).
- Nine gates ran in sequence on one 8-core self-hosted machine shared with other projects' CI, two gate runs at a time. Hosted CI was off by choice.
- Gate commands lived in a JSON list in the repo, read by a runner script — and also, by accident, in an older copy on the runner host.

## Baseline

One full run: 1,234 s wall, 3,771 CPU-seconds. History (371 runs over three weeks): median 929 s, p90 1,334 s; a third of runs waited for a slot, 42 hours of queue in total. Three gates held 90% of compute: the Node service tests (2,335 s CPU), the UI tests (663 s), the Go tests (410 s).

## What was found and done, in order

| # | Finding | Fix | Result |
| --- | --- | --- | --- |
| 1 | Two tests failed on every branch since a date: their data sat outside a "last 30 days" default window | Pin the window in the tests | Unblocked every other measurement |
| 2 | One Go test took 260 s: every test server generated a new 2048-bit RSA key (82% of CPU) | One key per test process; planted key mismatch fails 14 subtests | Go package 429 s → 42 s |
| 3 | Two Go tests waited 31 s each: real exponential backoff on a 429 with no Retry-After | Inject the existing no-op sleeper (after the test replaced the client) | 34 s → 4 s, 31 s → 0.2 s |
| 4 | A UI test failed in 4% of runs on the loaded machine; the suite then reran entirely | Read the failure: a real bug — a stale `animationend` listener closed a reopened dialog on slow devices. Fixed the product code; added a deterministic slow-device test that failed on the old code. Rerun only failed tests, and name them | Bug fixed in production; a rerun costs 37 s instead of a whole suite |
| 5 | Every database fixture ran 96 migrations (0.7 s); one file made 661 fixtures | Build once per process, copy with SQLite serialize/deserialize; re-apply connection PRAGMAs and the two clock-based seed rows; guard test compares with a fresh migration | Node tests 2,406 → 847 s CPU, 469 → 165 s wall; identical results |
| 6 | ~1.3 s CPU per test process just to load and type-strip sources, 400 processes | Pack files into 5 processes; 9 files that need a fresh process stay isolated; a failed packed process reruns one-per-file and decides; release keeps isolated mode | A further 42–57% CPU per gate; identical JUnit results |
| 7 | UI tests rendered fixtures up to 9 times; test servers sent assets without cache headers; one file ran 260 s serially | Render once per process (deep copies); Cache-Control on assets; split two sweeps into their own file | UI wall −28%; UI compute unchanged (the gain in one sweep was eaten by the extra process) |

End state: a lane run ≈ 1,300 CPU-seconds (from 3,771), about −65%, every check still running, results identical by test ID.

## Mistakes worth learning from

- **A second copy of the gate commands.** The first step wrote a new gate script before finding the repo's existing gate list. It was reverted and the change moved into the existing list. Search first.
- **Profiling on a loaded laptop.** Good for ranking causes, wrong for sizing them. Final numbers came from the CI machine.
- **Wall time on a shared machine.** Load averages of 25–49 from another project's VM made wall times swing ±50%. CPU-seconds and A/B alternation gave stable answers.
- **New packing groups expose new leaks.** A rebalanced grouping put a file after a different neighbor and two of its 661 cases failed packed. The one-per-file fallback kept the gate correct; the file joined the isolation list. Keep groups stable (committed timings) and keep the fallback.
- **A mixed commit.** One commit removed tests from a file before the file that received them was committed. Check `git show --stat` before each commit when a change moves code between files.

## What was not done (and why)

- Change-based selection: after the fixes the remaining gate costs were small; the risk was not.
- Merging the three overlapping UI page sweeps: it would cut page loads but change what the tests check; left as a proposal for the owners.
- More runner slots: two runs already saturate the machine at peaks.
