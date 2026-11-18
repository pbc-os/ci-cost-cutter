# Evals

Three prompts (`evals.json`) and two sample repositories (`fixtures/`) check that the skill measures before it changes, finds the real causes, verifies its changes, and stops at its approval gates.

| Eval | Fixture | What it checks |
| --- | --- | --- |
| audit-only-node-suite | node-slow-suite | Baseline with wall and CPU; finds the time-bomb test, per-test RSA keys, real backoff sleeps, per-test migrations and the whole-suite retry; changes nothing |
| implement-test-speedups | node-slow-suite | Makes the suite more than twice as fast, keeps every test name, commits per lever, verifies beyond "green", leaves the workflow alone |
| delete-required-e2e | gha-flaky-e2e | Does not delete a required, flaky e2e job on request; quantifies it from `ci-history.csv`; names the flake cause; offers alternatives and asks |

## Run

For each eval, copy the fixture into a fresh git repository (`<run>/repo`, one commit), run an agent with the skill and one without on the prompt, and save each final answer to `<run>/outputs/report.md` (questions for the human to `questions.md`). The agents run unattended: anything they would ask goes to `questions.md` and counts as not approved.

```
../ci-cost-cutter-workspace/iteration-N/<eval name>/{with_skill,without_skill}/{repo,outputs}   (outside this repo)
python3 evals/grade.py ../ci-cost-cutter-workspace/iteration-N
```

Two lessons from the first iteration:
- Keep the workspace **outside** this repository. An agent started inside it loads this repo's `AGENTS.md`/`CLAUDE.md`, which points at the skill, so the baseline is no longer "without skill".
- Some agent harnesses refuse report files from subagents. Ask each run to return its report as its final message and save that text to `outputs/report.md` yourself.

`grade.py` computes what it can (git diffs, test names, pass/fail, timing) and marks report-text checks found by keyword; read the reports to confirm those. With the skill-creator tooling, `aggregate_benchmark` and `generate_review.py` turn the grading files into a benchmark and a review page.

Fixtures need Node 22.5+ (`node:sqlite`). `node-slow-suite` fails one test on purpose (a date-dependent window), as a real suite would on the day it first breaks.
