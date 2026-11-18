# Levers: causes of CI cost and how to remove them

Each lever has: the signal that points to it, the fix, how to verify, the risk, and whether it needs a human gate (see SKILL.md). Work from evidence: find the signal in your measurements before you apply a lever.

Contents
1. Work inside the tests (usually the biggest)
   1.1 Repeated expensive setup · 1.2 Real waits · 1.3 Per-process start-up · 1.4 Retry tax and flaky tests · 1.5 Time bombs
2. Work around the tests
   2.1 Duplicated work · 2.2 Missing or useless caches · 2.3 Oversharding and imbalance · 2.4 Serial gates that could overlap · 2.5 Runner type, size and matrix · 2.6 Checks that cover less than they claim
3. Work that need not run now
   3.1 Superseded runs · 3.2 Wrong stage · 3.3 Change-based selection · 3.4 Low-value tests
4. Order of attack

---

## 1. Work inside the tests

### 1.1 Repeated expensive setup

**Signal.** Many tests each take a similar, non-trivial time (for example 0.5 s each over hundreds of cases); a CPU profile of one test is dominated by setup — schema migrations, key generation, fixture rendering, container start, data seeding.

**Fix.** Build the expensive state once per process (or once per run) and give each test its own *copy*:
- Databases: run migrations once, then copy (SQLite `serialize`/`deserialize` or a template file; Postgres `CREATE DATABASE … TEMPLATE`; transactions rolled back per test).
- Crypto keys, certificates: one per process (`sync.OnceValue` in Go, a module-level promise in JS) when no test compares two keys.
- Rendered fixtures, parsed data files: cache the result, hand out deep copies (`structuredClone`) so a test that mutates its copy affects no other test.

**Verify.** The copy must equal a fresh build: same schema, same rows, same settings. Watch for values the setup takes from the clock or random sources (a seed row with `now()`), and connection-level settings that are not part of the copied bytes (SQLite `PRAGMA`s). Write a guard test that compares a copy with a fresh build and fails when a new setup step breaks the equivalence. Plant a fault (remove one refresh) and see the guard fail.

**Risk.** Shared mutable state between tests. Copies avoid it; shared objects do not.

**Gate.** None if every test keeps its meaning and gets a fresh copy. Gate if tests start sharing state.

**Case study.** Copying one migrated SQLite database instead of running 96 migrations per fixture cut a gate's test time from 2,770 s to 721 s with identical results.

### 1.2 Real waits

**Signal.** A test's wall time is high but its CPU time is near zero (a CPU profile shows a few percent busy). Typical causes: retry backoff with real sleeps (1+2+4+8+16 s), polling loops, fixed `sleep`s, network timeouts against nothing.

**Fix.** Inject the clock or sleeper (most retry libraries take one) and use a no-op or recording sleeper in tests. If you record the delays, the test can still assert the backoff schedule without waiting for it.

**Verify.** The same outcome is asserted. Check that the backoff schedule itself is covered somewhere (often in the client library's own tests). Watch for the case where the test replaces the client after your injection point — set the sleeper after the object is final.

**Gate.** None when the waited-for behavior keeps a test elsewhere; otherwise ask.

### 1.3 Per-process start-up

**Signal.** Many small test files, each in its own process; the sum of per-file wall time is far above the sum of test durations; a profile of an empty import shows module loading, transpiling (TypeScript type stripping, Babel, ts-node) or JIT warm-up dominating.

**Fix.**
- Pack files into a few long-lived processes (Node `--test-isolation=none`, Vitest `isolate: false` per lane, pytest-xdist workers, Jest `--runInBand` per shard), balanced by measured per-file time (longest first to the lightest worker).
- Keep files that need a fresh process in an explicit isolation list (module-load tests, global state they own).
- If a packed process fails, rerun its files one process per file and let that result decide. A failure that only appears packed is a state leak, not a product bug; name the files so they join the isolation list.
- Compile caches (Node `NODE_COMPILE_CACHE`, Python bytecode) are cheap to try but often save little (8% in the case study); measure.

**Verify.** Compare JUnit results by file and test name, packed vs isolated: same set, same outcomes. Plant two probes: a file that leaks global state into the next (expect PASS with a note) and a file that always fails (expect FAIL).

**Risk.** A packed *pass* does not prove a file passes alone (state from an earlier file can mask a bug). Keep the isolated mode for the pre-merge train or the release gate.

**Gate.** Yes (changes isolation). Propose with numbers: in the case study, packing cut CPU by 42–57% per gate.

### 1.4 Retry tax and flaky tests

**Signal.** A job reruns the whole suite on failure (`npm test || npm test`, `retry: 2` at job level), or failure rates show intermittent failures of one test.

**Fix.**
- Rerun only the failed tests (`node --test-rerun-failures`, `pytest --lf`/`--reruns`, Go: rerun failing packages), and print the names of tests that passed only on a retry, so flakes stay visible.
- Read every flaky failure before choosing a fix. A flake can be a real product race (in the case study, a dialog that closed itself on slow devices). Fix the cause and add a deterministic test that reproduces the slow path (for example, slow the animation down so the fallback timer always wins).

**Gate.** Changing retry policy changes what passes: gate it, and show the before/after for a planted first-run failure.

### 1.5 Time bombs

**Signal.** A test fails on every branch from a certain date, with no code change; it reads "now" and compares with fixed data.

**Fix.** Pin the time window in the test (pass explicit dates) or inject the clock. Fix it first: it blocks every other measurement.

## 2. Work around the tests

### 2.1 Duplicated work
The same build, install, lint or test runs in several jobs, or two tests check the same contract with the same setup (for example, three page sweeps that each load every page at overlapping widths). Build once and share artifacts; merge duplicate *loads* but keep each contract as its own named check. Merging tests changes semantics: gate it.

### 2.2 Missing or useless caches
A configured cache whose restore never hits, keys that change every run, caches that restore more than the job needs, or test servers that send assets without cache headers (a browser then refetches fonts on every page load). Check the restore result and the time still spent installing. Keys must match lockfile, toolchain and platform. Never let an untrusted job write a cache others restore.

### 2.3 Oversharding and imbalance
Many small shards each repeat checkout, install and start-up; or one shard holds the longest file and everyone waits for it. Pack enough work into each shard to pay for its setup, then balance by measured time. More shards is not always better; the case study's longest single file set the floor for the whole gate until its setup was fixed.

### 2.4 Serial gates that could overlap
A single file that runs its slow tests one after another sets the job's wall time while other workers idle. Split the slow tests into their own file so the runner runs them in parallel. Saves wall time, not compute.

### 2.5 Runner type, size and matrix
- **Multipliers first.** On hosted runners, billed minutes are multiplied by runner type (GitHub: Linux 1×, Windows 2×, macOS 10× on standard runners; check the current table). A matrix of 3 OS × 2 versions can put three quarters of the bill in the macOS and Windows cells. Ask which cells must pass *before merge*; the others can run on main or a schedule with an alert (gated: it changes when an answer arrives). Keep required job names unchanged.
- **Size.** A serial job gets nothing from 32 cores; a memory-heavy job needs the big machine even when its CPUs look idle. A smaller runner can cost less and take longer (the article's example: 41.7% cheaper, 16.5% slower). Present both numbers; the human chooses. Gate.
- **Rounding.** Hosted jobs bill whole minutes. Shaving a 50 s job to 20 s saves no money; merging tiny jobs or removing them does. Faster tests then help feedback time, not the bill — say which one a change improves.

### 2.6 Checks that cover less than they claim
While reading the gates, check that each one tests what its name says. Common gaps: `node --check a.mjs b.mjs` checks only the first file (the rest are arguments), an unquoted glob that matches nothing, a test command whose pattern skips a folder, `|| true`, a step that never fails. These are correctness findings, not savings: report them first, with a one-line proof (a planted bad file that still passes), and propose the fix (CI edit: gated).

## 3. Work that need not run now

### 3.1 Superseded runs
Pushes that start a run the next push cancels: use concurrency groups with cancel-in-progress for branches (not for the default branch or releases without asking), or a short admission delay before expensive jobs.

### 3.2 Wrong stage
Separate what must answer before merge from broader proof that can run on main on a schedule (full matrix, long E2E). A moved check still runs; keep its result tied to the revision that ships, and make sure someone is notified when it fails. Gate: it changes when an answer arrives.

### 3.3 Change-based selection
Run the tests a change can affect; widen to the full set when the mapping is uncertain. See `test-selection.md`. Gate. Measure first whether it is worth it: after the levers above, the remaining saving is often small and the risk is not.

### 3.4 Low-value tests
Agent-written suites grow tests that restate the implementation. Cleaning them up is real work: read the code, name the contract each test protects, keep the strongest test per contract, plant a fault to prove the survivor catches it. Never delete the only test of a contract. Always gated; propose as a separate campaign with its own ledger.

## 4. Order of attack

1. Time bombs, broken checks and checks that cover less than they claim (nothing else can be measured reliably while they fail, and a gap is a correctness problem).
2. Repeated setup, real waits (large, low risk, no semantics change).
3. Retry tax and flaky causes.
4. Per-process start-up (packing), caches, duplicated loads, overlap.
5. Stage moves, runner sizes, change-based selection, test cleanup (each gated, each a decision for the human).

Re-measure after each step: an earlier fix often changes what is worth doing next (in the case study, fixing setup made the biggest single file fall from 391 s to 33 s, which removed the reason to split it).
