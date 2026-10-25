import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import SPLITS, STEPS, flow, np, write_json
from pd.evaluate import spearman
from pd.predictors import one_step
from round3 import R1, R2, R3
from round2.evaluate import cluster_bootstrap
from round3.checks import statistics3
from round3.evaluate import KEYS, flag, rollout_arrays, rollout_summary, series_of, sweep_summary
from round3.sweep import sweep
from round3.thresholds import FLOORS

OUT = R3 / "pilot"
PLAN = [(R1 / "data", R1 / "preds", "val", ("P0", "P0f32")),
        (R2 / "data", R2 / "preds", "r2test", ("P0", "P0f32", "P1", "P2s0", "P2s1", "P3a", "P3b")),
        (R2 / "data", R2 / "preds", "r2ood5", ("P0", "P0f32")),
        (R2 / "data", R2 / "preds", "r2ood6", ("P0", "P0f32"))]


def summary():
    rows = json.loads((OUT / "pilot_rows.json").read_text())
    val = [r for r in rows if r["split"] == "val"]
    t1 = json.loads((R1 / "thresholds.json").read_text())["thresholds"]
    t2 = json.loads((R2 / "thresholds.json").read_text())["thresholds"]
    t3 = {k: max(low, 10 * max(r[k] for r in val)) for k, low in FLOORS.items()}
    for r in rows:
        r["flags"] = flag(r, t1, t2, t3)
    groups = {}
    for r in rows:
        groups.setdefault(f"{r['predictor']}/{r['split']}", []).append(r)
    out = {"candidate_thresholds": t3, "groups": {}, "ranking": {}}
    for g, members in sorted(groups.items()):
        out["groups"][g] = {"steps": len(members), "flagged": {k: sum(r["flags"][k] for r in members) for k in KEYS},
                            "max": {k: max(r[k] for r in members) for k in ("D2", "D2p", "D2pp", "G", "G6", "Gp", "D3")},
                            "median": {k: float(np.median([r[k] for r in members])) for k in ("D2", "D2p", "D2pp", "G", "G6", "Gp", "D3", "D4", "edge") if k in members[0]}}
        if g.startswith("P2"):
            out["ranking"][g] = {k: spearman([r[k] for r in members], [r["D4"] for r in members])["rho"] for k in ("G", "G6", "Gp", "D3")}
    for label in ("P2s0", "P2s1"):
        out["ranking"][f"{label}/r2test_ci"] = {k: cluster_bootstrap(groups[f"{label}/r2test"], k) for k in ("Gp", "D3")}
    rollout = rollout_summary([r for r in rows if r["split"] == "rollout"], ("P2s0", "P2s1"))
    out["rollout"] = {"tracking": {p: {x: {k: v[k] for k in ("mean_rho", "ci95", "per_step")} for x, v in t.items()} for p, t in rollout["tracking"].items()},
                      "alarm": {rule: {p: v for p, v in a.items() if p != "records"} for rule, a in rollout["alarm"].items()},
                      "pooled": rollout["pooled"], "by_step": rollout["by_step"],
                      "A_over_D4_at_crossing": [series_of(steps)["A"][rec["crossing"] - 1] / steps[rec["crossing"] - 1]["D4"]
                                                for p in ("P2s0", "P2s1") for name, steps in rollout_arrays([r for r in rows if r["split"] == "rollout"])[p].items()
                                                for rec in [rollout["alarm"]["A"]["records"][p][name]] if rec["crossing"]]}
    sweeps = json.loads((OUT / "pilot_sweep.json").read_text())
    rates, floors = sweep_summary(sweeps, t1, t2, t3, ("r2test", "r2ood6"))
    out["sweep"] = {"floors": floors, "rates": rates}
    write_json(OUT / "pilot_summary.json", out)
    for g, v in out["groups"].items():
        print(g, v["flagged"], {k: f"{x:.2e}" for k, x in v["max"].items()})
    print(json.dumps(out["ranking"], indent=1)[:3000])
    print(json.dumps({p: {x: v["mean_rho"] for x, v in t.items()} for p, t in out["rollout"]["tracking"].items()}))
    print(json.dumps({rule: a.get("nets_pooled") for rule, a in out["rollout"]["alarm"].items()}))
    print({k: v["floor"] for k, v in floors.items()})


def main():
    if "--summary" in sys.argv:
        return summary()
    solver = flow()
    rows, start = [], time.perf_counter()
    for data, preds, split, predictors in PLAN:
        for name in SPLITS[split][0]:
            reference = np.load(data / split / f"{name}.npy")
            for predictor in predictors:
                predicted = one_step(predictor, reference, split, name, preds)
                for step in range(STEPS):
                    rows.append({"predictor": predictor, "split": split, "trajectory": name, "step": step,
                                 **statistics3(solver, reference[step], predicted[step], reference[step + 1])})
        print(f"{split} done {time.perf_counter() - start:.0f}s", flush=True)
    for label in ("P2s0", "P2s1"):
        for name in SPLITS["test"][0]:
            reference = np.load(R1 / "data" / "test" / f"{name}.npy")
            states = np.load(R1 / "preds" / label / "rollout" / f"{name}.npy")
            previous = reference[0]
            for step in range(STEPS):
                rows.append({"predictor": label, "split": "rollout", "trajectory": name, "step": step,
                             **statistics3(solver, previous, states[step], reference[step + 1])})
                previous = states[step]
    print(f"rollouts done {time.perf_counter() - start:.0f}s", flush=True)
    write_json(OUT / "pilot_rows.json", rows)
    sweeps = []
    for split in ("r2test", "r2ood6"):
        for name in SPLITS[split][0]:
            sweeps += [{"split": split, **r} for r in sweep(solver, np.load(R2 / "data" / split / f"{name}.npy"), name)]
        print(f"sweep {split} done {time.perf_counter() - start:.0f}s", flush=True)
    write_json(OUT / "pilot_sweep.json", sweeps)


if __name__ == "__main__":
    main()
