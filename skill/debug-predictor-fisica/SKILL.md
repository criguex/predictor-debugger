---
name: debug-predictor-fisica
description: Re-verify or rerun the pre-registered physics debugger for a learned 3D Navier–Stokes predictor (sqe-private/predictor-debugger). Use when asked to check, re-verify, reproduce or rerun the predictor-debugger evidence, its verdicts H1–H4 or its fingerprint. Never changes thresholds, data, predictions or results.
---

# debug-predictor-fisica

Pipeline: `DESIGN.md` (pre-registration, amendments 1–5) → `thresholds.json` → `results/` → `RESULTS.md`.
The repo is `~/Projects/sqe-private/predictor-debugger`. Everything runs from the repo root with `.venv/bin/python`
(Python 3.9+, numpy==1.26.4 only; create it with `python3 -m venv .venv && .venv/bin/pip install numpy==1.26.4` if missing).

## Hard rules

- Do not edit `DESIGN.md`, `thresholds.json`, `results/`, `ledgers/`, `data/`, `preds/` or `checkpoints/`. The test split has been evaluated, so no threshold, split, check or criterion may change.
- Write anything new to a scratch directory, never over the evidence.
- Report a mismatch as a mismatch. Do not "fix" it by regenerating the canonical files.

## Mode 1 · re-verify the saved evidence

1. `.venv/bin/python tests/test_checks.py` must print `all checks passed`.
2. Quick (no data needed): `.venv/bin/python verify.py --saved mac` (and `--saved war`, `--saved guerra`).
   It re-applies `thresholds.json` to the saved per-step statistics, recomputes H1–H4 and prints the fingerprint.
3. Full (needs `data/` and `preds/`, about 2 minutes on the Mac): `.venv/bin/python verify.py`.
   It checks every input against `MANIFEST.sha256`, recomputes D1–D4 from the saved predictions, re-applies the thresholds and compares the verdicts with `results/mac/verdicts.json`.
4. Expected: H1 0/400, H1b 0/400, H2 400/400, H3 400/400, H4 400/400, `verdicts equal ... True`, fingerprint **EEC9-09E0-F77D**. If this numpy version or the code differ from the recorded run, the fingerprint changes even when the verdicts agree, so say which one differs.

## Mode 2 · rerun from scratch and compare

1. Regenerate the dataset from the seeds into scratch and compare it with the manifest:
   `.venv/bin/python verify.py --regenerate <scratch>/regen --splits train val test ood --report <scratch>/regeneration.json`.
   On the original Mac this is bit-identical. On other platforms, expect differences near 1e-15; the WAR and GUERRA reports are in `logs/*/regeneration_diff.json`.
2. Recompute the thresholds from validation into scratch, without overwriting:
   `.venv/bin/python -m pd.thresholds --data <scratch>/regen --out <scratch>/thresholds.json --stats <scratch>/val.json`, then compare with `thresholds.json`.
3. Retraining P2 needs torch and a GPU: `python -m pd.train --seed 0 --data <dir> --preds <scratch>/preds --checkpoints <scratch>/ckpt --log <scratch>/train_s0.json`. Weights will not be bit-exact across devices (DESIGN allows this). Compare the verdicts, not the floats: run `python -m pd.evaluate --machine rerun --data <dir> --preds <scratch>/preds --results <scratch>/results`. Note that `pd.predictors` must first build P3a/P3b into the same `--preds`.
4. Report each H1–H4 count next to the saved one, plus E1 (share flagged per check, Spearman ρ) next to `RESULTS.md`. Agreement means equal verdicts; it does not mean equal floats.

## Output

A short table: check → saved value → value now → same/different. Then the fingerprint and any manifest problems. Use the plain wording of `RESULTS.md`, and add no claims beyond it.
