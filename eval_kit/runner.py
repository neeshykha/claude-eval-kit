"""Blind classification runner: shells out to the Claude Code CLI once per item,
never passing ground truth, and writes predictions to a resumable JSONL file."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable


def drop_failed(output_path: Path, id_field: str = "id") -> int:
    """Removes recorded failures from a predictions file so a later run
    reclassifies them. Returns the number of rows dropped.

    Resumability records failures the same way it records successes, which means a
    transient error -- an expired session, a rate limit, the CLI updating itself
    mid-run -- becomes permanent: the id is in the file, so every subsequent run
    skips it. Deleting the whole file to recover throws away every good
    classification alongside the bad ones, which on a long run is most of the work.
    """
    if not output_path.exists():
        return 0
    rows = [json.loads(line) for line in output_path.read_text().splitlines() if line.strip()]
    keep = [r for r in rows if "error" not in r]
    if len(keep) != len(rows):
        output_path.write_text("".join(json.dumps(r) + "\n" for r in keep))
    return len(rows) - len(keep)


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
        retry_failed: bool = False,
    ) -> None:
        """Classifies every item not already present in output_path. Safe to
        interrupt and re-run -- already-classified ids are skipped.

        Recorded failures count as present, so they are skipped too. Pass
        `retry_failed=True` to drop them first and reclassify only those. It is not
        the default because an item that fails deterministically -- malformed input,
        a prompt the model always refuses -- would retry on every run and never
        converge; opting in keeps a run guaranteed to terminate.
        """
        if retry_failed:
            dropped = drop_failed(output_path, self.id_field)
            print(f"Dropped {dropped} failed rows for retry", file=sys.stderr)

        already_done: set[str] = set()
        failed: set[str] = set()
        if output_path.exists():
            for line in output_path.read_text().splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                already_done.add(record[self.id_field])
                if "error" in record:
                    failed.add(record[self.id_field])
        remaining = [it for it in items if it[self.id_field] not in already_done]

        status = f"Resuming: {len(already_done)} already done, {len(remaining)} remaining"
        if failed:
            status += (
                f"\nWARNING: {len(failed)} recorded failures are being skipped as done."
                " Pass retry_failed=True to reclassify them."
            )
        print(status, file=sys.stderr)

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
