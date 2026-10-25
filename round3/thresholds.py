import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pd.thresholds
from pd import SPLITS, environment, np, sha256, write_json
from round3 import R1, R2, R3
from round3.evaluate import onestep_task

EPS32 = float(np.finfo(np.float32).eps)
RULE = {
    "D2pp": "tau = max(10 x max over validation one-step steps of P0 and P0f32, 10 x eps(float32)); flagged if value > tau, non-finite, or E1 > E0",
    "Gp": "tau = max(10 x max over validation one-step steps of P0 and P0f32, 10 x eps(float32)); flagged if value > tau or non-finite",
    "G6": "tau = max(10 x max over validation one-step steps of P0 and P0f32, 1e-12); exploratory flag only",
}
FLOORS = {"D2pp": 10 * EPS32, "Gp": 10 * EPS32, "G6": 1e-12}


def main():
    records = onestep_task((R1 / "data", None, "val", ("P0", "P0f32")))
    write_json(R3 / "logs" / "mac" / "validation_controls.json", records)
    values = {}
    for key, low in FLOORS.items():
        column = [r[key] for r in records]
        if not all(np.isfinite(column)):
            raise FloatingPointError(f"non-finite validation statistic for {key}")
        values[key] = max(low, 10 * max(column))
    write_json(R3 / "thresholds.json", {
        "rule": RULE,
        "steps_per_predictor": len(records) // 2,
        "thresholds": values,
        "round1_thresholds_recomputed": pd.thresholds.compute(records, ("P0", "P0f32")),
        "round1_thresholds_equal": pd.thresholds.compute(records, ("P0", "P0f32")) == json.loads((R1 / "thresholds.json").read_text())["thresholds"],
        "round1_thresholds_sha256": sha256(R1 / "thresholds.json"),
        "round2_thresholds_sha256": sha256(R2 / "thresholds.json"),
        "round2_G_D2p_recomputed": {k: max(10 * max(r[k] for r in records), low) for k, low in (("D2p", 10 * EPS32), ("G", 1e-12))},
        "validation_max": {p: {k: max(r[k] for r in records if r["predictor"] == p) for k in ("D1", "D2", "D3", "D2p", "D2pp", "G", "G6", "Gp")} for p in ("P0", "P0f32")},
        "validation_data_sha256": {name: sha256(R1 / "data" / "val" / f"{name}.npy") for name in SPLITS["val"][0]},
        "uv_lock_sha256": sha256(R3.parent / "uv.lock"),
        "environment": environment(),
    })
    print((R3 / "thresholds.json").read_text())


if __name__ == "__main__":
    main()
