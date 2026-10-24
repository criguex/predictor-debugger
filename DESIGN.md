# Pre-registration · Physics debugger for a learned flow predictor

Written before any dataset, model or prediction exists. Changes after this commit are amendments: they go at the end with date, reason and commit, and none may be made after the test split has been evaluated.

## Question

A debugger made only of physical checks, with thresholds fixed in advance, receives the output of a flow predictor. Does it reject predictors known to be wrong, accept the exact solver, and flag where a learned predictor breaks the physics?

The object under test is the **debugger**, not the neural network. A poor network is an acceptable result; a debugger that cannot tell the controls apart is a failure.

## System

| Item | Value |
| --- | --- |
| Equations | 3D incompressible Navier–Stokes, no forcing, periodic box [0, 2π]³ |
| Grid | n = 32, 2/3 dealiasing |
| Viscosity | ν = 0.05 |
| Reference solver | `SpectralFlow` from `fluid_solver.py`, SHA-256 `87d3372edf646da285731f5144551c2a626987f3718c6985b47a6c816f3bdc50` (scientific-qa-evidence `d815cd9`), imported unchanged; RK4, dt = 0.01 |
| Initial conditions | Random divergence-free fields, energy spectrum E(k) ∝ k⁴ exp(−2 (k/k₀)²), random phases from `numpy.random.default_rng(seed)`, projected and rescaled to energy 0.125 |
| Prediction step | Δ = 0.1 (10 solver steps); trajectories of 10 steps, t ∈ [0, 1] |

The initial-condition generator is new code in its own module; the solver file is not edited.

## Splits

| Split | Seeds | k₀ | Use |
| --- | --- | --- | --- |
| Train | 0–159 | 3 | Fit the network |
| Validation | 160–179 | 3 | Early stopping and threshold calibration only |
| Test | 180–219 | 3 | Evaluated once, at the end |
| Out of distribution | 300–319 with k₀ = 5, plus Taylor–Green | 5 / — | Reported separately, no pass/fail |

## Predictors

| Id | Predictor | Role |
| --- | --- | --- |
| P0 | Reference solver | Positive control: must be accepted |
| P1 | Persistence, u(t+Δ) = u(t) | Naive baseline: ignores the dynamics |
| P2 | Learned Fourier neural operator | The predictor under study |
| P3a | P2 output plus a gradient field ∇φ with ‖∇φ‖ = 5 % of ‖u‖ | Negative control: breaks incompressibility |
| P3b | P2 output scaled by 1.05 | Negative control: injects energy |

P2 is fixed now: 4 Fourier layers, 8 modes per axis, width 24, GELU, MSE loss on u(t+Δ), Adam, learning rate 1e-3, batch 8, at most 100 epochs, early stopping on validation loss with patience 10, torch seed 0. No physics term in the loss, so the debugger's checks are not trained into the model. No architecture or hyperparameter search.

## Debugger checks

Computed spectrally on each predicted step (u₀ → u₁), with E the kinetic energy, Z the enstrophy and N(u) the solver's right-hand side.

| Id | Check | Statistic |
| --- | --- | --- |
| D1 | Incompressibility | ‖div u₁‖₂ / ‖∇u₁‖₂ |
| D2 | Energy budget | \|E(u₁) − E(u₀) + ν Δ (Z(u₀) + Z(u₁))\| / E(u₀), plus a hard rule: E(u₁) > E(u₀) is a violation |
| D3 | Momentum residual | ‖(u₁ − u₀)/Δ − ½ (N(u₀) + N(u₁))‖₂ / ‖N(u₀)‖₂ |
| D4 | Error against the reference | ‖u₁ − u₁^ref‖₂ / ‖u₁^ref‖₂, **not a debugger check**: used only to judge the debugger |

**Threshold rule, fixed now:** for D1, D2 and D3, τ = 10 × the maximum of the statistic for P0 over all validation steps, with a floor of 1e-12. Thresholds are computed once, written to `thresholds.json` with its hash, and not changed afterwards. A step is flagged if any check exceeds its threshold, or if any value is NaN or infinite. A NaN is never a pass.

## Hypotheses and criteria (test split)

| Id | Hypothesis | Pass if |
| --- | --- | --- |
| H1 | The exact solver is accepted | P0 flagged on ≤ 5 % of test steps |
| H2 | Broken incompressibility is caught | P3a flagged by D1 on ≥ 95 % of test steps |
| H3 | Energy injection is caught | P3b flagged by D2 on ≥ 95 % of test steps |
| H4 | Ignoring the dynamics is caught | P1 flagged by D3 on ≥ 95 % of test steps |
| E1 | Exploratory | For P2: share of steps flagged per check, and Spearman ρ between D3 and D4 over test steps. Reported with no pass/fail |

Any failure of H1–H4 is reported as a failure of the debugger. No threshold, split or check is changed to turn a failure into a pass.

## Evidence

- Every input, dataset, checkpoint, prediction and result file is listed with SHA-256 in `MANIFEST.sha256`.
- `environment.json`: Python, numpy, torch versions, device (CPU or MPS), OS, date.
- Raw logs of each stage are kept as produced, in `logs/`.
- `verify.py` recomputes D1–D4 from the saved predictions, re-applies `thresholds.json`, recomputes H1–H4 and prints a fingerprint. Rerunning from scratch must reproduce the verdicts; bit-exact network weights are not required across devices.

## Limits stated in advance

A 32³ periodic box, smooth random initial fields, short horizon, one architecture, no forcing. This says nothing about Clay's problem, about OpenAI's proof, or about real turbulence. A debugger that passes here is evidence about these checks on this setup only.

## Packaging

When the results exist, the pipeline is wrapped as a skill (`debug-predictor-fisica`) with two modes: re-verify the saved evidence, and rerun from scratch and compare. The skill is written after the results, and does not change them.

## Amendments

### 1 · 2026-10-24, before any data exists: numerical precision

Reason: the network is trained on Apple's MPS, which has no float64. A float32 field has relative rounding near 1.2e-7, while the threshold rule above calibrates D1 on a float64 solver whose divergence sits near 1e-15. As written, D1 would flag a perfect float32 predictor for rounding, not for physics.

- Datasets, reference trajectories, predictions and all debugger arithmetic are float64 (`<f8`, FFTs in complex128). Predictor outputs are cast to float64 before any check.
- New control **P0f32**: the reference solver's output rounded to float32 and cast back. It is the best a float32 predictor could do.
- Thresholds for D1–D3 are τ = 10 × the validation maximum over P0 **and** P0f32. A second table reports the float64-only thresholds (from P0 alone), to show how much resolution float32 costs. Only the first set decides H1–H4.
- New hypothesis **H1b**: P0f32 flagged on ≤ 5 % of test steps.
- `environment.json` records `numpy.finfo` and `torch.finfo` for every dtype used. A statistic below 10 × the machine epsilon of the data's dtype is reported as "at the precision floor", not as a measured value.
- float64 is enough: the solver's own controls already resolve errors of 1e-15 to 1e-17, while the D2 and D3 effects expected here are 1e-3 or larger. Extended precision is not used.

### 2 · 2026-10-24, before any data exists: three machines, discrepancy and false-positive ledgers

Reason: the author asked to run on more than one machine, with logs and evidence for everything and an explicit trail of false positives.

| Machine | Hardware | Role |
| --- | --- | --- |
| Mac mini (M2 Pro, 16 GB) | CPU float64, MPS float32 | Generates the canonical dataset and reference (P0, P0f32), computes thresholds, runs the debugger on every predictor |
| WAR | RTX 5070 12 GB, CUDA, torch 2.7.0+cu128 | Trains P2 (float32, CUDA) and runs the debugger again, independently, on the same saved predictions |
| GUERRA | RTX 4060 Laptop 8 GB, torch 2.6.0+cu124, 7.4 GB free on C: | Light role only: recomputes P0 for the test split from the seeds and re-runs the debugger on the test predictions. No dataset copy, no training, while its disk stays under 20 GB free |

- The canonical files are the Mac's. Each transfer is listed with source and destination SHA-256 in `logs/transfers.tsv`; a mismatch stops the run.
- On WAR and GUERRA, existing Python environments are used read-only (no package installs into them); all files go to a new folder outside any versioned tree, and are deleted after their hashes and logs are copied back.
- **Discrepancy ledger** (`ledgers/discrepancies.jsonl`): any test step whose verdict differs between machines, with the three values, thresholds and machine. Discrepancies are reported, never resolved by picking a machine.
- **False-positive ledger** (`ledgers/false_positives.jsonl`): every flag raised on P0 or P0f32, which are correct by construction, with machine, check, value, threshold, seed and step. Each entry stays open until it is explained by evidence (for example, a value at the precision floor); an unexplained entry is reported as open.
- **Exploratory confusion table for P2** (no pass/fail): a step counts as truly wrong when D4 > 1 % relative error, fixed now. Report flagged-and-wrong, flagged-but-not-wrong (debugger false positives), wrong-but-not-flagged (misses), and neither, per check and per machine.
- A second training of P2 with torch seed 1 on WAR is reported alongside seed 0, to show how much the debugger's view of P2 depends on the training run. It does not affect H1–H4.

### 3 · 2026-10-24, before any data exists: GUERRA's disk

GUERRA's C: went from 7.4 GB to 86.7 GB free after the author approved removing old installers and one game (log kept outside this repo). The 20 GB condition in amendment 2 no longer limits it. GUERRA therefore receives the full set of saved predictions and runs the debugger on every split, like WAR. It still does not train; seeds 0 and 1 stay on WAR.

### 4 · 2026-10-24, before any data exists: one-step versus rollout

Reason: the design said "trajectories of 10 steps" without saying whether predictors start each step from the reference state.

- **H1–H4, E1, the ledgers and the confusion table use one-step predictions**: for every reference pair (u(t), u(t+Δ)) in a split, each predictor receives the reference u(t) and returns its u₁. That gives 10 steps per trajectory: 200 validation steps, 400 test steps.
- **E2 (exploratory, no pass/fail)**: P2 rolled out on its own outputs for 10 steps from each test initial state, with D1–D4 per step, to show how violations accumulate.
- The numpy version is pinned to 1.26.4 on all three machines, matching what WAR and GUERRA already have. The dataset is generated on the Mac; WAR and GUERRA also regenerate it from the seeds, and the maximum absolute difference against the Mac's files is recorded per file. A nonzero difference is reported, not hidden; the Mac's files remain the canonical ones.
