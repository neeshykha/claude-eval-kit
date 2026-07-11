"""Blind classification runner: shells out to the Claude Code CLI once per item,
never passing ground truth, and writes predictions to a resumable JSONL file."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable


class BlindClassifier:
    """Runs a prompt template against every item in a dataset via the Claude Code
    CLI. The CLI is expected to auto-load a CLAUDE.md in `cwd` that defines the
    actual classification logic -- this runner only handles orchestration
    (prompting, parsing, resuming, error capture), never the domain rules."""

    def __init__(
        self,
        prompt_template: str,
        model: str = "sonnet",
        cwd: Path | None = None,
        timeout: int = 60,
        id_field: str = "id",
    ):
        self.prompt_template = prompt_template
        self.model = model
        self.cwd = cwd
        self.timeout = timeout
        self.id_field = id_field

    def classify_one(self, item: dict) -> dict:
        prompt = self.prompt_template.format(**item)
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", self.model, "--output-format", "json"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:500]}")
        envelope = json.loads(result.stdout)
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", envelope["result"].strip())
        return json.loads(raw)

    def run(
        self,
        items: list[dict],
        output_path: Path,
        on_progress: Callable[[str, dict], None] | None = None,
    ) -> None:
        """Classifies every item not already present in output_path. Safe to
        interrupt and re-run -- already-classified ids are skipped."""
        already_done: set[str] = set()
        if output_path.exists():
            already_done = {json.loads(l)[self.id_field] for l in output_path.open()}
        remaining = [it for it in items if it[self.id_field] not in already_done]
        print(f"Resuming: {len(already_done)} already done, {len(remaining)} remaining", file=sys.stderr)

        with output_path.open("a") as out:
            for i, item in enumerate(remaining, 1):
                item_id = item[self.id_field]
                print(f"[{i}/{len(remaining)}] {item_id}...", file=sys.stderr, end=" ")
                try:
                    prediction = self.classify_one(item)
                    record = {self.id_field: item_id, **prediction}
                    out.write(json.dumps(record) + "\n")
                    if on_progress:
                        on_progress(item_id, record)
                    else:
                        print(json.dumps({k: v for k, v in prediction.items() if k != "reasoning"}), file=sys.stderr)
                except Exception as exc:
                    out.write(json.dumps({self.id_field: item_id, "error": str(exc)}) + "\n")
                    print(f"FAILED: {exc}", file=sys.stderr)
                out.flush()
