import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import SPLITS, STEPS, flow, np, write_json
from pd.evaluate import spearman
from pd.predictors import one_step
from round2.checks import statistics2

R1 = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent / "pilot"
PLAN = {"val": ("P0", "P0f32"), "test": ("P0", "P0f32", "P1", "P2s0", "P2s1", "P3a", "P3b"), "ood": ("P0", "P0f32", "P2s0", "P3b")}


def main():
    solver = flow()
    rows = []
    start = time.perf_counter()
    for split, predictors in PLAN.items():
        for name in SPLITS[split][0]:
            reference = np.load(R1 / "data" / split / f"{name}.npy")
            for predictor in predictors:
                predicted = one_step(predictor, reference, split, name, R1 / "preds")
                for step in range(STEPS):
                    rows.append({"predictor": predictor, "split": split, "trajectory": name, "step": step,
                                 **statistics2(solver, reference[step], predicted[step], reference[step + 1])})
        print(f"{split} done {time.perf_counter() - start:.0f}s", flush=True)
    keys = [k for k in rows[0] if k not in ("predictor", "split", "trajectory", "step")]
    summary = {}
    for p, s in sorted({(r["predictor"], r["split"]) for r in rows}):
        g = [r for r in rows if r["predictor"] == p and r["split"] == s]
        summary[f"{p}/{s}"] = {k: {"min": min(r[k] for r in g), "max": max(r[k] for r in g), "median": float(np.median([r[k] for r in g]))} for k in keys}
        if p.startswith("P2"):
            summary[f"{p}/{s}"]["spearman_vs_D4"] = {k: spearman([r[k] for r in g], [r["D4"] for r in g])["rho"] for k in keys}
    write_json(OUT / "pilot_rows.json", rows)
    write_json(OUT / "pilot_summary.json", summary)


if __name__ == "__main__":
    main()
