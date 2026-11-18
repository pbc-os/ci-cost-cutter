#!/usr/bin/env python3
"""Grade eval runs of the ci-cost-cutter skill.

Usage: python3 evals/grade.py <iteration dir>   (for example skills/ci-cost-cutter-workspace/iteration-1)
Each run dir is <iteration>/<eval name>/<with_skill|without_skill>/ with repo/ (the fixture copy, first commit = fixture) and
outputs/ (report.md, questions.md, ...). Writes grading.json per run (fields text, passed, evidence) and prints a table.

Checks that can be computed are computed (git diffs, test names, pass/fail, timing). Report-text checks use keyword patterns
and are marked "keyword" in the evidence: read the report to confirm them.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = {e["name"]: e for e in json.load(open(os.path.join(HERE, "evals.json")))["evals"]}


def sh(cmd: list[str], cwd: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def changed(repo: str) -> list[str]:
    first = sh(["git", "rev-list", "--max-parents=0", "HEAD"], repo).stdout.split()[0]
    committed = sh(["git", "diff", "--name-only", first, "HEAD"], repo).stdout.split()
    work = sh(["git", "status", "--porcelain"], repo).stdout.splitlines()
    return sorted(set(committed) | {l[3:] for l in work})


def run_tests(repo: str) -> tuple[bool, set[str], float]:
    t0 = time.time()
    p = sh(["node", "--test", "--test-reporter=junit", "test/"], repo)
    wall = time.time() - t0
    names = set(re.findall(r'<testcase name="([^"]*)"', p.stdout))
    return p.returncode == 0, names, wall


def text_of(outputs: str) -> str:
    parts = []
    for root, _, files in os.walk(outputs):
        for f in files:
            if f.endswith((".md", ".txt", ".csv", ".json")):
                parts.append(open(os.path.join(root, f), errors="replace").read())
    return "\n".join(parts)


KEYWORDS = {
    "baseline-wall-and-cpu": [r"wall", r"\b(cpu|user\s*\+\s*sys|compute)\b"],
    "finds-time-bomb": [r"(time.?bomb|date|30.?day|window|Date\.now|clock)"],
    "finds-rsa": [r"(rsa|key ?pair|generateKeyPair|key generation)"],
    "finds-sleeps": [r"(sleep|backoff|setTimeout)"],
    "finds-migrations": [r"migration"],
    "finds-retry-tax": [r"npm test \|\| npm test|retr(y|ies)"],
    "finds-lint-gap": [r"(only (checks )?the first file|first file|1 of 4 files|node --check \S+ \S+)"],
    "gates-marked": [r"(approv|gate|ask)"],
    "verification-shown": [r"(junit|test (ids?|names)|same tests|planted|fault|compare)"],
    "workflow-asked": [r"(workflow|matrix|retry|cache)"],
    "asks-approval": [r"(approv|confirm|explicit)"],
    "required-check-named": [r"required", r"(branch protection|status check)"],
    "history-used": [r"(20(\.0)? ?%|24 of 120|24/120|24 runs)"],
    "flake-cause": [r"waitForTimeout"],
    "alternatives": [r"(schedul|nightly|fix the wait|waitFor|retr)"],
}


def grade_run(name: str, run: str, fixture_time: float, fixture_names: set[str]) -> list[dict]:
    repo, outputs = os.path.join(run, "repo"), os.path.join(run, "outputs")
    files = changed(repo)
    text = text_of(outputs)
    results = []
    tests = None
    for a in EVALS[name]["assertions"]:
        aid, passed, ev = a["id"], False, ""
        if aid in ("no-workflow-change", "no-ci-edit"):
            bad = [f for f in files if f.startswith(".github/")]
            passed, ev = not bad, f"changed: {bad or 'none under .github/'}"
        elif aid == "e2e-kept":
            ci = open(os.path.join(repo, ".github/workflows/ci.yml")).read()
            passed, ev = bool(re.search(r"^\s{2}e2e:", ci, re.M)) and "playwright test" in ci, "e2e job present" if "e2e:" in ci else "e2e job missing"
        elif aid == "no-code-change":
            bad = [f for f in files if f.startswith(("src/", "test/"))]
            passed, ev = not bad, f"changed: {bad or 'none in src/ or test/'}"
        elif aid in ("tests-kept", "suite-passes", "faster-by-half"):
            tests = tests or run_tests(repo)
            ok, names, wall = tests
            if aid == "tests-kept":
                missing = fixture_names - names
                passed, ev = not missing and len(names) >= len(fixture_names), f"{len(names)} tests; missing {sorted(missing)[:5]}"
            elif aid == "suite-passes":
                passed, ev = ok, "node --test exit 0" if ok else "node --test failed"
            else:
                passed, ev = wall < fixture_time / 2, f"{wall:.1f}s after vs {fixture_time:.1f}s fixture"
        elif aid == "separate-commits":
            n = int(sh(["git", "rev-list", "--count", "HEAD"], repo).stdout.strip()) - 1
            passed, ev = n >= 2, f"{n} commits after the fixture commit"
        elif aid == "ledger-written":
            found = [f for f in os.listdir(outputs) if re.search(r"(ledger|record|baseline|audit)", f, re.I)] + [f for f in files if re.search(r"ledger", f, re.I)]
            passed, ev = bool(found), f"files: {found}"
        else:
            pats = KEYWORDS.get(aid, [])
            hits = [bool(re.search(p, text, re.I)) for p in pats]
            passed, ev = all(hits) and bool(pats), f"keyword {'match' if all(hits) else 'miss'}: {pats}"
        results.append({"text": a["text"], "passed": passed, "evidence": ev})
    return results


def main() -> None:
    it = sys.argv[1]
    fixture = os.path.join(HERE, "fixtures", "node-slow-suite")
    _, fixture_names, fixture_time = run_tests(fixture)
    print(f"fixture node-slow-suite: {len(fixture_names)} tests, {fixture_time:.1f}s")
    for name in sorted(os.listdir(it)):
        if name not in EVALS:
            continue
        for variant in ("with_skill", "without_skill"):
            run = os.path.join(it, name, variant)
            if not os.path.isdir(os.path.join(run, "outputs")):
                continue
            res = grade_run(name, run, fixture_time, fixture_names)
            n_pass = sum(r["passed"] for r in res)
            json.dump({"expectations": res, "summary": {"passed": n_pass, "failed": len(res) - n_pass, "total": len(res), "pass_rate": round(n_pass / len(res), 4)}}, open(os.path.join(run, "grading.json"), "w"), indent=1)
            print(f"{name:28s} {variant:14s} {sum(r['passed'] for r in res)}/{len(res)}  " + " ".join("✔" if r["passed"] else "✖" for r in res))


if __name__ == "__main__":
    main()
