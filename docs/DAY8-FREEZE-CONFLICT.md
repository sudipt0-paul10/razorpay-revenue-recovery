# DAY 8 — BLOCKER INVESTIGATION: `eval-spec-v1.10` vs `code-freeze-holdout` provenance conflict

**Scope:** investigation only. No file modified, no commit made, no push, no test run, no holdout accessed or authorized, no preflight step run. All commands below are read-only (`git diff`, `git show`, `git log`, `git tag`, `git grep`, `grep`).

**Commits under investigation:**
- `eval-spec-v1.10^{commit}` = `125eae8841562f6d5eccab58e055400340e71af6`
- `code-freeze-holdout^{commit}` = `4d45db461943978637673a5611a429e0fe826065`

---

## 1. Exact diff between the two commits

```
$ git rev-parse 4d45db461943978637673a5611a429e0fe826065^
125eae8841562f6d5eccab58e055400340e71af6

$ git merge-base --is-ancestor 125eae8... 4d45db4...
125eae8 is an ancestor of 4d45db4

$ git log --oneline --reverse 125eae8...4d45db4
4d45db4 Preserve pre-holdout evaluation provenance
```

**`4d45db4` is a single commit whose sole parent is `125eae8`.** There is exactly one commit between the two — the graph is linear, not a merge, not a longer chain.

```
$ git diff --stat 125eae8841562f6d5eccab58e055400340e71af6 4d45db461943978637673a5611a429e0fe826065
 CLAUDE.md                                          | 177 ++++++++
 EVAL.md                                            |  10 +
 LIMITATIONS.md                                     | 462 +++++++++++++++++++++
 docs/A3-DESIGN.md                                  |   9 +
 results/a0-dev-20260828-01/manifest.json           |  13 +
 results/a0-dev-20260828-01/metrics.json            |  39 ++
 results/a0-dev-20260828-01/run_params.json         |  10 +
 results/a1-dev-20260828-01/manifest.json           |  13 +
 results/a1-dev-20260828-01/metrics.json            |  39 ++
 results/a1-dev-20260828-01/run_params.json         |  10 +
 results/a2s-dev-20260828-01/manifest.json          |  13 +
 results/a2s-dev-20260828-01/metrics.json           |  39 ++
 results/a2s-dev-20260828-01/run_params.json        |  10 +
 results/a3d-dev-20260828-01/manifest.json          |  13 +
 results/a3d-dev-20260828-01/metrics.json           |  53 +++
 results/a3d-dev-20260828-01/run_params.json        |  10 +
 results/a3llm-c1-dev500-20260828-01/manifest.json  |  13 +
 results/a3llm-c1-dev500-20260828-01/metrics.json   |  52 +++
 results/a3llm-c1-dev500-20260828-01/progress.json  |   6 +
 .../a3llm-c1-dev500-20260828-01/tuning_config.json |  45 ++
 20 files changed, 1036 insertions(+)
```

**All 20 changed files are additions (no deletions, no modifications to a pre-existing line outside the two documentation files below).** Composition:
- `CLAUDE.md` — new file (177 lines), the agent-instructions document.
- `LIMITATIONS.md` — new file (462 lines), a limitations/status document.
- `EVAL.md` — 10 lines added, 0 removed.
- `docs/A3-DESIGN.md` — 9 lines added, 0 removed.
- The remaining 16 files are `manifest.json` / `metrics.json` / `run_params.json` / `progress.json` / `tuning_config.json` for five already-executed `dev`/500-subsample runs (`a0`, `a1`, `a2s`, `a3d`, `a3llm-c1`) — pre-existing run output being **added to version control**, not new numbers. This matches the commit message, "Preserve pre-holdout evaluation provenance."

**`CHANGELOG.md` is byte-identical between the two commits:**
```
$ git diff 125eae8... 4d45db4... -- CHANGELOG.md
(no output)
```

**Note on `configs/model_params.yaml`, `results/sensitivity.md`, and `tests/test_model_params_swept.py`:** all three are also byte-identical between the two commits (confirmed under Task 6 below) — the 26-cell/21-pass-mark state already existed at `125eae8`, before `4d45db4` was written.

### Full text of the two documentation hunks

**`EVAL.md`** (`git diff 125eae8... 4d45db4... -- EVAL.md`):
```diff
@@ -960,6 +960,16 @@ evaluates to a pass mark of `ceil(0.80 × 26) = 21 / 26`, replacing the
 stale `18 / 22`. `results/sensitivity.md` carries the stale 22-cell
 structure and is regenerated from the registry.
 
+> `[CORRECTION, eval-spec-v1.11]` The sentence immediately above
+> describes the state at `eval-spec-v1.8`'s own writing — the artifact
+> genuinely carried the stale 22-cell structure at that time. Stage 7.4
+> (commit `588b6c0`) subsequently regenerated `results/sensitivity.md`
+> from the registry. The artifact now contains 26 cells and states pass
+> mark 21/26. All outcome columns (`clamped`, `invoice CI`, `rescue CI`,
+> `win`) remain `PENDING` in every row — no actual sensitivity sweep has
+> been run. This note does not alter the v1.8 sentence it follows; it
+> records that the regeneration it anticipated has since occurred.
+
 **D. `[AMENDMENT, eval-spec-v1.8]` Criterion 5 is satisfied against a
 stubbed planner, without live API calls.**
```
Landing point in the final file: `EVAL.md:963-971` (inside §7.1 item C, `eval-spec-v1.8`'s sweep-cell-count correction).

**`docs/A3-DESIGN.md`** (`git diff 125eae8... 4d45db4... -- docs/A3-DESIGN.md`):
```diff
@@ -847,6 +847,15 @@ planner failure (§19).
   `card_change_completion_propensity` (low, high) only. Any invocation of
   this fallback must be declared explicitly in `results/sensitivity.md`,
   naming which cells were skipped and why.
+
+  > `[CORRECTION, eval-spec-v1.11]` The two bullets above's "22 cells" /
+  > "22-cell sweep" references are read as 26 cells, pass mark 21/26 —
+  > the same correction `EVAL.md §7.1` item C (`eval-spec-v1.8`) already
+  > made for `EVAL.md §6A`, extended here to this section, which that
+  > correction did not originally sweep. Membership unchanged; no
+  > `[MODEL]` parameter, cell, or magnitude added or removed.
+  > `results/sensitivity.md` was subsequently regenerated from the
+  > registry in Stage 7.4 (commit `588b6c0`) and now shows 26 cells.
 - **Repeat-run subsample:** seeds 1000–1299, nested inside the 500-episode
   sweep subsample. Three live runs, three separate cache files (§13).
```
Landing point in the final file: `docs/A3-DESIGN.md:850-858` (inside §18, the pre-registered tuning/sweep section's cost-contingency bullets).

---

## 2. Every change labelled `[CORRECTION, eval-spec-v1.11]`

Exactly two, confirmed exhaustive by repo-wide search of the target commit's tree:

```
$ git grep -n "eval-spec-v1.11" 4d45db461943978637673a5611a429e0fe826065
4d45db4...:EVAL.md:963:> `[CORRECTION, eval-spec-v1.11]` The sentence immediately above
4d45db4...:docs/A3-DESIGN.md:851:  > `[CORRECTION, eval-spec-v1.11]` The two bullets above's "22 cells" /
```

No third occurrence anywhere in the tree at `4d45db4` (source, tests, configs, other docs, `CHANGELOG.md`, `results/`).

---

## 3. Per-correction analysis

### Correction A — `EVAL.md:963-971`

| Field | Content |
|---|---|
| **File changed** | `EVAL.md` |
| **Exact old text** | None — this is a pure insertion. The paragraph it is inserted after (`EVAL.md:954-961`, unchanged, part of `[CORRECTION, eval-spec-v1.8]` item C) ends: `"...replacing the stale 18 / 22. results/sensitivity.md carries the stale 22-cell structure and is regenerated from the registry."` |
| **Exact new text** | `"[CORRECTION, eval-spec-v1.11] The sentence immediately above describes the state at eval-spec-v1.8's own writing — the artifact genuinely carried the stale 22-cell structure at that time. Stage 7.4 (commit 588b6c0) subsequently regenerated results/sensitivity.md from the registry. The artifact now contains 26 cells and states pass mark 21/26. All outcome columns (clamped, invoice CI, rescue CI, win) remain PENDING in every row — no actual sensitivity sweep has been run. This note does not alter the v1.8 sentence it follows; it records that the regeneration it anticipated has since occurred."` |
| **Changes an evaluation metric?** | No. No metric definition (`EVAL.md §5`) is touched. |
| **Changes a success criterion?** | No. `EVAL.md §7`'s five criteria and the `eval-spec-v1.7`/`v1.8` comparator/tie text are not referenced or altered. |
| **Changes comparator/tie rules?** | No. |
| **Changes arm eligibility?** | No. Does not touch the `EVAL.md §7.1` item A five-arm holdout list. |
| **Changes a gate/invariant?** | No. `EVAL.md §5.2` is not referenced. |
| **Changes provenance only?** | Yes. It records that a previously-anticipated regeneration (`results/sensitivity.md` from 22→26 cells) has occurred, citing commit `588b6c0`. It explicitly disclaims altering the sentence it follows: `"This note does not alter the v1.8 sentence it follows."` |
| **Can it affect holdout results?** | No causal mechanism found. The sensitivity sweep is fixed at `sweep.split: dev` (`configs/model_params.yaml:21`, unchanged by this diff) — it is never run against `holdout`. Criterion 1 (invariants) does not depend on this artifact. No cell count, threshold, `[MODEL]` parameter, or magnitude is changed by this text — confirmed by cross-check in Task 6 (the underlying files were already at 26/21 before this note was written). |

### Correction B — `docs/A3-DESIGN.md:850-858`

| Field | Content |
|---|---|
| **File changed** | `docs/A3-DESIGN.md` |
| **Exact old text** | None — pure insertion. Preceding text (`docs/A3-DESIGN.md:843-849`, unchanged) is the §18 sweep-cost-contingency bullet ending: `"...naming which cells were skipped and why."` |
| **Exact new text** | `"[CORRECTION, eval-spec-v1.11] The two bullets above's \"22 cells\" / \"22-cell sweep\" references are read as 26 cells, pass mark 21/26 — the same correction EVAL.md §7.1 item C (eval-spec-v1.8) already made for EVAL.md §6A, extended here to this section, which that correction did not originally sweep. Membership unchanged; no [MODEL] parameter, cell, or magnitude added or removed. results/sensitivity.md was subsequently regenerated from the registry in Stage 7.4 (commit 588b6c0) and now shows 26 cells."` |
| **Changes an evaluation metric?** | No. |
| **Changes a success criterion?** | No. |
| **Changes comparator/tie rules?** | No. |
| **Changes arm eligibility?** | No. |
| **Changes a gate/invariant?** | No. |
| **Changes provenance only?** | Yes. By its own text, it is explicitly the *same* v1.8 correction "extended" to a section the v1.8 amendment "did not originally sweep" — a textual-consistency fix, not a new decision. It explicitly states `"Membership unchanged; no [MODEL] parameter, cell, or magnitude added or removed."` |
| **Can it affect holdout results?** | No causal mechanism found, for the same reasons as Correction A — same sweep, same `dev`-only scope, same unchanged cell membership. |

**Cross-cutting observation:** both corrections are self-consistent with each other (both cite the same `588b6c0` commit and the same 26-cell/21-pass-mark figures) and both are explicit, on their own text, about *not* changing any numeric value, parameter, or rule — only about bringing two pieces of prose in line with an artifact regeneration (`588b6c0`) that both corrections say already happened. Neither correction, on its face or by traced effect, touches anything in `EVAL.md §4` (arms), `§5` (metrics/gates), `§6`/`§6A` (seeds, save for the cell-count figure both already inherited from `eval-spec-v1.8`), or `§7`/`§7.1` (criteria, comparator, tie rule, holdout arm set).

---

## 4. Commit/parent/tag/CHANGELOG evidence on intentionality

```
$ git log -1 --format="%H%n%an <%ae>%n%ad%n%n%B" 4d45db461943978637673a5611a429e0fe826065
4d45db461943978637673a5611a429e0fe826065
sudipt0-paul10 <sudipto.official10@gmail.com>
Sat Aug 29 23:59:55 2026 +0530

Preserve pre-holdout evaluation provenance
```

The commit message names no spec version, no "amendment," no "correction," and no "v1.11." It describes the commit's purpose as preserving provenance (matching the 16 run-artifact JSON files it also adds), not as amending the specification.

```
$ git tag --points-at 125eae8841562f6d5eccab58e055400340e71af6
eval-spec-v1.10

$ git tag --points-at 4d45db461943978637673a5611a429e0fe826065
code-freeze-holdout
```

No tag named `eval-spec-v1.11`, or containing "1.11" in any form, exists in the repository:
```
$ git tag -l | sort -V
code-freeze-holdout
eval-spec-v1
eval-spec-v1.1
eval-spec-v1.2
eval-spec-v1.3
eval-spec-v1.4
eval-spec-v1.6
eval-spec-v1.7
eval-spec-v1.8
eval-spec-v1.9
eval-spec-v1.10
sim-v1
```
(Note, incidental to this investigation but visible in the same listing: `eval-spec-v1.5` also has no tag, despite a `CHANGELOG.md` entry existing for it — the tag sequence has a pre-existing gap unrelated to the v1.10/v1.11 question. Not investigated further here as it is outside this task's scope.)

`CHANGELOG.md` contains no `eval-spec-v1.11` section and is confirmed byte-identical between `125eae8` and `4d45db4` (Task 1). Its newest entry is titled `## eval-spec-v1.10 — fallback-reason taxonomy corrected for executor enforcement — 2026-08-29` (`CHANGELOG.md:3`), and that entry's content concerns only the `fallback_reason` taxonomy (`no_executor_mapping`), not the sensitivity-cell-count topic either correction addresses.

`588b6c0` ("Generate sensitivity artifact from registry"), the commit both corrections cite as already having occurred, itself predates `125eae8`/`eval-spec-v1.10` in the commit graph:
```
$ git log --oneline --reverse 9ab5440^..4d45db4
9ab5440 Wire required stress split and validate deterministic stress invariants
fbe09c6 Correct stress split definition before holdout
588b6c0 Generate sensitivity artifact from registry
125eae8 Correct fallback taxonomy for executor enforcement       <- eval-spec-v1.10
4d45db4 Preserve pre-holdout evaluation provenance                <- code-freeze-holdout
```
So the event described (`588b6c0`) is temporally *before* the `eval-spec-v1.10` tag; the *documentation note* describing that event, and labelling it `eval-spec-v1.11`, was written *after* the `eval-spec-v1.10` tag, in the very next (and, per Task 1, only) commit — which is also the commit `code-freeze-holdout` points to.

**No file in the repository — commit message, `CHANGELOG.md`, tag annotation, or any other document — states that a version `eval-spec-v1.11` was deliberately opened, amended, and intentionally left untagged as part of the pre-holdout freeze process.** The `code-freeze-holdout` tag's own annotation (read at `git show code-freeze-holdout --no-patch`, per the prior Step 0 session) reads: `"pre-holdout implementation/artifact/documentation freeze, eval-spec-v1.10"` — it names `eval-spec-v1.10`, not `v1.11`, as the frozen spec version, even though the commit it points to contains text self-labelled `v1.11`.

---

## 5. On resolving v1.10 vs v1.11

**Not decided here, per instruction.** The evidence above is presented without a determination of which label is authoritative. Two readings are both consistent with the evidence and neither is preferred in this document:

- *Reading X:* the `eval-spec-v1.11` label is a drafting slip — the author meant to write a plain post-freeze note (or reuse the `v1.8` label, since both corrections say they merely "extend" the v1.8 correction) and typed the next sequential version number out of habit, without intending to open a real new spec version. Under this reading, `code-freeze-holdout`'s own tag annotation (which says "eval-spec-v1.10") would be the intended authority, and the two notes are informal commentary that happens to sit inside the frozen commit.
- *Reading Y:* a real `eval-spec-v1.11` amendment was made — content was added to the frozen contract after the `eval-spec-v1.10` tag — and the project's own stated process (`EVAL.md:7`: *"Any change after the tag is a new tagged version with a changelog entry. Results always report the spec version they ran under."*) was not followed for it: no tag was cut and no `CHANGELOG.md` entry was written.

This document does not choose between them.

---

## 6. Cross-check: are the two corrections already reflected elsewhere?

**Yes — the state both corrections describe (26 cells, pass mark 21/26) was already fully in place at `125eae8` (`eval-spec-v1.10`), before either `v1.11`-labelled note was written.** None of the three artifacts that would carry this state were touched by the `125eae8`→`4d45db4` diff:

```
$ git diff 125eae8... 4d45db4... -- results/sensitivity.md
(no output — byte-identical)

$ git diff 125eae8... 4d45db4... -- configs/model_params.yaml
(no output — byte-identical)

$ git diff 125eae8... 4d45db4... -- tests/test_model_params_swept.py
(no output — byte-identical)
```

`results/sensitivity.md` at `4d45db4` already reads:
```
- Pass mark: 21 / 26 cells (ceil of 80%)
...
**Cells won: PENDING / 26. Pass mark 21.**
```
(26 numbered cell rows present, all outcome columns `PENDING` — matches both corrections' description exactly.)

`tests/test_model_params_swept.py:101-128` already asserts:
```python
def test_cell_count_matches_locked_design():
    """26 with the topup toggle off; 28 with it on (DEFECT 1). ..."""
    ...
    expected = 28 if reg.sweep["include_topup_acceleration_cells"] else 26
    assert len(cells) == expected, ...
    ...
    assert required_wins(26, reg) == 21
```

`configs/model_params.yaml` still carries a stale comment at line 33 (`# ceil(0.80 * 22) = 18`) that neither correction touches — the comment predates, and is orthogonal to, both `v1.11` notes; it was already stale under the `eval-spec-v1.8` correction (`EVAL.md §7.1` item C) and remains stale after `4d45db4`, unchanged either way.

**Conclusion for this task:** both `[CORRECTION, eval-spec-v1.11]` notes are narrative-only. They assert that an artifact regeneration (`588b6c0`) already brought `results/sensitivity.md` in line with the `eval-spec-v1.8`-mandated 26-cell/21-pass-mark figures, and every artifact checked (`results/sensitivity.md`, `configs/model_params.yaml`, `tests/test_model_params_swept.py`) confirms that state was already true at the `eval-spec-v1.10` tag commit itself, independent of and prior to the two notes' existence. The notes describe reality; they do not create a new reality that some other file has yet to catch up to.

---

## Summary of findings (evidence only, no resolution offered)

1. `code-freeze-holdout` (`4d45db4`) is exactly one commit past the `eval-spec-v1.10` tag (`125eae8`), and that one commit adds two text passages self-labelled `[CORRECTION, eval-spec-v1.11]` (`EVAL.md:963-971`, `docs/A3-DESIGN.md:850-858`).
2. Both corrections are pure insertions (no prior text removed or altered) and are, by their own content and by independent cross-check against `results/sensitivity.md`/`configs/model_params.yaml`/`tests/test_model_params_swept.py`, provenance/documentation notes only — they touch no metric, criterion, comparator/tie rule, arm eligibility, or gate/invariant, and no numeric value they describe was actually changed by them (it was already in place since before `eval-spec-v1.10`).
3. No tag `eval-spec-v1.11` exists; `CHANGELOG.md` has no `v1.11` entry and is byte-identical between the two commits; the commit message of `4d45db4` does not describe itself as a spec amendment. The `code-freeze-holdout` tag's own annotation names `eval-spec-v1.10`, not `v1.11`, as the frozen version — despite pointing at a commit containing `v1.11`-labelled content.
4. No repository artifact states whether this was an intentional, process-compliant new version left deliberately untagged, or an unintentional labelling slip. Both readings remain open.
