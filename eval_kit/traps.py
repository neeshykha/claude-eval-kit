"""Confusable-pattern traps: groups of dataset items deliberately written so that
a naive keyword-matching read gets them wrong. Auditing these separately from
overall accuracy is the point of this kit -- aggregate accuracy hides exactly the
failures that matter most (an eval that's 90% accurate but always fails the same
trap has a specific, fixable blind spot, not a vague accuracy gap)."""

from dataclasses import dataclass


@dataclass
class TrapGroup:
    ids: list[str]
    label: str
    field: str = "severity"


@dataclass
class TrapResult:
    group: TrapGroup
    hits: int
    total: int
    detail: list[tuple[str, str, str, bool]]  # (id, true, predicted, correct)


def audit_traps(scored: dict, truth: dict, groups: list[TrapGroup]) -> list[TrapResult]:
    results = []
    for group in groups:
        detail = []
        hits = 0
        for pid in group.ids:
            if pid not in scored:
                continue
            true_val = truth[pid][group.field]
            pred_val = scored[pid].get(group.field)
            correct = true_val == pred_val
            hits += int(correct)
            detail.append((pid, true_val, pred_val, correct))
        results.append(TrapResult(group=group, hits=hits, total=len(detail), detail=detail))
    return results
