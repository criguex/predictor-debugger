# Pre-registration · Round 3 · Sensitivity floor, a scale-aware alarm, and rollouts

Written on 2026-10-25 (UTC) before any round-3 evaluation data exists: no trajectory with the seeds below has been generated, no network has been run on them, and no round-3 threshold has been computed. Rounds 1 (`DESIGN.md`, `RESULTS.md`, …) and 2 (`round2/`) are frozen and are not edited; their fingerprints EEC9-09E0-F77D and D506-F58F-3838 must still verify at the end. Changes after this commit are numbered amendments at the end, each saying whether it was made before or after the round-3 test data was seen.

## Why a third round

Round 2 passed H1–H8 but left three weaknesses open:

1. **D2′'s sensitivity floor.** D2′ = (|R₄| − |C|)/E₀ subtracts the step's own quadrature correction |C|, so an energy error smaller than |C| cannot be seen. That floor was stated, never measured.
2. **G is not an alarm out of distribution.** With its validation threshold, G flags the exact solver at step 0 of all twenty k₀ = 6 trajectories (round-2 RESULTS). G was a gauge, not a check.
3. **No rollouts.** Real use chains a network's own predictions. Round 2 only scored one-step predictions.

And one weakness of round 2's own design: H8 passed, but round 1's D3 would have passed it too. In this round **every ranking or alarm hypothesis names a comparator that should fail it**; a pass where the comparator also passes is reported as NON-DISCRIMINATIVE, not as a pass.

## Pilot on already-seen data, disclosed

Before writing this file, the new statistics below were computed on data that rounds 1 and 2 had already evaluated: round-1 validation (P0, P0f32), round-2 `r2test` (all seven one-step predictors), `r2ood5` and `r2ood6` (P0, P0f32), round-1's 10-step rollouts of P2 seeds 0 and 1 (test seeds 180–219), and the energy and momentum sweeps below on `r2test` and `r2ood6`. Code `round3/pilot.py`, output `round3/pilot/` (rows, sweep, `pilot_summary.json`), log `round3/logs/mac/pilot*.log`. The pilot's momentum sweep was run before D3 was added to it, so it has no D3 column. The pilot shaped the choices below; it cannot leak round-3 data, which does not exist yet. A smoke run of `round3/evaluate.py` on a few already-seen trajectories (round-2 seeds standing in for the round-3 splits, round-1 10-step rollouts standing in for `r3roll`, placeholder thresholds) only exercised the code path; its outputs were not kept.

| Pilot result (seen data) | Value |
| --- | --- |
| Candidate thresholds from round-1 validation (rule below) | τ_D2″ = 1.19e-6 (float32 floor), τ_G′ = 1.19e-6 (float32 floor), τ_G6 = 7.11e-7 |
| Max over P0/P0f32 of D2″ on val / r2test / r2ood5 / r2ood6 | −3.6e-8 / −3.5e-8 / −1.1e-6 / −2.3e-6 → 0 flags |
| Max over P0/P0f32 of G′ on the same splits | −1.7e-7 / −1.7e-7 / −5.5e-7 / −8.4e-7 → 0 flags |
| G6 (sixth-order residual, no subtraction) with τ_G6 | flags 16/200 control steps on r2ood5 and 40/200 on r2ood6 |
| G′ flags on r2test: P1 / P3a / P3b / P2s0 / P2s1 | 400 / 400 / 400 / 400 / 400 of 400 |
| ρ(G′, D4) on r2test, P2s0 / P2s1 (cluster 95 % CI) | 0.932 [0.922, 0.940] / 0.973 [0.966, 0.978]; D3: −0.205 / +0.029 |
| Energy floor (uniform scaling, ±), r2test: D2 / D2′ / D2″ | +3.2e-3, −1.0e-2 / ±3.2e-4 / ±3.2e-6 |
| Energy floor, r2ood6: D2 / D2′ / D2″ | baseline false-positive rate 40 % / ±1.0e-2 / ±3.2e-4 |
| Momentum floor (random solenoidal error), r2test / r2ood6: G / G6 / G′ | 1e-4, 1e-4 (baseline FP 10 %) / 1e-6, 1e-6 / 1e-5, 3.2e-4 |
| Rollouts (10 steps): within-step ρ(A_k, D4_k), mean over k, P2s0 / P2s1 | 0.726 / 0.749, falling from 0.99 at k = 1 to 0.51–0.55 at k = 10 |
| Same with the comparator C_k (cumulative D3) | 0.653 / **0.835** |
| A_k / D4_k at the first step where D4 > 5 % (44 crossings) | 1.39–1.76, median 1.47 |
| Alarm A_k ≥ 5 %: on time / premature (D4 < 2.5 % at the alarm) | 44/44 on time, 0/80 premature; round-2 debugger any2: 44/44 on time, 80/80 premature |

What the pilot changed or predicts:

- A higher-order rule alone does not make G an alarm: G6 still flags the exact solver on k₀ = 5 and 6 (as D2h did for energy in round 2). The scale-aware subtraction is what removes those flags, so G′ is pre-registered, G6 is exploratory.
- The rollout tracking hypothesis H14 is written with a fixed criterion before seeing fresh data, although the pilot (10 steps) sits only just above it and shows the ranking decaying with time; over the 20-step horizon here it may well fail. The pilot also shows the cumulative-D3 comparator ranking well for one network, so H14 may come out NON-DISCRIMINATIVE. Both outcomes will be reported as they come.
- A_k overestimates D4_k by about 1.5 at the crossing, so an alarm at A_k ≥ 5 % should come early but not too early; the premature rule (D4 < 2.5 % when the alarm fires) is set so that a factor-2 overestimate still counts as on time.

## New statistics

Float64 everywhere (`<f8`, complex128 FFTs), as in rounds 1–2. Notation of round 2: û the full unmasked FFT, N = the solver's `rhs(û, ν)`, Δ = 0.1. Code `round3/checks.py`, which imports round 1's and round 2's statistics unchanged and adds:

- **Second time derivative of the tendency, exact.** N is a quadratic polynomial in û, N(x) = Lx + B(x, x) with L linear and B symmetric bilinear (projection and mask included). Along the flow, Ṅ = LN + 2B(u, N) (round 2) and N̈ = LṄ + 2B(u, Ṅ) + 2B(N, N) = ½[N(u + Ṅ) − N(u − Ṅ)] + N(N) + N(−N). Exact, no step size.
- **Enstrophy acceleration.** Z̈ = ⟨|curl N|²⟩ + ⟨curl u · curl Ṅ⟩ (grid means), so that d²Z/dt² = Z̈ along the flow.
- **Sixth-order two-point Hermite rule**: ∫₀^Δ f = Δ/2 (f₀ + f₁) + Δ²/10 (ḟ₀ − ḟ₁) + Δ³/120 (f̈₀ + f̈₁) + O(Δ⁷).

| Id | Name | Statistic |
| --- | --- | --- |
| D2h6 | Energy budget, sixth order | \|R₆\|/E₀, R₆ = R₂ + νΔ²/5 (Ż₀ − Ż₁) + νΔ³/60 (Z̈₀ + Z̈₁) (R₂, R₄, C as in round 2) |
| **D2pp** (D2″) | Energy budget beyond its sixth-order correction | (\|R₆\| − \|R₆ − R₄\|)/E₀. As for D2′, \|R₆\| − \|R₆ − R₄\| ≤ min(\|R₄\|, \|R₆\|); the allowance is now the size of the fourth-to-sixth-order correction (≈ \|R₄\| of an exact step) instead of the second-to-fourth (≈ \|R₂\|). Can be negative. |
| G6 | Momentum residual, sixth order | Δ‖r₆‖/‖û₁‖, r₆ = (û₁ − û₀)/Δ − ½(N₀ + N₁) − Δ/10 (Ṅ₀ − Ṅ₁) − Δ²/120 (N̈₀ + N̈₁). Exploratory. |
| **Gp** (G′) | Scale-aware alarm | Δ(‖r₆‖ − ‖r₆ − r₄‖)/‖û₁‖, r₄ round 2's Hermite residual (so G = Δ‖r₄‖/‖û₁‖). The subtracted term T = Δ‖r₆ − r₄‖/‖û₁‖ = G6 − G′ is the size of G's own truncation correction. Can be negative. |
| edge | Spectral content at the mask edge | Fraction of Σ\|û₁\|² in modes inside the 2/3 mask with max\|kᵢ\| ≥ 0.8 · 32/3. Diagnostic. |
| D4loc | Local rollout error | ‖u_k − S(u_{k−1})‖/‖S(u_{k−1})‖, S the reference solver over Δ: the one-step error from the rollout's own state. Not a debugger check. |

Accumulated statistics along a rollout (k = 1…20, step k maps the rollout's state k − 1 to its state k): **A_k = Σ_{j≤k} G_j** (primary), A_rss,k = (Σ G_j²)^½, A′_k = Σ G′_j (exploratory), and the comparator **C_k = Σ_{j≤k} D3_j**. D4_k = ‖u_k − u^ref(t_k)‖/‖u^ref(t_k)‖ is the accumulated error against the reference trajectory.

**The round-3 debugger** is D1 and D3 (round 1, unchanged thresholds), **D2″ in place of D2′**, and **G′ as an alarm**: `any3` = D1 ∨ D3 ∨ D2″ ∨ G′. A step is flagged by D2″ if D2″ > τ_D2″, or it is non-finite, or E(u₁) > E(u₀) (round 1's hard rule), or E(u₀), E(u₁) is non-finite; `D2pp_mag` is the same flag without the energy-increase rule. G′ flags if G′ > τ_G′ or non-finite. On a rollout, the **accumulated alarm** fires at the first k with A_k ≥ L = 0.05 (or non-finite).

## Thresholds, fixed now

Computed once by `round3/thresholds.py` on round 1's validation split (seeds 160–179, k₀ = 3, P0 and P0f32, the same 400 control steps round 2 used, for the same reason: exact controls cannot bias a threshold, and round 1's D1–D3 thresholds are recomputed there and must come out equal). Written to `round3/thresholds.json` and committed before any round-3 data exists.

- τ_D2″ = max(10 × validation max of D2″, 10 × eps(float32) = 1.19e-6).
- τ_G′ = max(10 × validation max of G′, 10 × eps(float32)). The same float32 floor: below it a float32 predictor's step cannot be resolved.
- τ_G6 = max(10 × validation max of G6, 1e-12). Exploratory flag only.
- D1, D2, D3 use round 1's `thresholds.json`; D2′ and G use round 2's `round2/thresholds.json`; both unchanged.
- **L = 0.05 and L/2 = 0.025 are design constants**, not calibrated on any data.

## Splits and seeds

Rounds 1–2 used seeds 0–219, 300–319, 1000 (Taylor–Green identity) and 2000–2219. Round 3 uses only seeds never used before:

| Split | Seeds | k₀ | Steps | Use |
| --- | --- | --- | --- | --- |
| validation | 160–179 (round 1) | 3 | 200 per predictor | Thresholds only |
| `r3test` | 3000–3039 | 3 | 10 per trajectory, 400 | H1–H7, H9–H13, sweep |
| `r3ood5` | 3100–3119 | 5 | 200 | H5, H9, H11, H12, sweep |
| `r3ood6` | 3200–3219 | 6 | 200 | H5, H9, H11, H12, sweep |
| `r3roll` | 3300–3339 | 3 | **horizon 20** (t ∈ [0, 2]), 800 per predictor | H14–H16 |

Same generator, solver, ν = 0.05, n = 32, Δ = 0.1 as before; `r3roll` trajectories are 21 states long. Code `round3/data.py`.

## Predictors

- **One-step**, on `r3test`, `r3ood5`, `r3ood6`: P0, P0f32, P1, P2s0, P2s1 (round 1's checkpoints, inference on WAR), P3a, P3b (round 1's definitions on P2s0's output; P3a phases `default_rng([7, seed, step])`). P3a/P3b are rebuilt deterministically at evaluation time from P2s0's saved predictions instead of being saved.
- **Rollouts**, on `r3roll`, from the reference state at t = 0 for 20 steps, each network fed its own float32 output on the GPU: P2s0, P2s1 (round 1), P2ge4 and P2gbest (round 2's graded checkpoints, one-step D4 medians 1.6 % and 0.74 % in round 2). Controls: P0 (the reference trajectory itself), **P0f32** (the solver applied to the previous P0f32 state, rounded to float32 each step: an exact predictor at float32 precision, chained), P1 (persistence, u_k = u₀). P0f32 and P1 rollouts are computed at evaluation time on each machine. Code `round3/predict.py`, `round3/evaluate.py`.

## Sensitivity sweep (Hook & Kelly–style graded mutations)

On every step of `r3test`, `r3ood5`, `r3ood6` (800 steps), the exact step (u₀ → u₁ = P0) is mutated with graded magnitudes m ∈ {1e-7, 3.2e-7, 1e-6, …, 3.2e-2} (half-decade grid, 12 values; momentum family up to 1e-2, 11 values):

- **Energy family, both signs.** u₁′ = α u₁ with α = (1 + s·m·E₀/E₁)^½, so E(u₁′) − E(u₁) = s·m·E₀ exactly: s = +1 injects energy, s = −1 removes it (excess dissipation). Divergence-free, shape-preserving.
- **Momentum family.** u₁′ = u₁ + m‖u₁‖ ξ/‖ξ‖, ξ a solenoidal masked random field with the k₀ = 3 initial spectrum and phases `default_rng([31, seed, step])`, so D4(u₁′) = m exactly.

Checks scored: energy family D2, D2′, D2″, each with and without the energy-increase rule (`_mag`); momentum family D3, G, G6, G′. The detection rate at (split, family, sign, check, m) is the share of the steps flagged. **Detection floor** = the smallest grid m such that the rate is ≥ 95 % at m and at every larger grid value; "none" if the largest value fails. The baseline (m = 0) flag rate is reported next to every floor: a floor with a nonzero baseline partly measures false positives.

## Hypotheses and criteria (fresh data)

| Id | Hypothesis | Pass if |
| --- | --- | --- |
| H1, H1b, H2, H3, H4 | Round 1 replicates, round-1 checks and thresholds | Round-1 criteria on `r3test` |
| H5, H6 | Round 2's D2′ replicates | 0 D2′ flags on P0/P0f32 in `r3test`, `r3ood5`, `r3ood6`; P3b flagged by `D2p_mag` on ≥ 95 % of `r3test` |
| H7 | Round 2's G ranking replicates | For each of P2s0, P2s1 on `r3test`: ρ(G, D4) ≥ 0.8 and CI low ≥ 0.6. **Comparator D3** under the same criterion must fail |
| **H9** | D2″ does not flag the exact solver | P0 and P0f32 flagged by D2″ on **0** steps in each of `r3test`, `r3ood5`, `r3ood6` (1,600 control steps) |
| **H10** | D2″ lowers the energy detection floor | For each split and each sign: floor(`D2pp_mag`) at least **two grid points (one decade) below** floor(`D2p_mag`). A missing floor counts as index 12 (the grid point after 3.2e-2) |
| H10b | D2″ still catches P3b by magnitude | P3b flagged by `D2pp_mag` on ≥ 95 % of `r3test` |
| **H11** | G′ is an alarm with no false positives | P0 and P0f32 flagged by G′ on **0** steps in each of `r3test`, `r3ood5`, `r3ood6` |
| **H12** | G′ still flags the broken predictors | P1, P3a and P3b each flagged by G′ on ≥ 95 % of steps in each of `r3test`, `r3ood5`, `r3ood6` |
| **H13** | G′ keeps the ranking | For each of P2s0, P2s1 on `r3test`: ρ(G′, D4) ≥ 0.8 and CI low ≥ 0.6. **Comparator D3** must fail |
| **H14** | Accumulated G tracks rollout error across trajectories | For each of P2s0, P2s1, P2ge4, P2gbest on `r3roll`: the mean over k = 1…20 of the within-step Spearman ρ_k(A_k, D4_k) across the 40 trajectories ≥ 0.7, and CI low ≥ 0.5. **Comparator C_k (cumulative D3)** under the same criterion must fail |
| **H15** | The accumulated alarm comes before D4 crosses 5 %, and not too early | Pooled over the four networks' 160 rollouts: of the rollouts whose D4 exceeds L = 5 % within 20 steps, the share whose alarm (A_k ≥ L) fired at or before that step is ≥ 0.9 with CI low ≥ 0.8; and of all alarms raised, the share raised while D4 < L/2 (premature) is ≤ 0.1. **Comparator: the round-2 debugger** (alarm at the first step flagged by `any2`) under the same criterion must fail |
| **H16** | No false alarms on the exact controls, alarm on persistence | 0 accumulated alarms on the 80 P0/P0f32 rollouts and 0 G′ flags on their 1,600 rollout steps; P1's alarm on time on ≥ 95 % of its rollouts that cross L |

**Verdicts.** H7, H13, H14 and H15 have three outcomes: PASS (the criterion holds and the comparator's does not), NON-DISCRIMINATIVE (both hold), FAIL (the criterion does not hold). The others are pass/fail. H8 (round 2's graded one-step ranking) is not repeated: round 2 already showed it non-discriminative, and the graded networks are used here in rollouts instead.

**Why within-step ranking.** Pooled over time, A_k, C_k and the bare step index k all rank D4_k almost perfectly (pilot: ρ ≈ 0.99 for all three), because every one of them grows with time. Fixing k and ranking across trajectories removes that trend; the time-pooled ρ and the step-index comparator are reported as exploratory, to show why they cannot be the test.

**Cluster bootstrap.** Trajectories are resampled with replacement (40 per replicate; in H7/H13 a trajectory brings its 10 steps, in H14 its 20 steps, in H15 its rollouts of all four networks), 2,000 replicates, `numpy.random.default_rng(20261024)` (round 2's seed and function for H7/H13), percentile interval 2.5–97.5 %. Spearman with average ranks (round 1's function). A within-step ρ that is non-finite in a replicate is skipped in that replicate's mean; a replicate whose statistic is non-finite is dropped and counted.

**What counts as a false positive:** any flag raised on P0 or P0f32 (exact by construction) by D1, D2, D3, D2′, D2″, G, G6 or G′ on any one-step or rollout step, and any accumulated alarm on a P0/P0f32 rollout, on any machine. Each one goes to `round3/ledgers/false_positives.jsonl` as `open`, marked as belonging to the round-3 debugger (D1, D3, D2″, G′, accumulated alarm) or not (D2, D2′, G, G6). It is closed only with written evidence in `round3/RESULTS.md`. For a network rollout, an alarm raised while D4 < L/2 is counted as premature in H15; it is not a ledger entry.

**Exploratory, no pass/fail:** the full floor table; flag rates of every check on every predictor and split, including P2s0/P2s1 for G′ and D2″; ρ of G, G6, G′, D3, D3p, D2, D2′, D2″ against D4 for each P2 group; **diagnosis of G's false alarms**: for P0 on the round-3 splits, ρ(G, T) and median G/T (T = G6 − G′, G's own truncation correction; G/T ≈ 1 means G on an exact step is its quadrature truncation), ρ(G, edge), ρ(G, step index), and median G and edge fraction per step index and split; for rollouts, per-step medians of D4, D4loc, G, G′, D1, D3, A and flags, ρ(G, D4loc) and median G/D4loc (does G estimate the local error along a rollout?), the time-pooled ρ of A, C and k against D4, H14 with A_rss, A′ and per-step G, and the alarm rates of `any3`.

Any failure is reported as a failure. No threshold, split, statistic, criterion or comparator is changed after the round-3 data exists.

## Machines and evidence

Same three machines as rounds 1–2, in a new folder `C:\ADN\pd-exp-r3` on WAR and GUERRA, using `C:\ADN\voz\venv` read-only (numpy 1.26.4), deleted at the end with a cleanup log. C: free space checked at 2026-10-25T04:03Z: WAR 60.0 GB, GUERRA 92.1 GB; GPUs idle. Nothing else on those machines is touched; the paused video factory stays paused.

| Machine | Role |
| --- | --- |
| Mac mini | Generates the round-3 splits (canonical), computes the thresholds, runs the full evaluation (`--jobs 2`), the ledgers and the full recomputation in `round3/verify.py` |
| WAR (RTX 5070) | One-step inference of P2s0/P2s1 and the four network rollouts (CUDA, float32); regenerates the round-3 splits from the seeds and reports the difference; runs the full evaluation independently (`--jobs 6`) |
| GUERRA (RTX 4060 laptop) | Regenerates the round-3 splits and reports the difference; runs the full evaluation independently (`--jobs 6`, because its CPU was about 6× slower than the Mac's single process in round 2). No training or inference |

Every hypothesis verdict is computed on all three machines from the Mac's canonical data and WAR's predictions; any machine that does not finish is stated as a gap. Remote machines apply the Mac's threshold files. All of `round3/*.py` and `round3/tools/` are copied to both remotes (round 2's first WAR fingerprint was wrong because one file was missing). Every transfer is hashed at both ends in `round3/logs/transfers.tsv` (round 1's `tools/sync.py` via `round3/tools/sync3.py`). The discrepancy ledger `round3/ledgers/discrepancies.jsonl` lists every step flag (all of `KEYS` in `round3/evaluate.py`), every sweep detection and every rollout alarm record whose verdict differs between machines. `round3/verify.py` re-applies the thresholds to saved statistics (`--saved MACHINE`) or recomputes everything, recomputes H1–H16 and prints a round-3 fingerprint over code (`pd/`, `round2/`, `round3/` `*.py`), inputs listed in `round3/MANIFEST.sha256` and verdicts; the one-action check is `uv run --locked round3/verify.py`. Stage times go to `round3/logs/mac/timeline.log`. Data, predictions and checkpoints stay out of git (hashes in the manifest); round 3 stays under 8 GB on the Mac.

## Limits stated in advance

The same box, viscosity, Δ and architecture as rounds 1–2. The energy mutations are uniform rescalings and the momentum mutations one random smooth direction per step; other error shapes can have other floors. D2″ and G′ still trade sensitivity for robustness, only at a lower level: an error smaller than the fourth-to-sixth-order correction of the step is invisible to them. The rollout horizon is 20 steps (t = 2) for k₀ = 3 only. Rollout hypotheses are about the debugger's view of four networks trained on one-step MSE; nothing here says how the debugger would behave on networks trained for rollouts. The pilot used the same networks P2s0/P2s1 and the same statistics; only the trajectories are new. This says nothing about the millennium problem or real turbulence.

## Amendments
