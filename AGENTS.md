# Agent instructions

This repository holds the **ci-cost-cutter** skill. Two cases:

1. **You were asked to make some *other* repository's CI faster or cheaper.** Follow [`skills/ci-cost-cutter/SKILL.md`](skills/ci-cost-cutter/SKILL.md) in that repository. Read its "Operating principles", "Human approval gates" and "Budget discipline" before you run anything. Never change this repository for that task.
2. **You were asked to improve this repository** (the skill itself). Keep `SKILL.md` under about 300 lines and move detail into `references/`. Keep the approval gates intact: they are the reason people can trust the skill. Test changes against `evals/evals.json` (see `evals/README.md`). Scripts must run on stock Python 3.9+ and Bash, with no third-party packages.

Writing style for everything here: short sentences, active voice, one name per thing, numbers with their conditions.
