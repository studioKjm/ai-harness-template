#!/usr/bin/env python3
"""Keyword detector hook for UserPromptSubmit.

Detects Ouroboros/Harness keywords in user prompts and outputs
routing suggestions. Runs as a Claude Code hook.
"""

import sys
import re

KEYWORDS = {
    "interview": "Start Socratic interview → /interview",
    "seed": "Generate seed spec → /seed",
    "run": "Execute Double Diamond → /run",
    "evaluate": "Run 3-stage evaluation → /evaluate",
    "evolve": "Start evolution loop → /evolve",
    "unstuck": "Get unstuck → /unstuck",
    "pm": "Generate PRD → /pm",
    "status": "Show session status → harness status",
    "drift": "Check drift → harness drift",
    "score": "Check ambiguity → harness score",
}

def detect(prompt: str) -> None:
    prompt_lower = prompt.lower().strip()

    # Direct command detection: "ooo interview", "/interview", etc.
    for keyword, description in KEYWORDS.items():
        patterns = [
            rf'\booo\s+{keyword}\b',
            rf'^/{keyword}\b',
            rf'\bharness\s+{keyword}\b',
        ]
        for pattern in patterns:
            if re.search(pattern, prompt_lower):
                # Output is captured by Claude Code and shown as context
                print(f"[Harness] Detected: {keyword} → {description}")
                return

    # Ambiguity warning: detect vague prompts
    vague_patterns = [
        r'^(make|build|create|add)\s+(a|an|the)\s+\w+$',
        r'^(fix|update|change)\s+(it|this|that)$',
        r'^(do|implement)\s+\w+$',
    ]
    for pattern in vague_patterns:
        if re.match(pattern, prompt_lower):
            print("[Harness] Warning: Vague prompt detected. Consider running /interview first.")
            return


if __name__ == "__main__":
    if len(sys.argv) > 1:
        detect(sys.argv[1])
