"""Renders a markdown scorecard from scored predictions: per-field accuracy,
confusion matrices, ordinal miss breakdowns, and confusable-pattern trap audits."""

from dataclasses import dataclass, field as dc_field

from .scorer import accuracy, confusion_matrix, ordinal_misses
from .traps import TrapGroup, audit_traps


@dataclass
class FieldConfig:
    name: str
    categories: list[str]
    order: list[str] | None = None  # set for ordinal fields (e.g. severity) to get under/over-triage split
    traps: list[TrapGroup] = dc_field(default_factory=list)
    text_field: str = "text"  # field on the source item used for miss excerpts


def render_scorecard(
    title: str,
    scored: dict,
    truth: dict,
    items: dict,
    fields: list[FieldConfig],
    errors: list[str] | None = None,
) -> str:
    errors = errors or []
    n = len(scored)
    lines = [f"# {title}\n"]
    lines.append(f"**Items scored:** {n}/{len(items)} ({len(errors)} failed to classify)\n")

    for fc in fields:
        correct, total = accuracy(scored, truth, fc.name)
        lines.append(f"**{fc.name.capitalize()} accuracy:** {correct}/{total} ({correct/total:.0%})\n")

    for fc in fields:
        lines.append(f"\n## {fc.name.capitalize()} Confusion Matrix\n")
        header = "| true \\ pred | " + " | ".join(fc.categories) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(fc.categories) + 1))
        matrix = confusion_matrix(scored, truth, fc.name, fc.categories)
        for t in fc.categories:
            row = " | ".join(str(matrix[t][pred]) for pred in fc.categories)
            lines.append(f"| {t} | {row} |")

        if fc.order:
            under, over = ordinal_misses(scored, truth, fc.name, fc.order)
            lines.append(f"\n**Under-predicted (predicted less urgent than reality):** {len(under)}")
            for pid, true_v, pred_v in under:
                excerpt = items[pid].get(fc.text_field, "")[:90]
                lines.append(f"- {pid}: true {true_v} -> predicted {pred_v} -- \"{excerpt}...\"")
            lines.append(f"\n**Over-predicted (predicted more urgent than reality):** {len(over)}")
            for pid, true_v, pred_v in over:
                excerpt = items[pid].get(fc.text_field, "")[:90]
                lines.append(f"- {pid}: true {true_v} -> predicted {pred_v} -- \"{excerpt}...\"")

        if fc.traps:
            lines.append(f"\n## {fc.name.capitalize()} Confusable-Pattern Audit\n")
            lines.append("Items deliberately written to test whether the classifier applies")
            lines.append("nuance rules, not just keyword matching.\n")
            for result in audit_traps(scored, truth, fc.traps):
                lines.append(f"- **{result.group.label}**: {result.hits}/{result.total} correct")
                for pid, true_v, pred_v, ok in result.detail:
                    mark = "OK" if ok else "MISS"
                    lines.append(f"  - [{mark}] {pid}: true {true_v}, predicted {pred_v}")

    if errors:
        lines.append(f"\n## Classification Failures ({len(errors)})\n")
        for eid in errors:
            lines.append(f"- {eid}")

    return "\n".join(lines) + "\n"
