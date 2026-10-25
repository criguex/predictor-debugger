import argparse
import json
import time
from pathlib import Path

import pd.evaluate
from pd import environment, flow, np, write_json
from pd.checks import CHECKS, flags
from pd.evaluate import HYPOTHESES, spearman
from round2 import GRADED, NEW_SPLITS, ONE_STEP, R1, R2
from round2.checks import statistics2

pd.evaluate.statistics = statistics2

KEYS = ("D1", "D2", "D3", "D2p", "D2p_mag", "G", "any", "any2")
STATS = ("D1", "D2", "D2h", "D2p", "D3", "D3p", "G", "Gs", "Gc", "D4", "D4s", "D4c")
GAUGES = ("G", "Gs", "D3", "D3p", "D2", "D2p")
BOOTSTRAP, BOOTSTRAP_SEED = 2000, 20261024


def compute(data, preds):
    solver = flow()
    records = pd.evaluate.one_step_records(solver, R1 / "data", preds, ("P0", "P0f32"), ("val",))
    records += pd.evaluate.one_step_records(solver, data, preds, ONE_STEP, tuple(NEW_SPLITS))
    return records + pd.evaluate.one_step_records(solver, data, preds, GRADED, ("r2test",))


def flag(r, t1, t2):
    out = flags(r, t1)
    energy = not np.isfinite(r["E0"]) or not np.isfinite(r["E1"]) or r["E1"] > r["E0"]
    out["D2p_mag"] = not np.isfinite(r["D2p"]) or r["D2p"] > t2["D2p"]
    out["D2p"] = out["D2p_mag"] or energy
    out["G"] = not np.isfinite(r["G"]) or r["G"] > t2["G"]
    out["any2"] = out["D1"] or out["D2p"] or out["D3"]
    return out


def cluster_bootstrap(rows, x, y="D4"):
    by = {}
    for r in rows:
        by.setdefault(r["trajectory"], []).append((r[x], r[y]))
    names = sorted(by)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    values = []
    for _ in range(BOOTSTRAP):
        pairs = [p for i in rng.integers(0, len(names), len(names)) for p in by[names[i]]]
        rho = spearman([a for a, _ in pairs], [b for _, b in pairs])["rho"]
        values.append(rho if rho is not None and np.isfinite(rho) else np.nan)
    low, high = np.nanpercentile(values, [2.5, 97.5])
    point = spearman([r[x] for r in rows], [r[y] for r in rows])
    return {"rho": point["rho"], "n": point["n"], "trajectories": len(names), "ci95": [float(low), float(high)],
            "replicates": BOOTSTRAP, "seed": BOOTSTRAP_SEED, "non_finite_replicates": int(np.sum(np.isnan(values)))}


def finite(values):
    return [v for v in values if np.isfinite(v)]


def group_summary(group):
    out = {"steps": len(group), "flagged": {k: sum(r["flags"][k] for r in group) for k in KEYS}}
    for s in STATS:
        values = finite([r[s] for r in group])
        out[s] = {"min": min(values), "median": float(np.median(values)), "max": max(values), "non_finite": len(group) - len(values)} if values else None
    return out


def summarize(records, t1, t2):
    for r in records:
        r["flags"] = flag(r, t1, t2)
    groups = {}
    for r in records:
        groups.setdefault(f"{r['predictor']}/{r['split']}", []).append(r)
    summary = {g: group_summary(rows) for g, rows in sorted(groups.items())}
    hypotheses = {}
    for name, (predictor, key, op, bound) in HYPOTHESES.items():
        g = summary[f"{predictor}/r2test"]
        share = g["flagged"][key] / g["steps"]
        hypotheses[name] = {"predictor": predictor, "check": key, "flagged": g["flagged"][key], "steps": g["steps"], "share": share,
                            "criterion": f"share {op} {bound}", "pass": share <= bound if op == "<=" else share >= bound}
    controls = {f"{p}/{s}": summary[f"{p}/{s}"]["flagged"]["D2p"] for p in ("P0", "P0f32") for s in NEW_SPLITS}
    hypotheses["H5"] = {"predictor": "P0, P0f32", "check": "D2p", "flagged": sum(controls.values()), "steps": sum(summary[g]["steps"] for g in controls),
                        "by_group": controls, "criterion": "0 flagged in every group", "pass": sum(controls.values()) == 0}
    g = summary["P3b/r2test"]
    hypotheses["H6"] = {"predictor": "P3b", "check": "D2p_mag", "flagged": g["flagged"]["D2p_mag"], "steps": g["steps"], "share": g["flagged"]["D2p_mag"] / g["steps"],
                        "criterion": "share >= 0.95", "pass": g["flagged"]["D2p_mag"] / g["steps"] >= 0.95}
    within = {label: cluster_bootstrap(groups[f"{label}/r2test"], "G") for label in ("P2s0", "P2s1")}
    hypotheses["H7"] = {"predictor": "P2s0, P2s1", "check": "Spearman(G, D4)", "by_group": within,
                        "criterion": "rho >= 0.8 and CI95 low >= 0.6 for both", "pass": all(v["rho"] >= 0.8 and v["ci95"][0] >= 0.6 for v in within.values())}
    pooled_rows = [r for label in GRADED for r in groups[f"{label}/r2test"]]
    pooled = cluster_bootstrap(pooled_rows, "G")
    hypotheses["H8"] = {"predictor": "+".join(GRADED), "check": "Spearman(G, D4)", **pooled,
                        "criterion": "rho >= 0.9 and CI95 low >= 0.8", "pass": pooled["rho"] >= 0.9 and pooled["ci95"][0] >= 0.8}
    ranking = {}
    for g, rows in sorted(groups.items()):
        if g.startswith("P2"):
            ranking[g] = {s: spearman([r[s] for r in rows], [r["D4"] for r in rows])["rho"] for s in GAUGES}
            ranking[g]["median_G_over_D4"] = float(np.median([r["G"] / r["D4"] for r in rows]))
    ranking["graded_pooled/r2test"] = {s: spearman([r[s] for r in pooled_rows], [r["D4"] for r in pooled_rows])["rho"] for s in GAUGES}
    intervals = {f"{label}/r2test": {s: cluster_bootstrap(groups[f"{label}/r2test"], s) for s in ("D3", "D3p", "Gs")} for label in ("P2s0", "P2s1")}
    intervals["graded_pooled/r2test"] = {s: cluster_bootstrap(pooled_rows, s) for s in ("D3", "D3p", "Gs")}
    false_positives = {f"{p}/{s}": {k: summary[f"{p}/{s}"]["flagged"][k] for k in ("D1", "D2", "D3", "D2p", "G")} for p in ("P0", "P0f32") for s in ("val",) + tuple(NEW_SPLITS)}
    return {"thresholds_round1": t1, "thresholds_round2": t2, "hypotheses": hypotheses, "groups": summary,
            "exploratory": {"ranking_spearman_vs_D4": ranking, "ranking_ci95": intervals, "control_flags": false_positives}}


def thresholds():
    t1 = json.loads((R1 / "thresholds.json").read_text())["thresholds"]
    t2 = json.loads((R2 / "thresholds.json").read_text())["thresholds"]
    return t1, t2


def evaluate(machine, data, preds):
    start = time.perf_counter()
    records = compute(data, preds)
    seconds = time.perf_counter() - start
    verdicts = summarize(records, *thresholds())
    verdicts["machine"], verdicts["seconds"] = machine, seconds
    out = R2 / "results" / machine
    write_json(out / "stats.json", records)
    write_json(out / "verdicts.json", verdicts)
    write_json(out / "environment.json", environment())
    for name, h in verdicts["hypotheses"].items():
        print(f"{name}: {h['predictor']} {h['check']} {h.get('flagged', h.get('rho'))} {'PASS' if h['pass'] else 'FAIL'}", flush=True)


def ledgers():
    results = R2 / "results"
    machines = sorted(p.name for p in results.iterdir() if (p / "stats.json").is_file())
    stats = {m: json.loads((results / m / "stats.json").read_text()) for m in machines}
    _, t2 = thresholds()
    t1 = json.loads((R1 / "thresholds.json").read_text())["thresholds"]
    limits = {**t1, **t2}
    false_positives, index = [], {}
    for m in machines:
        for r in stats[m]:
            index.setdefault((r["predictor"], r["split"], r["trajectory"], r["step"]), {})[m] = r
            if r["predictor"] not in ("P0", "P0f32"):
                continue
            for check in ("D1", "D2", "D3", "D2p", "G"):
                if r["flags"][check]:
                    false_positives.append({"machine": m, "predictor": r["predictor"], "split": r["split"], "seed": r["trajectory"], "step": r["step"],
                                            "check": check, "value": r[check], "threshold": limits[check], "E0": r["E0"], "E1": r["E1"],
                                            "debugger_check": check != "G", "status": "open", "explanation": None})
    discrepancies, difference = [], {s: 0.0 for s in STATS + ("E0", "E1")}
    for key, rows in sorted(index.items()):
        if len(rows) < 2:
            continue
        for s in difference:
            values = [rows[m][s] for m in rows]
            if all(np.isfinite(values)):
                difference[s] = max(difference[s], max(values) - min(values))
        for k in KEYS:
            verdict = {m: rows[m]["flags"][k] for m in rows}
            if len(set(verdict.values())) > 1:
                discrepancies.append({"predictor": key[0], "split": key[1], "seed": key[2], "step": key[3], "check": k, "verdict": verdict,
                                      "values": {m: {s: rows[m][s] for s in STATS + ("E0", "E1")} for m in rows}})
    hypotheses = {m: {h: v["pass"] for h, v in json.loads((results / m / "verdicts.json").read_text())["hypotheses"].items()} for m in machines}
    (R2 / "ledgers").mkdir(parents=True, exist_ok=True)
    for name, entries in (("false_positives", false_positives), ("discrepancies", discrepancies)):
        with (R2 / "ledgers" / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
    write_json(results / "comparison.json", {"machines": machines, "max_abs_difference_between_machines": difference, "discrepancies": len(discrepancies),
                                             "false_positives_by_check": {c: sum(e["check"] == c for e in false_positives) for c in ("D1", "D2", "D3", "D2p", "G")},
                                             "hypotheses_by_machine": hypotheses})
    print(f"machines {machines}: {len(discrepancies)} discrepancies, {len(false_positives)} control flags", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine")
    parser.add_argument("--data", type=Path, default=R2 / "data")
    parser.add_argument("--preds", type=Path, default=R2 / "preds")
    parser.add_argument("--ledgers", action="store_true")
    args = parser.parse_args()
    ledgers() if args.ledgers else evaluate(args.machine, args.data, args.preds)


if __name__ == "__main__":
    main()
