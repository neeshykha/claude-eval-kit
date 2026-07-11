"""Generic scoring functions for classification predictions against ground truth.
Works on any categorical field -- not specific to severity/routing/support."""

from collections import Counter


def accuracy(scored: dict, truth: dict, field: str) -> tuple[int, int]:
    """Returns (correct, total) for a single field across all scored items."""
    correct = sum(1 for pid, p in scored.items() if p.get(field) == truth[pid][field])
    return correct, len(scored)


def confusion_matrix(scored: dict, truth: dict, field: str, categories: list[str]) -> dict[str, Counter]:
    """Returns {true_category: Counter({predicted_category: count})}."""
    matrix = {c: Counter() for c in categories}
    for pid, p in scored.items():
        matrix[truth[pid][field]][p.get(field)] += 1
    return matrix


def ordinal_misses(
    scored: dict, truth: dict, field: str, order: list[str]
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """For fields with a meaningful severity-like order (most urgent first),
    splits misses into under-prediction (predicted less urgent than reality --
    typically the costlier direction) and over-prediction. Each entry is
    (item_id, true_value, predicted_value)."""
    under, over = [], []
    for pid, p in scored.items():
        true_val = truth[pid][field]
        pred_val = p.get(field)
        if pred_val not in order or true_val not in order:
            continue
        true_idx = order.index(true_val)
        pred_idx = order.index(pred_val)
        if pred_idx > true_idx:
            under.append((pid, true_val, pred_val))
        elif pred_idx < true_idx:
            over.append((pid, true_val, pred_val))
    return under, over
