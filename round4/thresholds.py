import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pd.thresholds
import round3.evaluate as r3
from pd import SPLITS, environment, np, sha256, write_json
from round3.thresholds import FLOORS
from round4 import LEVEL, R1, R2, R3, R4
from round4.evaluate import PRIMARY, VARIANTS, rollout_task, run

RULE = {"E_alarm": f"tau_E = max(L = {LEVEL}, 10 x max over every step of the P0 and P0f32 validation rollouts (round-1 seeds 160-179, 10 steps) of E_{PRIMARY}); "
                   "alarm at the first step with E >= tau_E or non-finite"}


def main():
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 1
    names = SPLITS["val"][0]
    plan = [("onestep", r3.onestep_task, (R1 / "data", None, "val", ("P0", "P0f32")))]
    plan += [("rollout", rollout_task, (R1 / "data", None, "val", p, names[i:i + 5])) for p in ("P0", "P0f32") for i in range(0, len(names), 5)]
    results = run(plan, jobs)
    write_json(R4 / "logs" / "mac" / "validation_controls.json", results)
    records, rolled = results["onestep"], results["rollout"]
    t1, t2, t3 = (json.loads((r / "thresholds.json").read_text())["thresholds"] for r in (R1, R2, R3))
    column = [r[f"E_{PRIMARY}"] for r in rolled]
    if not all(np.isfinite(column)):
        raise FloatingPointError("non-finite validation transport estimate")
    write_json(R4 / "thresholds.json", {
        "rule": RULE,
        "thresholds": {"E_alarm": max(LEVEL, 10 * max(column))},
        "validation_rollout_max": {p: {f"E_{v}": max(r[f"E_{v}"] for r in rolled if r["predictor"] == p) for v in VARIANTS} for p in ("P0", "P0f32")},
        "validation_rollout_steps": len(rolled),
        "round1_thresholds_equal": pd.thresholds.compute(records, ("P0", "P0f32")) == t1,
        "round2_thresholds_equal": {"D2p": max(10 * max(r["D2p"] for r in records), 10 * float(np.finfo(np.float32).eps)) == t2["D2p"],
                                    "G": max(10 * max(r["G"] for r in records), 1e-12) == t2["G"]},
        "round3_thresholds_equal": {k: max(low, 10 * max(r[k] for r in records)) == t3[k] for k, low in FLOORS.items()},
        "thresholds_sha256": {"round1": sha256(R1 / "thresholds.json"), "round2": sha256(R2 / "thresholds.json"), "round3": sha256(R3 / "thresholds.json")},
        "validation_data_sha256": {name: sha256(R1 / "data" / "val" / f"{name}.npy") for name in names},
        "uv_lock_sha256": sha256(R4.parent / "uv.lock"),
        "environment": environment(),
    })
    print((R4 / "thresholds.json").read_text())


if __name__ == "__main__":
    main()
