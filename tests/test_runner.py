"""Tests for the resumability logic in runner.py.

Stdlib unittest rather than pytest, so the kit keeps its zero-dependency install:

    python -m unittest discover tests

Only the file-manipulation half is covered. Classification itself shells out to the
Claude Code CLI and is stochastic -- that gets an eval (see examples/), not a test.
"""

import json
import tempfile
import unittest
from pathlib import Path

from eval_kit import drop_failed


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class DropFailedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "predictions.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_drops_only_error_rows(self):
        write_rows(
            self.path,
            [
                {"id": "A", "label": "x"},
                {"id": "B", "error": "claude CLI exited 1"},
                {"id": "C", "label": "y"},
                {"id": "D", "error": "No such file or directory: 'claude'"},
            ],
        )
        self.assertEqual(drop_failed(self.path), 2)
        self.assertEqual([r["id"] for r in read_rows(self.path)], ["A", "C"])

    def test_preserves_successful_work(self):
        """The whole point: recovering from a mid-run failure must not cost the
        classifications that already succeeded."""
        rows = [{"id": f"D{i:03d}", "label": "ok"} for i in range(16)]
        rows += [{"id": f"D{i:03d}", "error": "transient"} for i in range(16, 32)]
        write_rows(self.path, rows)

        self.assertEqual(drop_failed(self.path), 16)
        kept = read_rows(self.path)
        self.assertEqual(len(kept), 16)
        self.assertTrue(all("error" not in r for r in kept))

    def test_no_failures_leaves_file_untouched(self):
        rows = [{"id": "A", "label": "x"}, {"id": "B", "label": "y"}]
        write_rows(self.path, rows)
        before = self.path.read_text()

        self.assertEqual(drop_failed(self.path), 0)
        self.assertEqual(self.path.read_text(), before)

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(drop_failed(Path(self.tmp.name) / "nope.jsonl"), 0)

    def test_all_rows_failed(self):
        write_rows(self.path, [{"id": "A", "error": "x"}, {"id": "B", "error": "y"}])
        self.assertEqual(drop_failed(self.path), 2)
        self.assertEqual(read_rows(self.path), [])

    def test_respects_custom_id_field(self):
        write_rows(
            self.path,
            [{"ticket": "T1", "label": "x"}, {"ticket": "T2", "error": "boom"}],
        )
        self.assertEqual(drop_failed(self.path, id_field="ticket"), 1)
        self.assertEqual([r["ticket"] for r in read_rows(self.path)], ["T1"])


if __name__ == "__main__":
    unittest.main()
