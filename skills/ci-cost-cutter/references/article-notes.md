# Source: "Making CI faster and 95% cheaper" (OpenClaw)

Vincent Koc, November 2026: https://vincent.build/openclaw-ci-cost-reduction/ — read the original for the data, charts and the OpenClaw implementation links. This is a short paraphrase of its practices, as this skill uses them.

## Reported results (their repository, their workload)

- Weekly runner-hours down 86.5% (September peak week vs a November week); estimated compute value down 95.5%.
- The workload changed too (fewer commits), so the article does not attribute the saving to any single fix, and it does not claim a faster PR-to-merge time.

## The practices

1. **Delete the waste before optimizing it.** Agent-grown suites accumulate tests that restate the implementation. Each test should protect a named behavior; keep the strongest test per contract; prove the survivor still catches a planted bug. A budget on test-code growth makes growth visible and exceptions explicit.
2. **Run checks at the right stage.** Separate the answer needed to merge from broader proof for a release; run full validation on a schedule against a named revision; never treat an old green run as proof for a newer commit.
3. **Stop paying for the same review twice.** Automated reviews run once per PR and again on request, not on every push; local review tools avoid allocating runners.
4. **Test what changed.** A deterministic planner maps the diff to owning tests and importers, adds fixed smoke and policy checks, and widens to the full suite when unsure. Learned models run only in shadow mode: they record predictions and never skip tests.
5. **Catch cheap failures locally; use faster tools on the checks authors wait for.** Formatting, lint and focused tests before the remote round trip; faster type checkers where compatible, with the old tool kept for release validation.
6. **Stop rebuilding the same environment.** Fetch less (blobless clones), make cache hits real, restore only what a job needs, reuse an expensive runtime across test files where tests reset their state.
7. **Pack, balance and size the remaining work.** Sharding is not parallelism. Too many shards repeat setup; uneven shards wait for the slowest. Size runners to the work: a cheaper runner can make everyone wait longer.

Their recurring caution: every optimization needs a tradeoff check of cost against waiting time, and a smaller green run does not prove that selection is correct.

## What did not transfer to the case study

- Their tools (Blacksmith runners, Vitest-specific planners, tsgo/tsrs) did not apply; the repo used Node's built-in test runner, Go, and one self-hosted machine.
- Change-based selection was not worth it after setup fixes: the remaining per-gate cost was small.
- A faster type checker had little value: type checking took 17 s.
- The largest wins were inside test setup (practice 6 applied to fixtures, not CI caches), which the article mentions only briefly.
