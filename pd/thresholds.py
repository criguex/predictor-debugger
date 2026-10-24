import argparse
from pathlib import Path

from pd import ROOT, SPLITS, environment, flow, np, sha256, write_json
from pd.checks import CHECKS
from pd.evaluate import one_step_records

RULE = "tau = 10 x max over validation one-step steps of the statistic, floor 1e-12; flagged if value > tau or non-finite"
FLOOR = 1e-12


def compute(records, predictors):
    out = {}
    for check in CHECKS:
        values = [r[check] for r in records if r["predictor"] in predictors]
        if not values or not all(np.isfinite(values)):
            raise FloatingPointError(f"non-finite or missing validation statistic for {check}")
        out[check] = max(FLOOR, 10 * max(values))
    return out


def validation_max(records, predictor):
    return {check: max(r[check] for r in records if r["predictor"] == predictor) for check in CHECKS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "thresholds.json")
    parser.add_argument("--stats", type=Path, default=ROOT / "logs" / "mac" / "validation_controls.json")
    args = parser.parse_args()
    records = one_step_records(flow(), args.data, None, ("P0", "P0f32"), ("val",))
    write_json(args.stats, records)
    write_json(args.out, {
        "rule": RULE,
        "steps_per_predictor": len(records) // 2,
        "thresholds": compute(records, ("P0", "P0f32")),
        "float64_only_secondary": compute(records, ("P0",)),
        "validation_max": {p: validation_max(records, p) for p in ("P0", "P0f32")},
        "validation_data_sha256": {name: sha256(args.data / "val" / f"{name}.npy") for name in SPLITS["val"][0]},
        "environment": environment(),
        "decides_H1_H4": "thresholds",
    })
    print(args.out.read_text())


if __name__ == "__main__":
    main()
