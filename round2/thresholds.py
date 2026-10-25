import json

import pd.evaluate
import pd.thresholds
from pd import SPLITS, environment, flow, np, sha256, write_json
from round2 import R1, R2
from round2.checks import statistics2

pd.evaluate.statistics = statistics2

EPS32 = float(np.finfo(np.float32).eps)
RULE = {
    "D1, D2, D3": pd.thresholds.RULE,
    "D2p": "tau = max(10 x max over validation one-step steps of P0 and P0f32, 10 x eps(float32)); flagged if value > tau, non-finite, or E1 > E0",
    "G": "tau = max(10 x max over validation one-step steps of P0 and P0f32, 1e-12); exploratory flag only",
}


def tau(records, key, floor):
    values = [r[key] for r in records]
    if not all(np.isfinite(values)):
        raise FloatingPointError(f"non-finite validation statistic for {key}")
    return max(floor, 10 * max(values))


def main():
    records = pd.evaluate.one_step_records(flow(), R1 / "data", None, ("P0", "P0f32"), ("val",))
    write_json(R2 / "logs" / "mac" / "validation_controls.json", records)
    recomputed = pd.thresholds.compute(records, ("P0", "P0f32"))
    round1 = json.loads((R1 / "thresholds.json").read_text())["thresholds"]
    write_json(R2 / "thresholds.json", {
        "rule": RULE,
        "steps_per_predictor": len(records) // 2,
        "thresholds": {"D2p": tau(records, "D2p", 10 * EPS32), "G": tau(records, "G", 1e-12)},
        "round1_thresholds_recomputed": recomputed,
        "round1_thresholds_equal": recomputed == round1,
        "round1_thresholds_sha256": sha256(R1 / "thresholds.json"),
        "validation_max": {p: {k: max(r[k] for r in records if r["predictor"] == p) for k in ("D1", "D2", "D3", "D2h", "D2p", "G")} for p in ("P0", "P0f32")},
        "validation_data_sha256": {name: sha256(R1 / "data" / "val" / f"{name}.npy") for name in SPLITS["val"][0]},
        "uv_lock_sha256": sha256(R2.parent / "uv.lock"),
        "environment": environment(),
    })
    print((R2 / "thresholds.json").read_text())


if __name__ == "__main__":
    main()
