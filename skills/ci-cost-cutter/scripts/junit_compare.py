#!/usr/bin/env python3
"""Compare two JUnit result sets by (file, test name): same tests, same outcomes?

Usage:
  python3 junit_compare.py BEFORE AFTER [--allow-added] [--exclude TEXT] [--top 10]
BEFORE and AFTER are JUnit XML files or directories of them (shards are merged; files whose name contains an --exclude text are
skipped, for example a fallback rerun). Exit 0 when both sides have the same (file, name) keys with the same outcomes
(--allow-added: keys only in AFTER are allowed, for tests you added on purpose); exit 1 otherwise.

Outcome per test case: fail (a <failure>/<error> child or a failure attribute), skip (<skipped>), else pass. A key that appears
several times (parameterized names) is compared as the sorted list of its outcomes.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict


def parse(path: str) -> list[tuple[str, str, str, float]]:
    text = open(path, encoding="utf-8", errors="replace").read()
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text)
        rows = []
        for tc in root.iter("testcase"):
            outcome = "fail" if (tc.get("failure") is not None or tc.find("failure") is not None or tc.find("error") is not None) \
                else "skip" if tc.find("skipped") is not None else "pass"
            rows.append((tc.get("file") or tc.get("classname") or "?", tc.get("name") or "?", outcome, float(tc.get("time") or 0)))
        return rows
    except ImportError:  # a Python without expat: html.parser needs none
        from html.parser import HTMLParser

        class Cases(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.stack, self.rows = [], []

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                if tag == "testcase":
                    self.stack.append([a.get("file") or a.get("classname") or "?", a.get("name") or "?", "fail" if "failure" in a else "pass", float(a.get("time") or 0)])
                elif self.stack and tag in ("failure", "error"):
                    self.stack[-1][2] = "fail"
                elif self.stack and tag == "skipped" and self.stack[-1][2] == "pass":
                    self.stack[-1][2] = "skip"

            def handle_startendtag(self, tag, attrs):
                self.handle_starttag(tag, attrs)
                if tag == "testcase":
                    self.rows.append(tuple(self.stack.pop()))

            def handle_endtag(self, tag):
                if tag == "testcase" and self.stack:
                    self.rows.append(tuple(self.stack.pop()))

        c = Cases()
        c.feed(text)
        return c.rows


def load(path: str, exclude: list[str]) -> list[tuple[str, str, str, float]]:
    files = [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.endswith(".xml")] if os.path.isdir(path) else [path]
    files = [f for f in files if not any(x in os.path.basename(f) for x in exclude)]
    rows = []
    for f in files:
        rows += parse(f)
    return rows


def norm(file: str) -> str:
    return re.sub(r"^file://", "", file)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--allow-added", action="store_true")
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--top", type=int, default=10)
    a = p.parse_args()

    sides = {}
    for label, path in (("before", a.before), ("after", a.after)):
        rows = load(path, a.exclude)
        keyed = defaultdict(list)
        for f, n, o, t in rows:
            keyed[(norm(f), n)].append((o, t))
        sides[label] = keyed
        print(f"{label}: {len(rows)} test cases, {len(keyed)} keys, outcomes {dict(Counter(o for v in keyed.values() for o, _ in v))}")
    b, af = sides["before"], sides["after"]
    # Absolute paths differ between machines and checkouts: if no key matches, compare by path relative to the common suffix.
    if b and af and not set(b) & set(af):
        def tail(k): return ("/".join(k[0].split("/")[-3:]), k[1])
        b = {tail(k): v for k, v in b.items()}
        af = {tail(k): v for k, v in af.items()}
        print("note: no identical file paths; compared by the last three path parts")
    only_b, only_a = sorted(set(b) - set(af)), sorted(set(af) - set(b))
    diff = [(k, sorted(o for o, _ in b[k]), sorted(o for o, _ in af[k])) for k in sorted(set(b) & set(af)) if sorted(o for o, _ in b[k]) != sorted(o for o, _ in af[k])]
    for title, items in (("only in before (missing after)", only_b), ("only in after (added)", only_a)):
        if items:
            print(f"\n{title}: {len(items)}")
            for k in items[:20]:
                print(f"  {k[0]} :: {k[1]}")
    if diff:
        print(f"\noutcome differences: {len(diff)}")
        for k, x, y in diff[:20]:
            print(f"  {k[0]} :: {k[1]}: {x} -> {y}")
    for label, side in (("before", b), ("after", af)):
        per = Counter()
        for (f, _), v in side.items():
            per[f] += sum(t for _, t in v)
        print(f"\n{label}: test seconds {sum(per.values()):.0f}; top files: " + ", ".join(f"{os.path.basename(f)} {t:.0f}s" for f, t in per.most_common(a.top)))
    ok = not only_b and not diff and (a.allow_added or not only_a)
    print("\nRESULT", "SAME" if ok else "DIFFERENT")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
