# ci-cost-cutter

An agent skill that audits a repository's CI and cuts its time and compute cost in small, verified steps — without weakening any check, and asking a human before anything that could.

It packages a method: measure a baseline, find where the time and money actually go, remove work that does not need to run, make the rest cheaper, and prove at every step that the checks still catch what they caught before. The method comes from Vincent Koc's write-up [Making CI faster and 95% cheaper](https://vincent.build/openclaw-ci-cost-reduction/) (OpenClaw) and from a later run on a TypeScript + Go monorepo, where it cut CI compute by about 65% with identical test results ([case study](skills/ci-cost-cutter/references/case-study.md)).

## What the agent does

1. **Intake.** Maps the CI (workflows, scripts, runner hosts), finds the required checks, and asks you about goals, budget and permissions.
2. **Baseline.** Reads CI history first (free), then measures wall time *and* compute per job.
3. **Diagnose.** Profiles only the top consumers and classifies each cost: repeated setup, real waits, per-process start-up, retry tax, duplicated work, caches, oversharding, wrong stage.
4. **Propose.** A ranked list with expected savings, evidence, risk and a verification plan, then waits for your approval of anything gated.
5. **Implement.** One lever per commit. Each is verified (same tests by ID, same outcomes, a planted fault still fails) and measured.
6. **Hand off.** Before/after table, what it did not do and why, and how to maintain the changes.

It keeps a ledger (`CI_LEDGER.md`) so a later session can resume without re-measuring.

## Safety: what it will not do without you

The agent stops and asks before it:
- removes, skips, disables or weakens any check, job or test (including retries, `continue-on-error`, raised timeouts);
- renames or re-triggers a required check, or moves a check to another stage (nightly, post-merge);
- adds change-based test selection or changes test isolation or semantics;
- changes runner types or anything that costs money, or triggers more than a few CI runs;
- edits CI configuration (unless you said it may), pushes to the default branch, merges, deploys, or touches secrets.

The full list and the reasons are in [SKILL.md](skills/ci-cost-cutter/SKILL.md#human-approval-gates).

## Install

**Claude Code (plugin):**
```
/plugin marketplace add pbc-os/ci-cost-cutter
/plugin install ci-cost-cutter@ci-cost-cutter
```

**Claude Code (skill folder):**
```bash
git clone https://github.com/pbc-os/ci-cost-cutter
cp -r ci-cost-cutter/skills/ci-cost-cutter ~/.claude/skills/            # for every project
# or: cp -r ci-cost-cutter/skills/ci-cost-cutter <your-repo>/.claude/skills/   # one project
```

**Codex, Cursor and other agents:** clone the repo next to your project and point the agent at `skills/ci-cost-cutter/SKILL.md` (for example, add to your `AGENTS.md`: "For CI speed or cost work, follow ../ci-cost-cutter/skills/ci-cost-cutter/SKILL.md"). The references and scripts are plain Markdown, Python 3 and Bash.

## Use

In the repository you want to improve, ask your agent:

> Use the ci-cost-cutter skill. Audit this repository's CI and measure a baseline. Propose the highest-value changes, then implement them in reviewable steps. Keep every required check; run the full suite whenever test selection is uncertain. Verify correctness, feedback time and compute cost. Ask me before anything the skill marks as gated.

Shorter prompts work too ("our CI is slow and expensive, help"); the skill starts with intake questions.

Requirements: `git`; Python 3.9+ for the scripts; `gh` (logged in) for GitHub Actions history. Nothing is installed into your repository unless you approve the changes.

## Save time and money

The skill is written to spend as little as possible of both your CI budget and the agent's tokens:
- history before new runs; summaries before logs; grep, never whole logs;
- profile only the top consumers;
- measure on the CI hardware, alternate before/after runs, report compute as well as wall time;
- bundled scripts instead of hand-derived numbers ([`gha_baseline.py`](skills/ci-cost-cutter/scripts/gha_baseline.py), [`measure.sh`](skills/ci-cost-cutter/scripts/measure.sh), [`junit_compare.py`](skills/ci-cost-cutter/scripts/junit_compare.py));
- a ledger so no session repeats another's measurements.

## Repository layout

```
skills/ci-cost-cutter/
  SKILL.md                 the workflow, approval gates, budget rules
  references/              levers, measurement, verification, test selection, CI systems, case study, article notes
  scripts/                 gha_baseline.py, measure.sh, junit_compare.py
  assets/CI_LEDGER.template.md
evals/                     test prompts and sample repositories used to check the skill
.claude-plugin/            Claude Code plugin and marketplace manifests
```

## Credits

The method follows [Making CI faster and 95% cheaper](https://vincent.build/openclaw-ci-cost-reduction/) by Vincent Koc and the [OpenClaw CI implementation](https://github.com/openclaw/openclaw/blob/a7d05c7af04aa17ac57c994da238d0c60f058ca6/.github/workflows/ci.yml). This repository is independent and not affiliated with OpenClaw; read the article for the original data and reasoning.

## License

MIT — see [LICENSE](LICENSE).
