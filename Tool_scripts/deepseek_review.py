"""DeepSeek code/plan reviewer (in-container substitute for the deepseek MCP).

We are in a dev container where the deepseek-bridge MCP isn't reachable, but the
DeepSeek API is (same access the pipeline uses). This thin CLI sends a diff /
files / arbitrary text + review instructions to deepseek-v4-pro (thinking on) and
prints a graded review — genuine DeepSeek, no MCP plumbing.

Usage:
    # review the working-tree diff vs HEAD
    python Tool_scripts/deepseek_review.py --diff --context "what & why; what to check"
    # review specific files
    python Tool_scripts/deepseek_review.py --files a.py b.py --context "..."
    # review arbitrary text (e.g. a plan) from stdin
    echo "<plan>" | python Tool_scripts/deepseek_review.py --context "review this plan"
    # save the review to the audit trail
    python Tool_scripts/deepseek_review.py --diff --context "..." --out AI_agent/logs/review/review/<date>_<topic>_deepseek.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

from src.agent.llm import load_llm_section

_SYSTEM = (
    "You are a senior software reviewer for an EnergyPlus modeling pipeline. "
    "Review the provided change/plan strictly for: correctness & regressions, "
    "broken contracts or interfaces, design/architecture issues, missed edge "
    "cases, and anything unsafe. Output: (1) a one-line VERDICT "
    "(APPROVE / APPROVE-WITH-NITS / REQUEST-CHANGES), then (2) findings graded "
    "[High]/[Medium]/[Low], each with concrete evidence (file/line or quoted "
    "text) and a suggested fix. Be concise and specific; do not restate the "
    "change. If something is fine, say so briefly rather than inventing issues."
)


def _gather(args) -> str:
    if args.files:
        parts = []
        for f in args.files:
            p = Path(f)
            parts.append(f"===== {f} =====\n{p.read_text(encoding='utf-8')}")
        return "\n\n".join(parts)
    if args.diff:
        out = subprocess.run(
            ["git", "diff", args.base], capture_output=True, text=True
        )
        return out.stdout or "(empty diff)"
    data = sys.stdin.read()
    return data or "(no input)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", action="store_true", help="review `git diff <base>`")
    ap.add_argument("--base", default="HEAD", help="diff base (default HEAD)")
    ap.add_argument("--files", nargs="*", help="review these files verbatim")
    ap.add_argument("--context", default="", help="what changed / what to check")
    ap.add_argument("--out", help="also write the review to this path")
    args = ap.parse_args()

    content = _gather(args)
    section = load_llm_section("intake_phase2")
    client = OpenAI(
        api_key=section["api_key"],
        base_url=section.get("base_url"),
        timeout=600.0,
        max_retries=2,
    )
    human = (
        (f"REVIEW CONTEXT:\n{args.context}\n\n" if args.context else "")
        + "CHANGE / PLAN TO REVIEW:\n"
        + content
    )
    resp = client.chat.completions.create(
        model=section["model_name"],
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": human},
        ],
        temperature=0.2,
        max_tokens=section.get("max_tokens", 16000),
        extra_body=section.get("extra_body") or {"thinking": {"type": "enabled"}},
    )
    review = resp.choices[0].message.content or "(empty review)"
    print(review)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(review, encoding="utf-8")
        print(f"\n[saved review -> {args.out}]", file=sys.stderr)


if __name__ == "__main__":
    main()
