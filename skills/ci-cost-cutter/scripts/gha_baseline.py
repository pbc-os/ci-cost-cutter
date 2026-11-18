#!/usr/bin/env python3
"""GitHub Actions baseline from run history (no new CI runs).

Per workflow and per job: runs, median and p90 duration (runs and jobs that never ran — skipped, action_required, stale — are excluded), summed job minutes (each job rounded up to a whole minute, as hosted
billing does before the runner multiplier), median queue time, and failure / cancel rates. Uses the `gh` CLI for auth.

Usage:
  python3 gha_baseline.py --repo OWNER/REPO [--days 14] [--branch main] [--event pull_request] [--workflow NAME]
                          [--max-runs 200] [--json out.json]

Cost: one API call per 100 runs plus one per run for its jobs (200 runs ~ 202 calls; the authenticated limit is 5,000/hour).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone


NOT_RUN = ("skipped", "action_required", "stale")


def gh(path: str) -> dict:
    out = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh api {path} failed: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout)


def ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def seconds(a: datetime | None, b: datetime | None) -> float | None:
    return (b - a).total_seconds() if a and b and b >= a else None


def pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    v = sorted(values)
    return v[min(len(v) - 1, max(0, math.ceil(q * len(v)) - 1))]  # nearest rank


def fmt(s: float) -> str:
    if s != s:  # NaN
        return "-"
    return f"{s / 60:.1f}m" if s >= 90 else f"{s:.0f}s"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", required=True)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--branch")
    p.add_argument("--event")
    p.add_argument("--workflow", help="only runs whose workflow name contains this text")
    p.add_argument("--max-runs", type=int, default=200)
    p.add_argument("--json", help="also write the raw aggregates to this file")
    a = p.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(days=a.days)).strftime("%Y-%m-%d")
    query = f"per_page=100&created=%3E%3D{since}" + (f"&branch={a.branch}" if a.branch else "") + (f"&event={a.event}" if a.event else "")
    runs: list[dict] = []
    page = 1
    while len(runs) < a.max_runs:
        batch = gh(f"repos/{a.repo}/actions/runs?{query}&page={page}").get("workflow_runs", [])
        if not batch:
            break
        runs += [r for r in batch if not a.workflow or a.workflow.lower() in (r.get("name") or "").lower()]
        page += 1
    runs = [r for r in runs if r.get("status") == "completed"][: a.max_runs]
    if not runs:
        sys.exit("no completed runs in the window")

    wf = defaultdict(lambda: {"dur": [], "concl": defaultdict(int)})
    jobs = defaultdict(lambda: {"dur": [], "queue": [], "minutes": 0, "concl": defaultdict(int)})
    for i, r in enumerate(runs):
        name = r.get("name") or str(r.get("workflow_id"))
        d = seconds(ts(r.get("run_started_at")), ts(r.get("updated_at")))
        if d is not None and r.get("conclusion") not in NOT_RUN:  # skipped or never approved: no time; keep it out of the medians
            wf[name]["dur"].append(d)
        wf[name]["concl"][r.get("conclusion") or "none"] += 1
        for j in gh(f"repos/{a.repo}/actions/runs/{r['id']}/jobs?per_page=100").get("jobs", []):
            key = (name, j.get("name"))
            jd = seconds(ts(j.get("started_at")), ts(j.get("completed_at")))
            if jd is not None and j.get("conclusion") not in NOT_RUN:
                jobs[key]["dur"].append(jd)
                jobs[key]["minutes"] += math.ceil(jd / 60) if jd > 0 else 0
            q = seconds(ts(j.get("created_at") or r.get("run_started_at")), ts(j.get("started_at")))
            if q is not None and j.get("conclusion") not in NOT_RUN:
                jobs[key]["queue"].append(q)
            jobs[key]["concl"][j.get("conclusion") or "none"] += 1
        if (i + 1) % 25 == 0:
            print(f"... {i + 1}/{len(runs)} runs read", file=sys.stderr)

    rate = lambda c, k: 100 * c.get(k, 0) / max(1, sum(c.values()))
    print(f"# {a.repo}: {len(runs)} completed runs since {since}" + (f", branch {a.branch}" if a.branch else "") + (f", event {a.event}" if a.event else ""))
    print("\n## Workflows\n\n| workflow | runs | median | p90 | fail % | cancel % | not run % |\n| --- | --- | --- | --- | --- | --- | --- |")
    for name, w in sorted(wf.items(), key=lambda x: -sum(x[1]["dur"])):
        print(f"| {name} | {sum(w['concl'].values())} | {fmt(statistics.median(w['dur']) if w['dur'] else float('nan'))} | {fmt(pct(w['dur'], .9))} | {rate(w['concl'], 'failure'):.0f} | {rate(w['concl'], 'cancelled'):.0f} | {sum(rate(w['concl'], k) for k in NOT_RUN):.0f} |")
    total = sum(j["minutes"] for j in jobs.values()) or 1
    print("\n## Jobs by billed minutes (each job rounded up; apply your runner multiplier)\n\n| workflow / job | runs | median | p90 | minutes | share | median queue | fail % | cancel % |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for (w, jn), j in sorted(jobs.items(), key=lambda x: -x[1]["minutes"])[:40]:
        med = statistics.median(j["dur"]) if j["dur"] else float("nan")
        mq = statistics.median(j["queue"]) if j["queue"] else float("nan")
        print(f"| {w} / {jn} | {sum(j['concl'].values())} | {fmt(med)} | {fmt(pct(j['dur'], .9))} | {j['minutes']} | {100 * j['minutes'] / total:.0f}% | {fmt(mq)} | {rate(j['concl'], 'failure'):.0f} | {rate(j['concl'], 'cancelled'):.0f} |")
    print(f"\nTotal job minutes: {total}. Top consumers first; profile only those.")
    if a.json:
        out = {"repo": a.repo, "since": since, "runs": len(runs),
               "workflows": {n: {"durations": w["dur"], "conclusions": dict(w["concl"])} for n, w in wf.items()},
               "jobs": [{"workflow": w, "job": jn, "durations": j["dur"], "queue": j["queue"], "minutes": j["minutes"], "conclusions": dict(j["concl"])} for (w, jn), j in jobs.items()]}
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
