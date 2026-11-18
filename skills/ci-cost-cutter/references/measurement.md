# Measurement

Measure so that a decision follows. Record every number with its conditions (machine, load, cache state, commit) in the ledger.

## What to measure

| Measure | Why | Where from |
| --- | --- | --- |
| Wall time per job/gate (median, p90) | What authors and agents wait for | CI API history; `scripts/measure.sh` |
| Compute per job/gate (runner-minutes or CPU-seconds) | What it costs; more stable than wall time on shared machines | Hosted: billed minutes × runner size. Self-hosted: `getrusage` of the job's processes (`/usr/bin/time`, `scripts/measure.sh`) |
| Queue time | Waiting for a runner; faster tests do not fix a queue | CI API (created → started) |
| Failure, cancel and rerun rates | Retries and superseded runs cost money too | CI API; job conclusions |
| Flake rate per test | Retry tax and hidden bugs | Logs: tests that failed then passed on retry |
| Per-file and per-test time | Where inside a job the time goes | Test reporters (JUnit, JSON) |

Wall time vs compute: a job using 6 cores for 400 s costs ~2,400 CPU-seconds. Packing or caching can cut compute while wall time stays flat, and splitting files can cut wall time while compute stays flat. Report both.

## History first (free)

GitHub Actions:
```bash
python3 scripts/gha_baseline.py --repo OWNER/REPO --days 14 --branch main      # per workflow and job
python3 scripts/gha_baseline.py --repo OWNER/REPO --days 14 --event pull_request
```
It prints median/p90 duration, summed job minutes, queue time, and failure/cancel rates. Job minutes on hosted runners are billed per job, rounded up per minute, times the runner's multiplier; the script reports raw minutes, so apply the price table for the runner types used.

GitLab: `GET /projects/:id/pipelines` and `/pipelines/:id/jobs` give `duration` and `queued_duration`. Jenkins, Buildkite and others have equivalents; self-hosted runners may only keep logs, so grep their `RESULT`/timing lines.

## New measurements (cost money or time)

```bash
# one command, wall + CPU (children included), 1 run:
scripts/measure.sh -n 1 -- npm test
# alternate two variants, 2 rounds each, CSV out:
scripts/measure.sh -n 2 -o ab.csv -a "git checkout -q before && npm test" -b "git checkout -q after && npm test"
```
- Run on the CI hardware when sizing savings. A loaded laptop ranks causes; it does not size them.
- Alternate A and B (A1 B1 A2 B2). Running all A then all B confounds the change with load drift.
- Note load (`uptime`) before each run; on shared runners, compare CPU-seconds, not wall time.
- CPU accounting through `getrusage(RUSAGE_CHILDREN)` counts only processes the job waited for; daemons (a Docker VM, a browser left running) are invisible. Say so when it matters.

## Profiling inside a job

| Stack | Per-file / per-test time | CPU profile |
| --- | --- | --- |
| Node `node:test` | `--test-reporter=junit --test-reporter-destination=out.xml` (testcase has `file` and `time`) | `node --cpu-prof`; for imports: `--cpu-prof -e "await import('…')"` |
| Vitest / Jest | `--reporter=junit`, `--reporter=json` | `--cpu-prof` on the worker |
| Go | `go test -json` (Elapsed per test and package) | `go test -cpuprofile` then `go tool pprof -top -cum` |
| pytest | `--durations=50`, `--junitxml` | `py-spy record`, `-p cProfile` |
| Browser tests (Playwright etc.) | per-test durations from the reporter | count page loads per test; check asset caching |

Read profiles for three patterns:
- **Low CPU, high wall** → waiting (sleeps, backoff, timeouts, I/O).
- **Same setup in every test** → repeated setup (migrations, keys, rendering).
- **High cost before the first test** → per-process start-up (imports, transpiling).

## Baseline table (put this in the ledger)

```
Machine: <runner type or host>, <cores>, load <x> during run; commit <sha>; caches <warm/cold>
| Job/gate | runs (n) | wall median | wall p90 | compute | fail % | notes |
```
And the history window: dates, number of runs, queue total, top 3 consumers by compute.
