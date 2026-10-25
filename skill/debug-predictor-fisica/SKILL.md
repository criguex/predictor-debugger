---
name: debug-predictor-fisica
description: Re-verify or rerun the pre-registered physics debugger for a learned 3D Navier–Stokes predictor (sqe-private/predictor-debugger). Use when asked to check, re-verify, reproduce or rerun the predictor-debugger evidence, its verdicts H1–H4 or its fingerprint. Never changes thresholds, data, predictions or results.
---

# debug-predictor-fisica

Round 1: `DESIGN.md` (pre-registration, amendments 1–5) → `thresholds.json` → `results/` → `RESULTS.md`.
Round 2: `round2/DESIGN.md` → `round2/thresholds.json` → `round2/results/` → `round2/RESULTS.md`.
The repo is `~/Projects/sqe-private/predictor-debugger`. Everything runs from the repo root with `uv run --locked ...`
(`pyproject.toml` + `uv.lock`: Python 3.9, numpy==1.26.4; torch only in the `train` group).
Fallback without uv: `.venv/bin/python ...` (numpy==1.26.4 only; `python3 -m venv .venv && .venv/bin/pip install numpy==1.26.4`).

## Hard rules

- Do not edit `DESIGN.md`, `thresholds.json`, `results/`, `ledgers/`, `data/`, `preds/` or `checkpoints/`, nor their `round2/` counterparts. The test split has been evaluated, so no threshold, split, check or criterion may change.
- Write anything new to a scratch directory, never over the evidence.
- Report a mismatch as a mismatch. Do not "fix" it by regenerating the canonical files.

## Mode 1 · re-verify the saved evidence

1. `uv run --locked tests/test_checks.py` must print `all checks passed`.
2. Quick (no data needed): `uv run --locked verify.py --saved mac` (and `--saved war`, `--saved guerra`).
   It re-applies `thresholds.json` to the saved per-step statistics, recomputes H1–H4 and prints the fingerprint.
3. Full (needs `data/` and `preds/`, about 2 minutes on the Mac): `uv run --locked verify.py`.
   It checks every input against `MANIFEST.sha256`, recomputes D1–D4 from the saved predictions, re-applies the thresholds and compares the verdicts with `results/mac/verdicts.json`.
4. Expected: H1 0/400, H1b 0/400, H2 400/400, H3 400/400, H4 400/400, `verdicts equal ... True`, fingerprint **EEC9-09E0-F77D**. If this numpy version or the code differ from the recorded run, the fingerprint changes even when the verdicts agree, so say which one differs.

## Mode 2 · rerun from scratch and compare

1. Regenerate the dataset from the seeds into scratch and compare it with the manifest:
   `uv run --locked verify.py --regenerate <scratch>/regen --splits train val test ood --report <scratch>/regeneration.json`.
   On the original Mac this is bit-identical. On other platforms, expect differences near 1e-15; the WAR and GUERRA reports are in `logs/*/regeneration_diff.json`.
2. Recompute the thresholds from validation into scratch, without overwriting:
   `uv run --locked python -m pd.thresholds --data <scratch>/regen --out <scratch>/thresholds.json --stats <scratch>/val.json`, then compare with `thresholds.json`.
3. Retraining P2 needs torch and a GPU (`uv run --locked --group train python -m pd.train ...`): `python -m pd.train --seed 0 --data <dir> --preds <scratch>/preds --checkpoints <scratch>/ckpt --log <scratch>/train_s0.json`. Weights will not be bit-exact across devices (DESIGN allows this). Compare the verdicts, not the floats: run `python -m pd.evaluate --machine rerun --data <dir> --preds <scratch>/preds --results <scratch>/results`. Note that `pd.predictors` must first build P3a/P3b into the same `--preds`.
4. Report each H1–H4 count next to the saved one, plus E1 (share flagged per check, Spearman ρ) next to `RESULTS.md`. Agreement means equal verdicts; it does not mean equal floats.

## Mode 3 · round 2 (ranking gauge G, scale-aware energy check D2p)

Round 2 lives in `round2/` and reads round 1's validation data, thresholds and checkpoints through the link `round2/r1` → repo root
(create it with `ln -s .. round2/r1` if missing). Data, predictions and checkpoints (about 4.5 GB) are not in git; hashes are in `round2/MANIFEST.sha256`.

1. `uv run --locked round2/test_checks2.py` must print `all checks passed`.
2. Quick: `uv run --locked round2/verify.py --saved mac` (and `--saved war`, `--saved guerra`).
3. Full, one action (needs `round2/data/` and `round2/preds/`, about 12 minutes on the Mac): `uv run --locked round2/verify.py`.
4. Compare with `round2/RESULTS.md`: H1–H8 verdicts, the cluster-bootstrap intervals of H7/H8 and the round-2 fingerprint printed there.
   Regenerating the round-2 splits: `uv run --locked round2/verify.py --regenerate <scratch>/regen --report <scratch>/regeneration.json`.

## Output

A short table: check → saved value → value now → same/different. Then the fingerprint and any manifest problems. Use the plain wording of `RESULTS.md`, and add no claims beyond it.
