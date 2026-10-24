import argparse
import json
import time
from pathlib import Path

from pd import ROOT, SPLITS, STEPS, environment, flow, np, write_json
from pd.checks import CHECKS, flags, statistics
from pd.predictors import EVALUATED_SPLITS, NATIVE_DTYPE, ONE_STEP, one_step

WRONG = 0.01
FLAG_KEYS = CHECKS + ("any",)
HYPOTHESES = {
    "H1": ("P0", "any", "<=", 0.05),
    "H1b": ("P0f32", "any", "<=", 0.05),
    "H2": ("P3a", "D1", ">=", 0.95),
    "H3": ("P3b", "D2", ">=", 0.95),
    "H4": ("P1", "D3", ">=", 0.95),
}


def one_step_records(solver, data, preds, predictors, splits):
    out = []
    for split in splits:
        start = time.perf_counter()
        for name in SPLITS[split][0]:
            reference = np.load(data / split / f"{name}.npy")
            for predictor in predictors:
                predicted = one_step(predictor, reference, split, name, preds)
                for step in range(STEPS):
                    stats = statistics(solver, reference[step], predicted[step], reference[step + 1])
                    out.append({"predictor": predictor, "split": split, "trajectory": name, "step": step, **stats})
        print(f"{split}: {', '.join(predictors)} in {time.perf_counter() - start:.1f} s", flush=True)
    return out


def rollout_records(solver, data, preds, labels):
    out = []
    for name in SPLITS["test"][0]:
        reference = np.load(data / "test" / f"{name}.npy")
        for label in labels:
            states = np.load(preds / label / "rollout" / f"{name}.npy")
            previous = reference[0]
            for step in range(STEPS):
                stats = statistics(solver, previous, states[step], reference[step + 1])
                out.append({"predictor": label, "split": "rollout", "trajectory": name, "step": step, **stats})
                previous = states[step]
    return out


def compute(data, preds):
    solver = flow()
    records = one_step_records(solver, data, preds, ONE_STEP, EVALUATED_SPLITS)
    return records + rollout_records(solver, data, preds, ("P2s0", "P2s1"))


def finite(values):
    return [v for v in values if np.isfinite(v)]


def ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for t in range(i, j + 1):
            out[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if np.isfinite(a) and np.isfinite(b)]
    if len(pairs) < 3:
        return {"rho": None, "n": len(pairs), "excluded_non_finite": len(x) - len(pairs)}
    rx, ry = ranks([a for a, _ in pairs]), ranks([b for _, b in pairs])
    return {"rho": float(np.corrcoef(rx, ry)[0, 1]), "n": len(pairs), "excluded_non_finite": len(x) - len(pairs)}


def group_summary(group, eps):
    out = {"steps": len(group), "flagged": {k: sum(r["flags"][k] for r in group) for k in FLAG_KEYS}}
    out["energy_increase_steps"] = sum(r["E1"] > r["E0"] for r in group)
    for check in CHECKS + ("D4",):
        values = finite(r[check] for r in group)
        out[check] = {
            "max": max(values) if values else None,
            "median": float(np.median(values)) if values else None,
            "non_finite": len(group) - len(values),
            "at_precision_floor": sum(v < 10 * eps for v in values),
        }
    return out


def confusion(group):
    out = {}
    for key in FLAG_KEYS:
        cells = {"flagged_and_wrong": 0, "flagged_not_wrong": 0, "wrong_not_flagged": 0, "neither": 0}
        for r in group:
            wrong = not np.isfinite(r["D4"]) or r["D4"] > WRONG
            flagged = r["flags"][key]
            name = ("flagged_and_wrong" if wrong else "flagged_not_wrong") if flagged else ("wrong_not_flagged" if wrong else "neither")
            cells[name] += 1
        out[key] = cells
    return out


def summarize(records, thresholds):
    for r in records:
        r["flags"] = flags(r, thresholds)
    groups = {}
    for r in records:
        groups.setdefault((r["predictor"], r["split"]), []).append(r)
    summary = {
        f"{p}/{s}": group_summary(g, float(np.finfo(NATIVE_DTYPE[p]).eps))
        for (p, s), g in sorted(groups.items())
    }
    hypotheses = {}
    for name, (predictor, key, op, bound) in HYPOTHESES.items():
        group = summary[f"{predictor}/test"]
        flagged, steps = group["flagged"][key], group["steps"]
        share = flagged / steps
        hypotheses[name] = {
            "predictor": predictor, "check": key, "flagged": flagged, "steps": steps, "share": share,
            "criterion": f"share {op} {bound}", "pass": share <= bound if op == "<=" else share >= bound,
        }
    exploratory = {}
    for label in ("P2s0", "P2s1"):
        test = groups[(label, "test")]
        rollout = groups[(label, "rollout")]
        exploratory[label] = {
            "E1_share_flagged_test": {k: summary[f"{label}/test"]["flagged"][k] / len(test) for k in FLAG_KEYS},
            "E1_spearman_D3_D4_test": spearman([r["D3"] for r in test], [r["D4"] for r in test]),
            "confusion_test": confusion(test),
            "E2_rollout_by_step": [
                {
                    "step": k + 1,
                    "steps": len(rows),
                    "flagged": {key: sum(r["flags"][key] for r in rows) for key in FLAG_KEYS},
                    "median": {c: float(np.median(finite(r[c] for r in rows))) for c in CHECKS + ("D4",)},
                    "max": {c: max(finite(r[c] for r in rows)) for c in CHECKS + ("D4",)},
                }
                for k in range(STEPS)
                for rows in [[r for r in rollout if r["step"] == k]]
            ],
        }
    return {"thresholds": thresholds, "hypotheses": hypotheses, "groups": summary, "exploratory": exploratory}


def evaluate(machine, data, preds, results):
    thresholds_file = json.loads((ROOT / "thresholds.json").read_text())
    start = time.perf_counter()
    records = compute(data, preds)
    seconds = time.perf_counter() - start
    from pd.thresholds import compute as recompute
    validation = [r for r in records if r["split"] == "val"]
    verdicts = summarize(records, thresholds_file["thresholds"])
    verdicts["machine"] = machine
    verdicts["seconds"] = seconds
    verdicts["thresholds_recomputed_here_informational"] = recompute(validation, ("P0", "P0f32"))
    out = results / machine
    write_json(out / "stats.json", records)
    write_json(out / "verdicts.json", verdicts)
    write_json(out / "environment.json", environment())
    for name, h in verdicts["hypotheses"].items():
        print(f"{name}: {h['predictor']} {h['check']} {h['flagged']}/{h['steps']} {'PASS' if h['pass'] else 'FAIL'}", flush=True)


def ledgers(results, out):
    machines = sorted(p.name for p in results.iterdir() if (p / "stats.json").is_file())
    stats = {m: json.loads((results / m / "stats.json").read_text()) for m in machines}
    thresholds = {m: json.loads((results / m / "verdicts.json").read_text())["thresholds"] for m in machines}
    false_positives = []
    for m in machines:
        eps = {p: float(np.finfo(NATIVE_DTYPE[p]).eps) for p in NATIVE_DTYPE}
        for r in stats[m]:
            if r["predictor"] not in ("P0", "P0f32"):
                continue
            for check in CHECKS:
                if not r["flags"][check]:
                    continue
                entry = {
                    "machine": m, "predictor": r["predictor"], "split": r["split"], "seed": r["trajectory"],
                    "step": r["step"], "check": check, "value": r[check], "threshold": thresholds[m][check],
                    "E0": r["E0"], "E1": r["E1"], "status": "open", "explanation": None,
                }
                floor = 10 * eps[r["predictor"]]
                increase = (r["E1"] - r["E0"]) / r["E0"]
                if check == "D2" and r[check] <= thresholds[m][check] and 0 < increase < floor:
                    entry["status"] = "explained"
                    entry["explanation"] = f"energy-increase rule only; relative increase {increase:.3e} is below 10 x eps({NATIVE_DTYPE[r['predictor']]}) = {floor:.3e}"
                false_positives.append(entry)
    index = {}
    for m in machines:
        for r in stats[m]:
            index.setdefault((r["predictor"], r["split"], r["trajectory"], r["step"]), {})[m] = r
    discrepancies = []
    max_difference = {c: 0.0 for c in CHECKS + ("D4", "E0", "E1")}
    for key, rows in sorted(index.items()):
        if len(rows) < 2:
            continue
        for c in max_difference:
            values = [rows[m][c] for m in rows]
            if all(np.isfinite(values)):
                max_difference[c] = max(max_difference[c], max(values) - min(values))
        for check in FLAG_KEYS:
            verdict = {m: rows[m]["flags"][check] for m in rows}
            if len(set(verdict.values())) > 1:
                discrepancies.append({
                    "predictor": key[0], "split": key[1], "seed": key[2], "step": key[3], "check": check,
                    "verdict": verdict,
                    "values": {m: {c: rows[m][c] for c in CHECKS + ("E0", "E1")} for m in rows},
                    "thresholds": {m: thresholds[m] for m in rows},
                })
    out.mkdir(parents=True, exist_ok=True)
    for name, entries in (("false_positives", false_positives), ("discrepancies", discrepancies)):
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
    write_json(results / "comparison.json", {
        "machines": machines,
        "max_abs_difference_between_machines": max_difference,
        "discrepancies": len(discrepancies),
        "false_positives": {"open": sum(e["status"] == "open" for e in false_positives), "explained": sum(e["status"] == "explained" for e in false_positives)},
    })
    print(f"machines {machines}: {len(discrepancies)} discrepancies, {len(false_positives)} false positives", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--preds", type=Path, default=ROOT / "preds")
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument("--ledgers", action="store_true")
    args = parser.parse_args()
    if args.ledgers:
        ledgers(args.results, ROOT / "ledgers")
    else:
        evaluate(args.machine, args.data, args.preds, args.results)


if __name__ == "__main__":
    main()
