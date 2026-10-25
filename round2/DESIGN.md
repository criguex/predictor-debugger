# Pre-registration · Round 2 · Ranking and out-of-distribution energy checks

Written on 2026-10-25 (UTC) before any round-2 evaluation data exists: no test or out-of-distribution trajectory with the seeds below has been generated, and no predictor has been run on them. Round 1 (`DESIGN.md`, `RESULTS.md`, `thresholds.json`, `results/`, `ledgers/` at `f1080ed`) is frozen and is not edited. Changes after this commit are numbered amendments at the end, each saying whether it was made before or after the round-2 test data was seen.

## Why a second round

Round 1 passed H1–H4 on three machines, but showed two weaknesses that its in-distribution hypotheses could not test:

1. **Ranking.** On P2 (FNO, about 1 % one-step error) D1 and D3 flag every step, yet Spearman ρ(D3, D4) is −0.19 (seed 0) and +0.06 (seed 1). The debugger says P2 is wrong, not which steps are worse.
2. **D2 out of distribution.** 126 false-positive entries, all D2 on the exact solver (P0, P0f32) on k₀ = 5 flows, values 3.32e-3–4.77e-3 against τ = 3.31e-3, explained by hand as error of D2's own trapezoid over Δ = 0.1.

Round 2 asks whether two new statistics, fixed below, remove these weaknesses on data the debugger has never seen.

## Pilot on round-1 data (already seen), disclosed

Before writing this file, the candidate statistics were computed on round-1 data only: validation (P0, P0f32), test (all one-step predictors) and OOD (P0, P0f32, P2 seed 0, P3b). Those splits were already seen in round 1, so this pilot cannot leak round-2 evaluation data, but it did shape the choices below. Code `round2/pilot.py`, output `round2/pilot/pilot_summary.json` (per step: `pilot_rows.json`).

| Pilot result (round-1 data) | Value |
| --- | --- |
| ρ(D3, D4), P2 seeds 0 / 1, round-1 test | −0.185 / +0.056 |
| ρ(D3p, D4): D3 on the Leray-projected prediction, still divided by ‖N(u₀)‖ | −0.209 / +0.046 |
| ρ(Gs, D4): solenoidal part of the Hermite residual, in state units | +0.843 / +0.944 |
| ρ(G, D4): full Hermite residual, in state units | +0.932 / +0.976 |
| P0 on round-1 OOD k₀ = 5: max D2 / max D2h / max D2p | 4.77e-3 / 6.21e-5 / −1.19e-6 |
| P0 on round-1 validation: max D2h / max D2p | 1.66e-6 / −9.25e-5 |

What the pilot changed in the plan:

- The suspected cause of weakness 1 (D3 dominated by the non-solenoidal part of the prediction) is **not** supported: projecting first (D3p) leaves ρ near zero. What breaks the ranking is D3's normaliser ‖N(u₀)‖, which changes from step to step independently of the error. Expressing the residual in state units (times Δ, divided by ‖u₁‖) restores the ranking; the higher-order quadrature and the compressive part add a little more. The projected D3p is kept as an exploratory comparison only.
- A higher-order energy budget alone (D2h) does not remove weakness 2: its residual on k₀ = 5 (6.21e-5) is 37 times its validation maximum, so the round-1 rule (10 × validation maximum) would still flag the exact solver. The pre-registered D2′ below subtracts the size of the quadrature correction, which is a scale-aware bound on the remaining quadrature error.
- The pass criteria of H7 and H8 were written after seeing the pilot's ρ on round-1 test (0.93 / 0.98). They are set at levels that mean "a usable severity gauge" (ρ ≥ 0.8 within one predictor, ρ ≥ 0.9 across a graded set) and are judged only on fresh trajectories.

## New statistics

All arithmetic is float64 (`<f8`, FFTs in complex128), as in round 1. Notation as in round 1: û the full, unmasked FFT of a field, N(û) the solver's `rhs(û, ν)` (projected and masked), Δ = 0.1, E and Z energy and enstrophy as in `pd/checks.py`. The code is `round2/checks.py`; it imports round 1's `statistics` unchanged and adds:

- **Time derivative of the tendency, exact.** Along the flow, Ṅ(û) = dN/dt = ½ [N(û + N(û)) − N(û − N(û))]. N is a quadratic polynomial in û (the projection and mask are linear), so this central difference is exact, not an approximation.
- **Enstrophy rate.** Ż(û) = ⟨curl(û) · curl(N(û))⟩ (grid mean), so that dZ/dt = Ż along the flow.
- **Hermite-corrected (Euler–Maclaurin) trapezoid**: ∫₀^Δ f dt = Δ/2 (f₀ + f₁) + Δ²/12 (ḟ₀ − ḟ₁) + O(Δ⁵).

| Id | Name | Statistic |
| --- | --- | --- |
| D2h | Energy budget, fourth order | \|R₄\| / E(u₀), with R₂ = E(u₁) − E(u₀) + νΔ (Z(u₀) + Z(u₁)) (round 1's residual, signed), C = νΔ²/6 (Ż(u₀) − Ż(u₁)), R₄ = R₂ + C |
| **D2p** (D2′) | Energy budget beyond its own quadrature error | (\|R₄\| − \|C\|) / E(u₀). Since \|R₄\| − \|C\| ≤ min(\|R₂\|, \|R₄\|), a step is charged only for the part of the residual that neither rule's quadrature error explains. Can be negative. |
| **G** | Severity gauge, momentum residual in state units | Δ ‖r‖₂ / ‖û₁‖₂, with r = (û₁ − û₀)/Δ − ½ (N₀ + N₁) − Δ/12 (Ṅ₀ − Ṅ₁) |
| Gs, Gc | Solenoidal and compressive parts of G | Δ ‖P r‖ / ‖û₁‖ and Δ ‖(I − P) r‖ / ‖û₁‖, with P the solver's `project` (Leray projection and 2/3 mask). Gs² + Gc² = G² (orthogonal split). Exploratory. |
| D3p | User's candidate, kept as comparison | ‖P((û₁ − û₀)/Δ − ½ (N₀ + N₁))‖ / ‖N₀‖. Exploratory. |
| D4s, D4c | Solenoidal and compressive parts of D4 | ‖P(û₁ − û₁^ref)‖ / ‖û₁^ref‖, ‖(I − P)(û₁ − û₁^ref)‖ / ‖û₁^ref‖. Not debugger checks. |

For an exact step G is the fourth-order truncation of the time quadrature; for a prediction u₁ = u₁^ref + δ, Δ r ≈ (I − Δ/2 J) δ plus that truncation, so G estimates D4 from u₀ and u₁ alone, without the reference.

**The round-2 debugger** is D1 and D3 (round 1, unchanged, with round 1's thresholds) plus **D2p in place of D2**. A step is flagged by D2p if D2p > τ_D2p, or D2p is non-finite, or E(u₁) > E(u₀) (round 1's hard rule, unchanged), or E(u₀), E(u₁) is non-finite. `D2p_mag` is the same flag without the energy-increase rule. G is a gauge, not a pass/fail check; an exploratory flag G > τ_G is reported.

## Thresholds, fixed now

Computed once, on validation only, by `round2/thresholds.py`, written to `round2/thresholds.json` and committed before any round-2 test or OOD data exists.

- **Validation reuses round 1's validation split** (seeds 160–179, k₀ = 3, files hashed in round 1's `thresholds.json`). Why: thresholds come only from P0 and P0f32, which are exact by construction, so having seen these trajectories cannot bias them; keeping the same split makes D1–D3 directly comparable with round 1 (`round2/thresholds.py` recomputes round 1's three thresholds and records whether they are equal); and it adds no data. P2 also used these trajectories for early stopping, which does not touch the thresholds.
- τ_D2p = max(10 × max over validation of D2p for P0 and P0f32, 10 × eps(float32) = 1.19e-6). The floor is the float32 precision floor of amendment 1: below it a float32 predictor's energy budget cannot be resolved. In the pilot the validation maximum is negative, so the floor is expected to decide.
- τ_G = max(10 × max over validation of G for P0 and P0f32, 1e-12). Exploratory flag only.
- D1, D2, D3 use round 1's `thresholds.json` (SHA-256 `77bfdca0…ad32eb`) unchanged.

## Splits and seeds

Round 1 used seeds 0–219, 300–319 and Taylor–Green; P3a's phases use identity 1000 for Taylor–Green. Round 2 uses only seeds never used before:

| Split | Seeds | k₀ | Steps (one-step) | Use |
| --- | --- | --- | --- | --- |
| Train, validation | 0–159, 160–179 (round 1) | 3 | — | Graded training below; calibration |
| `r2test` | 2000–2039 | 3 | 400 | Hypotheses H1–H8 |
| `r2ood5` | 2100–2119 | 5 | 200 | H5 (the round-1 failure regime) |
| `r2ood6` | 2200–2219 | 6 | 200 | H5, harder: faster decay, larger quadrature error; spectrum peaks at k = 6 against the mask edge 32/3 |

Same generator, solver, ν = 0.05, n = 32, Δ = 0.1, 10 steps per trajectory as round 1. Taylor–Green is not used (already seen). No rollout (E2) in round 2.

## Predictors

On every round-2 split: P0, P0f32, P1, P2 seed 0, P2 seed 1 (round 1's checkpoints `checkpoints/P2s{0,1}.pt`, unchanged, inference on WAR), P3a and P3b (round 1's definitions, built from P2 seed 0's round-2 predictions on the Mac).

**Graded set, for ranking across severity** (`r2test` only): one new training of P2 with the round-1 recipe and **torch seed 2** on WAR (CUDA, float32), keeping the weights after epochs **1, 2, 4 and 8** and the best-validation weights (labels P2ge1, P2ge2, P2ge4, P2ge8, P2gbest). If early stopping ends the run before epoch 8, the missing labels are reported missing and H8 uses the ones that exist. Code `round2/predict.py`.

## Hypotheses and criteria (fresh data)

| Id | Hypothesis | Pass if |
| --- | --- | --- |
| H1, H1b, H2, H3, H4 | Round 1 replicates on fresh test, round-1 checks and thresholds | Same criteria as round 1, on `r2test` |
| **H5** | D2p does not flag the exact solver, in or out of distribution | P0 and P0f32 flagged by D2p on **0** steps in each of `r2test`, `r2ood5`, `r2ood6` (1,600 control steps) |
| **H6** | D2p still catches energy injection by magnitude alone | P3b flagged by `D2p_mag` (without the energy-increase rule) on ≥ 95 % of `r2test` steps |
| **H7** | G ranks errors within one learned predictor | For **each** of P2 seed 0 and seed 1 on `r2test`: Spearman ρ(G, D4) ≥ 0.8 **and** the lower end of its 95 % cluster-bootstrap interval ≥ 0.6 |
| **H8** | G ranks errors across a graded set of learned predictors | Pooled over P2ge1, P2ge2, P2ge4, P2ge8, P2gbest on `r2test`: ρ(G, D4) ≥ 0.9 **and** the lower end of its 95 % interval ≥ 0.8 |

**Cluster bootstrap:** steps within a trajectory are not independent, so trajectories are resampled with replacement (40 per replicate; for H8 each resampled trajectory brings its steps from all graded predictors), 2,000 replicates, `numpy.random.default_rng(20261024)`, Spearman with average ranks (round 1's function), percentile interval 2.5–97.5 %. A replicate with a non-finite ρ is dropped and counted.

**Exploratory, no pass/fail:** old D2 against D2p on P0/P0f32 per split (the false-positive comparison); ρ of G, Gs, D3, D3p, D2, D2p against D4 for every P2 group (including OOD and each graded predictor), with intervals for D3, D3p and Gs; median G/D4; D2p and G flag rates on every predictor; D1/D3 flags on the controls out of distribution.

**What counts as a false positive:** any flag raised on P0 or P0f32 (correct by construction) by D1, D2, D3, D2p or G, on any split and machine. Every such flag goes to `round2/ledgers/false_positives.jsonl` as `open`; the ledger marks whether the check belongs to the round-2 debugger (G does not). An entry is closed only with written evidence in `round2/RESULTS.md`. H5 counts D2p flags only; D1/D3/old-D2 flags on OOD controls are reported, not hidden.

Any failure of H1–H8 is reported as a failure. No threshold, split, statistic or criterion is changed to turn a failure into a pass.

## Machines and evidence

Same three machines and roles as round 1 (amendments 2 and 3), in a new folder `C:\ADN\pd-exp-r2` on WAR and GUERRA, using `C:\ADN\voz\venv` read-only, deleted at the end with a cleanup log. Windows C: free space is checked before copying (WAR 55.9 GB, GUERRA 85.8 GB free at 2026-10-25T01:00Z).

| Machine | Role |
| --- | --- |
| Mac mini | Generates the round-2 splits (canonical), calibrates, builds P3a/P3b, runs the debugger on everything, ledgers |
| WAR (RTX 5070) | P2 seed 0/1 inference on the round-2 splits; graded training (seed 2) and its predictions; regenerates the round-2 splits from the seeds and reports the difference; runs the debugger independently |
| GUERRA (RTX 4060) | Regenerates the round-2 splits and reports the difference; runs the debugger independently. No training |

- Every transfer is hashed at both ends in `round2/logs/transfers.tsv` (round 1's `tools/sync.py`, pointed at the new folder).
- Remote machines apply the Mac's `round2/thresholds.json`.
- **Discrepancy ledger** `round2/ledgers/discrepancies.jsonl`: every step and flag (D1, D2, D3, D2p, D2p_mag, G, any, any2) whose verdict differs between machines.
- `round2/verify.py` re-applies the thresholds to saved statistics (`--saved MACHINE`) or recomputes everything from the saved predictions, recomputes H1–H8 and prints a round-2 fingerprint over code, inputs listed in `round2/MANIFEST.sha256` and verdicts. On the Mac the one-action check is `uv run --locked round2/verify.py`. `round2/thresholds.json` records the SHA-256 of `uv.lock`.
- Every step is committed with its time; `round2/logs/mac/timeline.log` keeps UTC times of each stage.
- Data, predictions and checkpoints stay out of git (hashes in the manifest). Round 2 stays under 10 GB on the Mac.

## Limits stated in advance

The same box, viscosity, horizon and architecture as round 1. H7/H8 test ranking against D4 on one-step predictions only. D2p's subtraction of \|C\| trades sensitivity for robustness: an energy error smaller than the step's quadrature correction cannot be seen. The pilot used round-1 data that also contains the P2 checkpoints evaluated here; only the round-2 trajectories are new.

## Amendments
