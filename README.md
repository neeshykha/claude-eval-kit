# claude-eval-kit

A small, reusable framework for scoring AI classifiers against ground truth: blind
classification via the Claude Code CLI, confusion matrices, ordinal miss-direction
splits (e.g. under- vs. over-triage), and confusable-pattern trap audits.

This isn't a new idea — it's an extraction. [claude-triage-simulator](https://github.com/neeshykha/claude-triage-simulator)
built this exact pattern once, inline, for one domain (support-ticket triage).
[agent-ops-bench](https://github.com/neeshykha/agent-ops-bench) needed most of the
same scoring logic again, for a different question (does a second agent help).
Two repos quietly reinventing the same eval machinery is a sign the machinery
should be a package, not a habit. This is that package — `examples/support_triage/`
is the triage simulator's pattern, re-expressed on top of it instead of duplicated.

---

## Why a package instead of a script per project

Aggregate accuracy hides exactly the failures that matter. A classifier that's 90%
accurate but always fails the same edge case has a specific, fixable blind spot —
not a vague accuracy gap. The point of this kit is to make three things a five-line
config instead of a hundred-line rewrite every time:

1. **Blind classification** — the classifier never sees ground truth, only the item.
2. **Confusable-pattern traps** — deliberately-written edge cases scored as their
   own named group, not folded into the overall percentage.
3. **Ordinal miss direction** — for fields with a real order (severity, priority),
   split misses into "predicted less urgent than reality" vs. the reverse, because
   those two failure modes usually carry different operational cost.

---

## How It Works

```
eval_kit/
  runner.py    BlindClassifier — shells out to `claude -p` per item, resumable
  scorer.py    accuracy(), confusion_matrix(), ordinal_misses()
  traps.py     TrapGroup + audit_traps() — named, scored edge-case groups
  report.py    render_scorecard() — assembles all of the above into markdown
```

A project using this kit provides:
- A `CLAUDE.md` in its working directory with the actual classification logic
  (the CLI auto-loads it — this is the runtime prompt, not documentation)
- A dataset of labeled items
- A `FieldConfig` per field being scored (categories, optional order, optional traps)

`eval_kit` never sees the domain logic. It only orchestrates calling the classifier,
scoring what comes back, and writing the report.

### Resuming, and recovering from a failed run

`BlindClassifier.run()` appends each result as it lands and skips ids already in the
output file, so an interrupted run picks up where it stopped.

Failures are recorded the same way successes are, which makes them **sticky**: the id
is in the file, so every later run skips it. That is deliberate — an item that fails
deterministically would otherwise retry forever and the run would never converge — but
it means a *transient* failure needs an explicit escape hatch:

```python
classifier.run(items, predictions_path, retry_failed=True)
```

That drops the recorded error rows first, so the next pass reclassifies only those and
keeps everything that already succeeded. `drop_failed(path)` is exported separately if
you want the same behavior outside a run.

`run()` also warns when the output file contains failures it is about to skip. Without
that, a run where every call failed reports `32 already done, 0 remaining` and exits
looking like a success — which is exactly how a broken run gets mistaken for a
finished one.

This came out of [deflection-audit](https://github.com/neeshykha/deflection-audit),
where the Claude Code CLI updated itself mid-run and its symlink briefly vanished,
taking out 16 of 32 conversations. Deleting the file to recover would have thrown away
the 16 that worked.

---

## Example: Support Triage

`examples/support_triage/` re-implements the triage-simulator's pattern on top of
this kit: a 20-ticket subset of the original 60 (chosen to include every confusable
pattern group), the same severity/routing taxonomy, scored the same way.

### Results (last run)

20 tickets, 20 scored, 0 classification failures.

| Metric | Result |
|---|---|
| Severity accuracy | 80% (16/20) |
| Routing accuracy | 70% (14/20) |
| Confusable-pattern traps | 10/12 (83%) |

The headline number isn't the interesting part — the routing confusion matrix is.
**3 of 4 true "Field Service / Hardware Dispatch" thermostat tickets got routed to
"Environmental Monitoring" instead**, including both halves of the multi-unit
thermostat trap (T007, T008 — severity was correctly bumped to P1, but routing
missed anyway). The taxonomy reserves Environmental Monitoring for leak/humidity/
*sensor* issues tied to property damage risk, and Field Service for thermostat
hardware — but "temperature" reads as environmental to the classifier regardless
of which category the ticket actually describes. That's a specific, legible
routing blind spot a taxonomy-naming tweak could probably fix, not a vague
accuracy gap — which is the entire point of scoring a confusion matrix instead of
just an accuracy percentage.

Full breakdown: [`examples/support_triage/results/scorecard.md`](examples/support_triage/results/scorecard.md).

### Run it yourself

```bash
git clone https://github.com/neeshykha/claude-eval-kit
cd claude-eval-kit/examples/support_triage

# Requires the Claude Code CLI, authenticated
python3 run_example.py
```

Resumable — if interrupted, re-running skips tickets already in `predictions.jsonl`.

### Tests

```bash
python3 -m unittest discover tests
```

Covers the resumability file handling only — stdlib `unittest`, so the kit keeps its
zero-dependency install. Classification itself is stochastic and gets an eval rather
than assertions; the scorecard is that measurement.

---

## Using It On a New Problem

1. Write a `CLAUDE.md` with your classification taxonomy and an `Output Format`
   section specifying strict JSON.
2. Load your dataset as `{id: {...fields..., true_<field>: ...}}`.
3. Define a `FieldConfig` per scored field:
   ```python
   FieldConfig("severity", categories=[...], order=[...], traps=[TrapGroup([...], "label")])
   ```
4. Run `BlindClassifier(prompt_template, cwd=your_dir).run(items, predictions_path)`,
   then `render_scorecard(...)`.

No fork required — `pip install -e .` this repo and import `eval_kit` from anywhere.

---

## On the Dataset

The 20 tickets in `examples/support_triage/` are a subset of the synthetic dataset
built for `claude-triage-simulator`, written to mirror real patterns from
multifamily IoT support operations without using any actual customer or company
data. No production ticket content — from this project or any employer — appears
anywhere in this repo.

---

## Tech Stack

- **Claude Code** — classification execution
- **Python (stdlib only)** — orchestration, scoring, reporting
