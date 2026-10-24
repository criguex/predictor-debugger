# Results · Physics debugger for a learned flow predictor

Run on 2026-10-24 under `DESIGN.md` with amendments 1–5. Amendment 5 (implementation choices) was committed before any data existed. The thresholds were committed (`fd33dd3`, `thresholds.json` SHA-256 `77bfdca0…ad32eb`) before any prediction on the test split existed and before the debugger saw the test split. Nothing was changed after the test evaluation.

## Pre-registered hypotheses (test split, 400 one-step predictions each)

| Id | Criterion | Mac | WAR | GUERRA | Result |
| --- | --- | --- | --- | --- | --- |
| H1 | P0 flagged on ≤ 5 % | 0/400 | 0/400 | 0/400 | pass |
| H1b | P0f32 flagged on ≤ 5 % | 0/400 | 0/400 | 0/400 | pass |
| H2 | P3a flagged by D1 on ≥ 95 % | 400/400 | 400/400 | 400/400 | pass |
| H3 | P3b flagged by D2 on ≥ 95 % | 400/400 | 400/400 | 400/400 | pass |
| H4 | P1 flagged by D3 on ≥ 95 % | 400/400 | 400/400 | 400/400 | pass |

The three machines gave the same verdict on every step of every predictor and split: the discrepancy ledger is empty. The largest difference in any statistic between machines was 2.8e-17 (D1) and 4.4e-16 (D3); D2, D4, E(u₀) and E(u₁) were bit-identical. `verify.py` prints the same fingerprint on all three: **EEC9-09E0-F77D**. A full recomputation on the Mac (`logs/mac/verify_recompute.log`) gives the same verdicts and the same fingerprint.

These controls were easy to separate. On the test split, the margins between control and threshold were large:

| Check | τ (P0 + P0f32, validation) | τ float64 only (secondary) | P0 test max | P0f32 test max | negative control, test median |
| --- | --- | --- | --- | --- | --- |
| D1 | 8.32e-7 | 1e-12 (floor) | 8.1e-16 | 8.4e-8 | P3a: 6.5e-2 |
| D2 | 3.31e-3 | 3.31e-3 | 3.4e-4 | 3.4e-4 | P3b: 9.7e-2 |
| D3 | 8.35e-2 | 8.35e-2 | 8.2e-3 | 8.2e-3 | P1: 1.00 |

Precision floor (amendment 1): every D1 value of P0 (below 10 × eps64 = 2.2e-15) and of P0f32 (below 10 × eps32 = 1.19e-6) is at the precision floor of its dtype, so these are not measured values. The D1 threshold of 8.32e-7 is therefore ten times a float32 rounding level, not a physical measurement. The float64-only threshold for D1 hits the 1e-12 floor. On D2 and D3, float32 costs nothing: both tables agree to 6 digits, because truncation error in the checks dominates there.

## The learned predictor P2 (exploratory, no pass/fail)

Training on WAR (RTX 5070, CUDA, float32, torch 2.7.0+cu128), fixed architecture, 4,724,675 parameter elements (complex weights counted once):

| Seed | Best epoch | Epochs run | Best validation MSE | Training time |
| --- | --- | --- | --- | --- |
| 0 | 14 | 24 | 5.37e-6 | 102.6 s |
| 1 | 22 | 32 | 5.42e-6 | 136.8 s |

**E1, test split** (same on all three machines):

| | D1 flagged | D2 flagged | D3 flagged | any | D4 median | Spearman ρ(D3, D4) |
| --- | --- | --- | --- | --- | --- | --- |
| P2 seed 0 | 100 % | 0 % | 100 % | 100 % | 1.06 % | −0.185 (n = 400) |
| P2 seed 1 | 100 % | 0 % | 100 % | 100 % | 1.05 % | +0.056 (n = 400) |

The debugger rejects every P2 step, mainly because the network's output is not divergence-free (D1 median 8.0e-3 against τ 8.3e-7) and because its time derivative does not match the equations (D3 median 0.16 against τ 0.084). D2 never fires: P2 does not inject energy, and its energy-budget errors stay below τ. Within P2, D3 does not rank errors: ρ is near zero for both seeds, so it says that P2 is wrong but not which steps are worse.

**Confusion table, test split, "truly wrong" = D4 > 1 %** (same on all three machines):

| Seed | Check | flagged and wrong | flagged, not wrong | wrong, not flagged | neither |
| --- | --- | --- | --- | --- | --- |
| 0 | D1, D3, any | 301 | 99 | 0 | 0 |
| 0 | D2 | 0 | 0 | 301 | 99 |
| 1 | D1, D3, any | 317 | 83 | 0 | 0 |
| 1 | D2 | 0 | 0 | 317 | 83 |

P2's error sits right at the 1 % line, so this table mostly measures where that line falls. The 99 (seed 0) and 83 (seed 1) "flagged, not wrong" steps have D4 between 0.82 % (seed 0) or 0.86 % (seed 1) and 1 %, yet they still break incompressibility at the 1e-2 level.

**E2, rollouts from the 40 test initial states** (seed 0; seed 1 is similar, see `results/mac/verdicts.json`): D4 median grows from 1.05 % at step 1 to 4.8 % at step 10. D1 (about 1e-2) and D3 (about 0.10) stay flat and do not accumulate, and D2 stays below τ. Every rollout step is flagged by D1 and D3. The checks catch that the rollout breaks the physics at every step, but they do not track how the error grows.

## Out of distribution (k₀ = 5 plus Taylor–Green, reported separately, no pass/fail)

- P0 and P0f32 are flagged by D2 on 21 of 210 steps, on all three machines (126 false-positive ledger entries = 21 steps × 2 predictors × 3 machines). The flagged steps are step 0 of each of the 20 k₀ = 5 trajectories plus step 1 of seed 301. The values run from 3.32e-3 to 4.77e-3 against τ = 3.31e-3. Taylor–Green is never flagged.
- P1, P3a and P3b are flagged on every OOD step. P2 is flagged by D1 and D3 on every step, and by D2 on 84/210 (seed 0) and 75/210 (seed 1), with D4 median about 4 %.

## Ledgers

- `ledgers/discrepancies.jsonl`: **0 entries** (every split, every predictor, every check, three machines).
- `ledgers/false_positives.jsonl`: **126 entries, all OOD D2 on P0/P0f32, none on test or validation.** In the file, all 126 are `open`, because amendment 5's automatic precision-floor rule does not apply to any of them.
- **Explanation by evidence, applied here by hand as amendment 5 requires.** `tools/fp_diagnostic.py` (output in `results/fp_diagnostic.json`) recomputes the exact solver's energy budget for the 21 flagged steps with finer trapezoid intervals. The residual falls by a factor of 3.96–3.98 at each halving, as second-order quadrature error should: the maximum is 4.77e-3 at h = 0.1, 1.20e-3 at h = 0.05, 1.9e-4 at h = 0.02 and 4.8e-5 at h = 0.01. So the flags come from the D2 statistic's own trapezoid over Δ = 0.1, which the faster k₀ = 5 decay makes larger than the k₀ = 3 calibration allowed, and not from the solver. The diagnostic was run on P0, on the Mac. The P0f32 entries cover the same 21 steps, with D2 within 0.22 % of P0's value, and the values are bit-identical across machines. **Counted this way: 0 open, 126 explained.** Counted strictly from the ledger file: 126 open. Either way, D2's threshold does not carry over to a faster-decaying flow without recalibration.

## Reproducibility across machines

| Item | WAR | GUERRA |
| --- | --- | --- |
| Regenerated from seeds, bit-identical to the Mac | 0 / 241 | 0 / 81 (val, test, OOD) |
| Max absolute difference against the Mac's files | 8.9e-16 | 7.2e-16 |
| Debugger wall time (all predictors, splits, rollouts) | 257 s | 704 s (Mac: 126 s) |
| `tests/test_checks.py` | passed | passed |

Because no regenerated file was bit-identical, the Mac's canonical files were transferred, and both machines ran the debugger on them. The regenerated copies were used only for the difference report (`logs/war/regeneration_diff.json`, `logs/guerra/regeneration_diff.json`). numpy was 1.26.4 everywhere; Python 3.9.6 (Mac), 3.12.10 (WAR), 3.12.3 (GUERRA).

Transfers (`logs/transfers.tsv`, 1,225 rows, SHA-256 checked at both ends):

| Direction | Files | Bytes | Retries | Failed |
| --- | --- | --- | --- | --- |
| Mac → WAR | 430 | 3.36 GB | 0 | 0 |
| Mac → GUERRA | 511 | 3.88 GB | 0 | 0 |
| WAR → Mac | 272 | 1.98 GB | 0 | 0 |
| GUERRA → Mac | 12 | 3 MB | 0 | 0 |

`C:\ADN\pd-exp\` was deleted on WAR (935 files, 7.4 GB) and GUERRA (606 files, 4.6 GB) after every output had been pulled and verified (`logs/war/cleanup.log`, `logs/guerra/cleanup.log`). WAR's free space was 69.0 GB at the start, 52.6 GB just before cleanup and 60.0 GB after it. The remaining 9 GB drop is not from this experiment's folder, which is gone.

## What did not go as designed, or was not done

- Amendment 1 assumed MPS training. Amendment 2 moved training to WAR's CUDA, and no MPS run was made.
- No regenerated dataset was bit-identical on Windows. Per amendment 4 this is reported, and the Mac's files stayed canonical.
- The OOD false positives above show a weakness in D2's calibration that the in-distribution hypotheses could not reveal.
- P2's checks D1 and D3 flag every step. The experiment shows the debugger separating its controls, but it does not show the debugger telling a better learned predictor from a worse one: ρ(D3, D4) is about 0, and D2 misses every P2 error.
- Bit-exact network weights across devices were not attempted (DESIGN does not require them). P2 was trained once per seed, on WAR only.

## Limits (from DESIGN, unchanged)

A 32³ periodic box, smooth random initial fields, a short horizon, one architecture and no forcing. This says nothing about Clay's problem, about OpenAI's proof, or about real turbulence. A debugger that passes here is evidence about these checks on this setup only.

## Files

`DESIGN.md` (pre-registration and amendments) · `thresholds.json` · `MANIFEST.sha256` (dataset, predictions, checkpoints, thresholds) · `environment.json` · `results/{mac,war,guerra}/` (per-step statistics, verdicts, environments) · `results/comparison.json` · `results/fp_diagnostic.json` · `ledgers/` · `logs/` · `verify.py`. Data, predictions and checkpoints (about 5 GB) are not in git; their hashes are in `MANIFEST.sha256`.
