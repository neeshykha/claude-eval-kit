#!/usr/bin/env python3
"""Runs the support-triage example end to end using eval_kit: blind-classifies
every ticket via the Claude Code CLI (CLAUDE.md in this directory drives the
logic), scores predictions against ground truth, and writes a markdown scorecard.

This is eval_kit's example #1 -- the same pattern originally built for
claude-triage-simulator, re-expressed on top of the reusable package instead of
duplicated inline."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from eval_kit import BlindClassifier, TrapGroup, render_scorecard
from eval_kit.report import FieldConfig

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "tickets.jsonl"
PREDICTIONS_PATH = ROOT / "predictions.jsonl"
SCORECARD_PATH = ROOT / "results" / "scorecard.md"

PROMPT_TEMPLATE = """Classify this support ticket per the severity taxonomy, routing \
categories, and output format defined in CLAUDE.md.

Ticket (author role: {author_role}):
\"\"\"{text}\"\"\"

Return only the JSON object described in the Output Format section. No other text."""

SEVERITY_ORDER = ["P1", "P2", "P3", "P4"]
ROUTING_CATEGORIES = [
    "Tier 1 Support",
    "Tier 2 Escalations",
    "Field Service / Hardware Dispatch",
    "Access Control & Security",
    "Environmental Monitoring",
    "Billing & Account Management",
    "Product/Engineering Bug Report",
]

CONFUSABLE_GROUPS = [
    TrapGroup(["T028", "T029", "T030"], "Resolved lockout via backup code (should not stay P1)"),
    TrapGroup(["T031", "T032", "T033", "T034"], "False-alarm leak, confirmed dry (should downgrade to P3)"),
    TrapGroup(["T007", "T008"], "Multi-unit thermostat = property-wide P1, not per-unit P2"),
    TrapGroup(["T009", "T010", "T060"], "Unresolved >24h on safety-adjacent device = escalation override to P1"),
]


def load_jsonl(path: Path) -> dict:
    return {json.loads(l)["id"]: json.loads(l) for l in path.open()}


def main() -> None:
    items = load_jsonl(DATA_PATH)
    classifier = BlindClassifier(PROMPT_TEMPLATE, cwd=ROOT)
    classifier.run(list(items.values()), PREDICTIONS_PATH)

    predictions = load_jsonl(PREDICTIONS_PATH)
    errors = [pid for pid, p in predictions.items() if "error" in p]
    scored = {pid: p for pid, p in predictions.items() if "error" not in p}
    truth = {
        pid: {"severity": item["true_severity"], "routing": item["true_routing"]}
        for pid, item in items.items()
    }

    fields = [
        FieldConfig("severity", SEVERITY_ORDER, order=SEVERITY_ORDER, traps=CONFUSABLE_GROUPS),
        FieldConfig("routing", ROUTING_CATEGORIES),
    ]

    report = render_scorecard("Support Triage Scorecard (eval_kit example)", scored, truth, items, fields, errors)
    SCORECARD_PATH.write_text(report)
    print(report)


if __name__ == "__main__":
    main()
