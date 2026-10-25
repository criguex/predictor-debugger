# Pre-registration · Round 4 · Error transport along rollouts

Written on 2026-10-25 (UTC) before any round-4 evaluation data exists: no trajectory with the seeds below has been generated, no network has been run on them, and no round-4 threshold has been computed. Rounds 1 (`DESIGN.md`, …), 2 (`round2/`) and 3 (`round3/`) are frozen and are not edited; their fingerprints EEC9-09E0-F77D, D506-F58F-3838 and 6319-537B-7167 must still verify at the end. Changes after this commit are numbered amendments at the end, each saying whether it was made before or after the round-4 test data was seen.

## Why a fourth round

Round 3's H14 failed. Along 20-step rollouts, the accumulated gauge A_k = Σ_{j≤k} G_j ranked trajectories by their rollout error D4_k with ρ ≈ 0.99 at step 1 but only 0.45–0.73 at step 20 (mean over steps 0.800 / 0.815 / 0.747 / 0.635 for P2s0 / P2s1 / P2ge4 / P2gbest), and the comparator ΣD3 met the same criterion on three of four networks, so the test did not discriminate either way. G itself measured the local one-step error almost perfectly along the rollouts (ρ(G, D4loc) ≥ 0.9987, G/D4loc 0.96–1.00).

Diagnosis. Write u_k for the reference trajectory, û_k for the network's rollout and Φ for one exact solver step over Δ. Then

e_k = û_k − u_k = d_k + [Φ(û_{k−1}) − Φ(u_{k−1})] ≈ d_k + DΦ(û_{k−1}) e_{k−1},   d_k = û_k − Φ(û_{k−1}),

so the error is the local defect d_k plus the previous error carried by the tangent map DΦ. G estimates ‖d_k‖; ΣG adds norms and ignores both the direction of each defect and what DΦ does to the accumulated error (damping, rotation, cancellation). Round 4 replaces the sum of norms by a transported vector estimate.

## Prior art (no novelty claimed)

- **Error transport equations** in CFD a-posteriori error estimation propagate a local truncation-error source through the linearised equations, e.g. Cavallo & Sinha, *J. Aircraft* 44 (2007) 1954–1963.
- **Dual-weighted residual** estimation (Becker & Rannacher, *Acta Numerica* 10 (2001) 1–102) weights local residuals by an adjoint solution to estimate the error in a target functional; here the forward (tangent-linear) version is used for the error vector itself.
- **Tangent-linear models** as in variational data assimilation (Le Dimet & Talagrand, *Tellus A* 38 (1986) 97–110).
- **Breeding vectors** (Toth & Kalnay, *Bull. Amer. Meteor. Soc.* 74 (1993) 2317–2330) and **finite-time Lyapunov exponents** by renormalised forward iteration of the tangent map (Benettin et al., *Meccanica* 15 (1980) 9–20; Lorenz, *Tellus* 17 (1965) 321–333).

What is tested here is whether these standard tools, fed only by the debugger's residual, make the rollout ranking and calibration hypotheses hold on a learned 3D Navier–Stokes predictor.

## New statistics

Float64 everywhere (`<f8`, complex128 FFTs), as in rounds 1–3. Notation of rounds 2–3: ĥ = full unmasked FFT, N the solver's `rhs(·, ν)` (projected and masked), P the solver's `project` (Leray projection and 2/3 mask), Δ = 0.1, DT = 0.01, 10 substeps. Code `round4/transport.py`, `round4/evaluate.py`; rounds 1–3 are imported unchanged.

**Tangent-linear map, exact.** N(x) = Lx + B(x, x) is quadratic, so J(s)v = ½[N(s + v) − N(s − v)] is exact for any size of v; it is evaluated with v rescaled to ‖s‖ and the result scaled back, to avoid cancellation. One solver step Φ(u) = physical(RK4¹⁰(P ĥ(u))) is differentiated stage by stage: for each RK4 substep the tangent stages are dk₁ = J(s)t, dk₂ = J(s + DT/2 k₁)(t + DT/2 dk₁), dk₃ = J(s + DT/2 k₂)(t + DT/2 dk₂), dk₄ = J(s + DT k₃)(t + DT dk₃), t′ = P(t + DT(dk₁ + 2dk₂ + 2dk₃ + dk₄)/6), with the input tangent projected as the solver projects its input. The base state is computed with the solver's own expressions in the same order, so it equals `advance()` bit for bit (asserted in `round4/test_checks4.py`). `vendor/fluid_solver.py` is not edited. **Measured check** (self-test, a random k₀ = 3 state, before any round-4 data): against central differences of Φ the relative difference is 5.7e-11 at ε = 1e-4·‖u‖ and falls as ε²; Richardson-extrapolated differences agree to 3.2e-13 at ε = 1e-3; linearity holds to 1e-12.

**Local defect estimate d̂_k** from the round-3 residual vector, with the start projected as the solver projects it: r₆ = (ĥ_k − P ĥ_{k−1})/Δ − ½(N_{k−1} + N_k) − Δ/10 (Ṅ_{k−1} − Ṅ_k) − Δ²/120 (N̈_{k−1} + N̈_k) (round 3's sixth-order Hermite residual, whose own truncation is the term G′ subtracts). For a step û_k = Φ(û_{k−1}) + δ, Δ r₆ ≈ (I − Δ/2 J(û_k))δ + O(Δ²) δ + truncation. Pre-registered reconstruction (primary, `fp3`): three fixed-point iterations δ ← Δ r₆ + (Δ/2) J(û_k) δ starting at δ = Δ r₆ (inverting the trapezoid Jacobian; the O(Δ²) Jacobian terms and the quadratic remainder are neglected). Exploratory variants: `r6` = Δ r₆ (no inversion), `r4` = Δ r₄ (round-2/3 G's residual), `r6u` = Δ r₆ with the unprojected start (round 3's literal residual).

**Transported error.** ê₀ = 0, ê_k = DΦ(û_{k−1}) ê_{k−1} + d̂_k, evaluated at the network's own states (never the reference). Statistic **Ê_k = ‖ê_k‖ / ‖û_k‖** (same units as D4_k). One transported vector per variant.

**Oracle (diagnostic, not a debugger statistic).** Ê*_k from the same transport with the exact local defect d_k = û_k − Φ(û_{k−1}), which needs the reference solver run from the network's state. It separates the two error sources: ‖ê*_k − e_k‖/‖e_k‖ is the linearisation error of the transport, and ‖d̂_k − d_k‖/‖d_k‖ is the defect-reconstruction error.

**Option A (comparator and exploratory): Lyapunov weighting.** A unit vector b₀ (solenoidal, masked, k₀ = 3 spectrum, phases `default_rng([41, seed])`) is carried by the same tangent map and renormalised every step (forward power iteration / breeding with the tangent-linear model): λ_k = ‖DΦ(û_{k−1}) b_{k−1}‖, b_k = DΦ(û_{k−1}) b_{k−1}/λ_k. **Lyapunov-weighted ΣG:** S₀ = 0, S_k = λ_k S_{k−1} + G_k, i.e. each past G_j is multiplied by the finite-time growth factor λ_{j+1}⋯λ_k of the leading direction. Finite-time exponent σ_k = Σ_{j≤k} log λ_j /(kΔ), reported.

**Cost note.** A debugger that can run DΦ could also run Φ and obtain d_k exactly; Ê is the residual route, and the oracle measures what it loses. Per rollout step the transport costs about 40 + 80 × (number of carried vectors) right-hand-side evaluations.

## Pilot on already-seen data, disclosed

Before writing this file, the new statistics were computed on data that round 3 had already evaluated: round 3's `r3roll` (seeds 3300–3339, 20-step rollouts of P2s0, P2s1, P2ge4, P2gbest from round 3's WAR predictions, plus P0, P0f32, P1), 5,600 steps. Code `round4/pilot.py`, output `round4/pilot/` (`pilot_rows.json`, `pilot_summary.json`), logs `round4/logs/mac/pilot.log`, `pilot_summary.log`. Before the full pilot, a five-step smoke test on `r3roll` states compared the defect variants against the exact local defect (fixed-point iterations 0–9: error 8–15 % with no inversion, ≈ 1 % after 3 iterations, no gain after 4); that is where `fp3` was chosen as primary, before the full pilot ran. **The hypotheses H17–H20 and their thresholds were set by the author before the pilot and are not changed by it.** A smoke run of the full `round4/evaluate.py` on three already-seen trajectories per split (round-3 files standing in for round-4 names, placeholder τ_Ê = 0.05) only exercised the code path; its outputs were written to a scratch folder and not kept.

| Pilot result (seen data, `r3roll`) | P2s0 | P2s1 | P2ge4 | P2gbest |
| --- | --- | --- | --- | --- |
| mean within-step ρ(Ê, D4) [CI95] | 0.991 [0.977, 0.994] | 0.984 [0.963, 0.990] | 0.990 [0.975, 0.993] | 0.997 [0.990, 0.997] |
| ρ_k of Ê at k = 1 / 5 / 10 / 20 | 1.000 / 0.997 / 0.990 / 0.981 | 0.999 / 0.993 / 0.983 / 0.960 | 1.000 / 0.998 / 0.992 / 0.977 | 0.999 / 0.998 / 0.996 / 0.989 |
| mean ρ of A = ΣG (round 3) | 0.800 | 0.815 | 0.747 | 0.635 |
| ρ_k of A at k = 1 / 20 | 0.993 / 0.708 | 0.994 / 0.732 | 0.995 / 0.593 | 0.990 / 0.473 |
| Δρ Ê − A [paired CI95] | +0.191 [+0.097, +0.329] | +0.169 [+0.091, +0.284] | +0.244 [+0.122, +0.449] | +0.362 [+0.201, +0.582] |
| Δρ Ê − C (ΣD3) [paired CI95] | +0.206 [+0.104, +0.362] | +0.133 [+0.082, +0.212] | +0.181 [+0.093, +0.333] | +0.343 [+0.190, +0.550] |
| mean ρ of S (Lyapunov-weighted ΣG) | 0.751 | 0.808 | 0.753 | 0.622 |
| mean ρ of the oracle Ê* / of `r6` (no inversion) / `r6u` | 0.991 / 0.986 / 0.987 | 0.984 / 0.982 / 0.982 | 0.990 / 0.990 / 0.990 | 0.997 / 0.994 / 0.995 |
| median Ê/D4 over k (min–max) | 1.001–1.003 | 0.984–1.002 | 1.001–1.004 | 1.003–1.017 |
| same for A / S | 1.09–1.83 / 1.09–1.48 | 1.09–1.47 / 1.01–1.28 | 1.08–1.62 / 1.08–1.27 | 1.09–1.73 / 1.09–1.44 |
| median ‖d̂ − d‖/‖d‖, `fp3` / `r6` / `r6u`, k = 5 | 1.4 % / 17 % / 57 % | 1.3 % / 16 % / 49 % | 1.1 % / 14 % / 53 % | 1.4 % / 17 % / 61 % |
| median linearisation error ‖ê* − e‖/‖e‖ at k = 20 | 1.6 % | 1.9 % | 3.3 % | 1.2 % |
| Ê alarm (≥ 5 %) on time, of 40 rollouts crossing 5 % | 39/40 | 38/40 | 40/40 | 40/40 |

Controls on the same rollouts: Ê never exceeds 6.1e-8 on P0 and 6.7e-8 on P0f32 (no alarm in 80 rollouts, no flag from any check); P1's Ê alarm is on time in 40/40. λ_k (one-step growth of the bred direction) is 0.95–0.98 at every step: in this viscous regime the tangent map contracts, so ΣG's failure is not chaotic amplification. Pooled Ê alarm: on time 157/160 = 0.981 (CI95 [0.963, 1.0]), premature 0; A: 160/160 on time with lead 0–9 steps.

What the pilot shows and what it changed:

- The round-3 failure was the sum of norms, not the defect estimate: even the uninverted residual (`r6`, 14–17 % defect error) transported through DΦ ranks at 0.98–0.99, while the Lyapunov-weighted sum S, which knows the growth of the leading direction but still adds norms, does no better than A. The transport carries the direction of each defect and the cancellations between them.
- Projecting the start (P û_{k−1}) matters for the defect (`r6u`: 45–60 % error after the first step, because the network's non-solenoidal content enters the residual twice), but barely for the ranking.
- Ê is calibrated to about 2 %, so as an alarm at the same level L it fires in the crossing step itself (lead 0) and is late by one step in a few rollouts; H20 may fail on fresh data for that reason. The criterion is kept.
- Nothing in the criteria was changed. The pilot fixed the choice of `fp3` as primary (confirming the smoke test) and the list of exploratory variants.

## Thresholds, fixed now

Computed once by `round4/thresholds.py` on round 1's validation split (seeds 160–179, k₀ = 3), written to `round4/thresholds.json` and committed before any round-4 data exists.

- **Ê alarm:** τ_Ê = max(L, 10 × the maximum of Ê_k (`fp3`) over every step of the P0 and P0f32 *validation rollouts*), with **L = 0.05** a design constant (round 3's rollout level). P0's validation rollout is the reference trajectory itself; P0f32 chains the solver rounded to float32 each step; each is 10 steps long. The alarm fires at the first k with Ê_k ≥ τ_Ê or non-finite.
- Rounds 1–3 thresholds (D1, D2, D3; D2′, G; D2″, G′, G6) and round 3's L = 0.05 for A_k are reused unchanged; `round4/thresholds.py` recomputes them from the same validation data and records whether they come out equal.

## Splits and seeds

Rounds 1–3 used seeds 0–219, 300–319, 1000, 2000–2219 and 3000–3339. Round 4 uses only seeds never used before:

| Split | Seeds | k₀ | Steps | Use |
| --- | --- | --- | --- | --- |
| validation | 160–179 (round 1) | 3 | 200 one-step + 200 rollout per control | Thresholds only |
| `r4test` | 4000–4039 | 3 | 10 per trajectory, 400 | Sanity block (H1–H7, H9–H13), sweep |
| `r4ood5` | 4100–4119 | 5 | 200 | H5, H9, H11, H12, sweep |
| `r4ood6` | 4200–4219 | 6 | 200 | H5, H9, H11, H12, sweep |
| `r4roll` | 4300–4339 | 3 | horizon 20 (t ∈ [0, 2]), 800 per predictor | H17–H20 |

Same generator, solver, ν = 0.05, n = 32, Δ = 0.1 as before (code `round4/data.py`, which calls rounds 1 and 3's generators).

## Predictors

As in round 3, with round 1's checkpoints P2s0/P2s1 and round 2's P2ge4/P2gbest (no retraining). One-step on `r4test`, `r4ood5`, `r4ood6`: P0, P0f32, P1, P2s0, P2s1, P3a, P3b. Rollouts on `r4roll` from the reference state at t = 0 for 20 steps, each network fed its own float32 output on WAR's GPU (`round4/predict.py`): P2s0, P2s1, P2ge4, P2gbest; controls P0 (reference), P0f32 (solver chained in float32), P1 (persistence), computed at evaluation time on each machine.

## Hypotheses and criteria (fresh data)

**Sanity block (round 3 replicated on fresh splits, round-3 checks, thresholds and criteria):** H1, H1b, H2, H3, H4, H5, H6, H7, H9, H10, H10b, H11, H12, H13 exactly as in `round3/DESIGN.md`, on `r4test`/`r4ood5`/`r4ood6` in place of the round-3 splits. H7 and H13 keep their D3 comparator and three outcomes.

| Id | Hypothesis | Pass if |
| --- | --- | --- |
| **H17** | The transported estimate ranks rollout error across trajectories | For **each** of P2s0, P2s1, P2ge4, P2gbest on `r4roll`: the mean over k = 1…20 of the within-step Spearman ρ_k(Ê_k, D4_k) across the 40 trajectories ≥ 0.8 **and** its cluster-bootstrap CI95 low ≥ 0.6, **and** ρ₂₀ (point estimate at k = 20) ≥ 0.7 |
| **H17-D** | …and it discriminates (required for H17 to count as PASS) | For each network, paired bootstrap of Δρ = mean ρ(Ê) − mean ρ(X) for X = A (ΣG) and X = C (ΣD3): Δρ ≥ 0.1 **and** CI95 low > 0, for both comparators |
| **H18** | Ê is calibrated | For each network and every k = 1…20, the median over the 40 trajectories of Ê_k/D4_k lies in [1/1.5, 1.5] |
| **H19** | No false alarms, alarm on persistence | 0 Ê alarms on the 80 P0/P0f32 rollouts; **0 new false positives from any check** (definition below); P1's Ê alarm on time (at or before D4 > L) on ≥ 95 % of its rollouts that cross L |
| **H20** | Ê is a timely alarm | Pooled over the four networks' 160 rollouts: of the rollouts whose D4 exceeds L = 5 % within 20 steps, the share whose Ê alarm fired at or before that step ≥ 0.9 with CI95 low ≥ 0.8; of all Ê alarms raised, the share raised while D4 < L/2 (premature) ≤ 0.1. Round 3's A alarm is reported under the same rule as the reference (not as a comparator that must fail: A passed H15); the lead-time distribution (crossing step − alarm step) is reported for both |

**Verdicts.** H17 has three outcomes: PASS (H17 criterion holds for all four networks and H17-D holds for all four), NON-DISCRIMINATIVE (H17 holds, H17-D fails for at least one network or comparator), FAIL (H17 does not hold). H18, H19, H20 are pass/fail. H7/H13 as in round 3.

**Within-step ranking and bootstrap** exactly as in round 3: trajectories resampled with replacement (40 per replicate, each bringing its 20 steps), 2,000 replicates, `numpy.random.default_rng(20261024)`, percentile interval 2.5–97.5 %, Spearman with average ranks; a non-finite within-step ρ is skipped in that replicate's mean. For H17-D the same resampled trajectories are used for Ê, A and C in each replicate (paired); the interval is that of the per-replicate difference. H20's interval is round 3's (trajectories resampled with all four networks' rollouts).

**False positives.** Any flag on P0 or P0f32 (one-step on every split, and every rollout step) by D1, D2, D3, D2′, D2″, G, G6 or G′, any A alarm and any Ê alarm on a P0/P0f32 rollout, on any machine, goes to `round4/ledgers/false_positives.jsonl` as `open`. A flag is **known** (not new) only when it comes from an old non-debugger check and round 3's written explanation applies to that very step, checked automatically: a D2 flag with D2′ < 0, a D2′ flag with D2″ < 0, a G or G6 flag with G′ < 0 (the residual is smaller than its own quadrature correction). Every other entry — any flag by D1, D3, D2″ or G′, any A or Ê alarm, or an old-check flag whose explanation does not hold — is **new** and fails H19.

**What a failure would mean, stated now.**
- If H17 fails while the oracle Ê* tracks (its mean ρ meets the H17 criterion), the bottleneck is the defect estimate d̂ (its direction or noise), not the amplification; ‖d̂_k − d_k‖/‖d_k‖ per step says how far off it is.
- If H17 fails and Ê* also fails, the linearised transport is the limit (‖ê*_k − e_k‖/‖e_k‖ large) or D4's within-step spread is too small to rank; the report says which.
- If H17 holds but H17-D fails, transport is not needed for ranking at this horizon: the cheaper sums do as well.
- If H18 fails with Ê* calibrated, the defect estimate is biased in size; if Ê* is also off, the normalisation or linearisation is.
- If H20 fails by lateness while H18 holds, a calibrated estimate is a late alarm by construction (half the rollouts cross before the estimate does); L would have to carry a margin, which is not changed here.

**Exploratory, no pass/fail:** ρ_k curves (k = 1…20) and mean ρ with CIs for Ê, A, C, S (Lyapunov-weighted ΣG), A_rss, the oracle Ê* and the variants `r6`, `r4`, `r6u`, with paired Δρ against Ê; the median ratio to D4 per step for Ê, Ê*, A, S and the variants; per-step medians of λ_k, σ_k, ‖d̂_k − d_k‖/‖d_k‖ for every variant, ‖ê*_k − e_k‖/‖e_k‖, the fixed-point change at the third iteration, D4, D4loc, G; alarm records of A, S and Ê*; round 3's H14–H16 statistics on the fresh rollouts (A versus C, A alarm, controls); every check's flag rates on every predictor and split.

Any failure is reported as a failure. No threshold, split, statistic, reconstruction, criterion or comparator is changed after the round-4 data exists.

## Machines and evidence

Same three machines as rounds 1–3, in a new folder `C:\ADN\pd-exp-r4` on WAR and GUERRA, using `C:\ADN\voz\venv` read-only (numpy 1.26.4), deleted at the end with a cleanup log. C: free space checked at 2026-10-25T13:05Z: WAR 59.8 GB, GUERRA 92.4 GB; GPUs idle, `C:\ADN\pd-exp-r3` already gone. Nothing else on those machines is touched; the paused video factory stays paused.

| Machine | Role |
| --- | --- |
| Mac mini | Generates the round-4 splits (canonical), computes the thresholds, runs the full evaluation, the ledgers and the full recomputation in `round4/verify.py` |
| WAR (RTX 5070) | One-step inference of P2s0/P2s1 and the four network rollouts (CUDA, float32); regenerates the round-4 splits and reports the difference; runs the full evaluation independently |
| GUERRA (RTX 4060 laptop) | Regenerates the round-4 splits and reports the difference; runs the full evaluation independently (more processes, since its FFTs measured about 2× slower than the Mac's per process). No training or inference |

Tasks are split by predictor and by chunks of five trajectories so that the slowest machine is not held by one long task (round 3's GUERRA run was). Every hypothesis verdict is computed on all three machines from the Mac's canonical data and WAR's predictions; any machine that does not finish is stated as a gap. Remote machines apply the Mac's threshold files. All of `round4/*.py`, `round4/tools/` and every module of rounds 1–3 they import are copied to both remotes; every transfer is hashed at both ends in `round4/logs/transfers.tsv` (`round4/tools/sync4.py` over round 1's `tools/sync.py`). The discrepancy ledger `round4/ledgers/discrepancies.jsonl` lists every step flag, sweep detection and rollout alarm record (A and Ê) whose verdict differs between machines. `round4/verify.py` re-applies the thresholds to saved statistics (`--saved MACHINE`) or recomputes everything, recomputes the sanity block and H17–H20 and prints a round-4 fingerprint over code (`pd/`, `round2/`, `round3/`, `round4/` `*.py`), inputs listed in `round4/MANIFEST.sha256` and verdicts; the one-action check is `uv run --locked round4/verify.py`. Stage times go to `round4/logs/mac/timeline.log`. Logs are kept exactly as produced — never edited, filtered or stripped; summaries, when needed, go to separate files. Data and predictions stay out of git (hashes in the manifest); round 4 stays under 6 GB on the Mac.

## Limits stated in advance

The same box, viscosity, Δ, architecture and networks as rounds 1–3, horizon 20 steps, k₀ = 3 rollouts only. The transport is linearised at the network's state; with rollout errors of 5–15 % its quadratic remainder is not negligible, and the oracle measures it. The defect reconstruction neglects the O(Δ²) part of the Hermite Jacobian. Ê needs the tangent of one solver step per rollout step, roughly three times the cost of the step itself per carried vector: it is a debugger statistic only in the sense that it uses no reference trajectory, not in the sense of being cheap. The pilot used the same four networks and the same statistics on round 3's rollout trajectories; only the round-4 trajectories are new. This says nothing about the millennium problem or real turbulence.

## Amendments
