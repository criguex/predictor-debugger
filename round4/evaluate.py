import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import round3.evaluate as r3
from pd import SPLITS, environment, flow, np, write_json
from pd.checks import norm
from pd.data import advance
from pd.evaluate import HYPOTHESES, spearman
from round2.evaluate import BOOTSTRAP, BOOTSTRAP_SEED, cluster_bootstrap
from round3.checks import statistics3
from round3.sweep import sweep
from round4 import LEVEL, NEW_SPLITS, ONE_STEP, R1, R2, R3, R4, ROLL, ROLLED, ROLLED_NETS
from round4.transport import breeding_direction, defects, tl_advance

r3.SWEEP_SPLITS = tuple(NEW_SPLITS)

VARIANTS = ("fp3", "r6", "r4", "r6u")
PRIMARY = "fp3"
CHUNK = 5
SERIES = ("E", "A", "C", "S", "Eor", "E_r6", "E_r4", "E_r6u", "A_rss")
DEBUGGER_CHECKS = ("D1", "D3", "D2pp", "Gp")
EXPLAINED_BY = {"D2": "D2p", "D2p": "D2pp", "G": "Gp", "G6": "Gp"}
NEW_STATS = ("E_fp3", "E_r6", "E_r4", "E_r6u", "Eor", "S", "lam", "dhat_err_fp3", "dhat_err_r6", "dhat_err_r4", "dhat_err_r6u",
             "lin_err", "fp_change", "D4loc")


def ratio(a, b):
    return float(a / b) if b > 0 and np.isfinite(a / b) else None


def rolled_states(solver, predictor, reference, split, name, preds):
    if predictor in ("P0", "P0f32", "P1"):
        horizon = len(reference) - 1
        if predictor == "P0":
            return reference[1:]
        if predictor == "P1":
            return np.array([reference[0]] * horizon)
        states, state = [], reference[0]
        for _ in range(horizon):
            state = advance(solver, state).astype(np.float32).astype(np.float64)
            states.append(state)
        return np.array(states)
    return np.load(preds / predictor / split / f"{name}.npy")


def transport_rows(solver, predictor, split, name, reference, states):
    previous, out = reference[0], []
    errors = {v: np.zeros_like(solver.transform(reference[0])) for v in VARIANTS}
    oracle, bred, s = np.zeros_like(errors[PRIMARY]), breeding_direction(solver, name), 0.0
    for step in range(len(states)):
        u1 = states[step]
        row = {"predictor": predictor, "split": split, "trajectory": name, "step": step,
               **statistics3(solver, previous, u1, reference[step + 1]), "edge": r3.edge_fraction(solver, u1)}
        with np.errstate(all="ignore"):
            exact, moved = tl_advance(solver, previous, [errors[v] for v in VARIANTS] + [oracle, bred])
            estimates, row["fp_change"] = defects(solver, previous, u1)
            h1, true_error = solver.transform(u1), solver.transform(u1 - reference[step + 1])
            local = h1 - solver.transform(exact)
            scale = norm(h1)
            for v, carried in zip(VARIANTS, moved):
                errors[v] = carried + estimates[v]
                row[f"E_{v}"] = float(norm(errors[v]) / scale)
                row[f"dhat_err_{v}"] = ratio(norm(estimates[v] - local), norm(local))
            oracle = moved[len(VARIANTS)] + local
            lam = float(norm(moved[-1]))
            bred = moved[-1] / lam
            s = lam * s + row["G"]
            row.update({"Eor": float(norm(oracle) / scale), "lam": lam, "S": s, "lin_err": ratio(norm(oracle - true_error), norm(true_error)),
                        "D4loc": float(norm(u1 - exact) / norm(exact))})
        out.append(row)
        previous = u1
    return out


def rollout_task(args):
    data, preds, split, predictor, names = args
    solver, out = flow(), []
    for name in names:
        reference = np.load(data / split / f"{name}.npy")
        out += transport_rows(solver, predictor, split, name, reference, rolled_states(solver, predictor, reference, split, name, preds))
    return out


def sweep_task(args):
    data, split, names = args
    solver, out = flow(), []
    for name in names:
        out += [{"split": split, **r} for r in sweep(solver, np.load(data / split / f"{name}.npy"), name)]
    return out


def chunks(names):
    return [names[i:i + CHUNK] for i in range(0, len(names), CHUNK)]


def tasks(data, preds, parts):
    out = []
    if "rollout" in parts:
        out += [("rollout", rollout_task, (data, preds, ROLL, p, c)) for p in ROLLED for c in chunks(SPLITS[ROLL][0])]
    if "sweep" in parts:
        out += [("sweep", sweep_task, (data, split, c)) for split in NEW_SPLITS for c in chunks(SPLITS[split][0])]
    if "onestep" in parts:
        out += [("onestep", r3.onestep_task, (R1 / "data", preds, "val", ("P0", "P0f32")))]
        out += [("onestep", r3.onestep_task, (data, preds, split, (p,))) for split in NEW_SPLITS for p in ONE_STEP]
    return out


def run(plan, jobs):
    results = {part: [] for part, _, _ in plan}
    start = time.perf_counter()
    label = lambda part, args: " ".join([part] + [str(a[0]) if isinstance(a, (list, tuple)) else str(a) for a in args if a is not None and not isinstance(a, Path)])
    if jobs == 1:
        for part, task, args in plan:
            results[part] += task(args)
            print(f"{label(part, args)} done {time.perf_counter() - start:.0f}s", flush=True)
        return results
    with ProcessPoolExecutor(jobs) as pool:
        futures = [pool.submit(task, args) for _, task, args in plan]
        for (part, _, args), future in zip(plan, futures):
            results[part] += future.result()
            print(f"{label(part, args)} done {time.perf_counter() - start:.0f}s", flush=True)
    return results


def compute(data, preds, jobs=1, parts=("onestep", "sweep", "rollout")):
    return run(tasks(data, preds, parts), jobs)


def thresholds():
    t1 = json.loads((R1 / "thresholds.json").read_text())["thresholds"]
    t2 = json.loads((R2 / "thresholds.json").read_text())["thresholds"]
    t3 = json.loads((R3 / "thresholds.json").read_text())["thresholds"]
    t4 = json.loads((R4 / "thresholds.json").read_text())["thresholds"]
    return t1, t2, t3, t4


def ranking_hypothesis(groups, split, gauge, comparator, labels=("P2s0", "P2s1")):
    meets = lambda v: v["rho"] >= 0.8 and v["ci95"][0] >= 0.6
    target = {label: cluster_bootstrap(groups[f"{label}/{split}"], gauge) for label in labels}
    against = {label: cluster_bootstrap(groups[f"{label}/{split}"], comparator) for label in labels}
    passed, comparator_passes = all(meets(v) for v in target.values()), all(meets(v) for v in against.values())
    return {"predictor": ", ".join(labels), "check": f"Spearman({gauge}, D4)", "by_group": target,
            "comparator": {"check": f"Spearman({comparator}, D4)", "by_group": against, "meets_criterion": comparator_passes},
            "criterion": "rho >= 0.8 and CI95 low >= 0.6 for each; comparator must fail", "pass": passed,
            "verdict": "FAIL" if not passed else "NON-DISCRIMINATIVE" if comparator_passes else "PASS"}


def sanity(results, groups, summary, t1, t2, t3, split="r4test"):
    h = {name: r3.rate_hypothesis(summary, p, split, key, op, bound) for name, (p, key, op, bound) in HYPOTHESES.items()}
    h["H5"] = r3.zero_hypothesis(summary, "D2p", NEW_SPLITS)
    h["H6"] = r3.rate_hypothesis(summary, "P3b", split, "D2p_mag", ">=", 0.95)
    h["H7"] = ranking_hypothesis(groups, split, "G", "D3")
    h["H9"] = r3.zero_hypothesis(summary, "D2pp", NEW_SPLITS)
    rates, floors = r3.sweep_summary(results["sweep"], t1, t2, t3, tuple(NEW_SPLITS))
    h["H10"] = r3.floor_hypothesis(floors)
    h["H10b"] = r3.rate_hypothesis(summary, "P3b", split, "D2pp_mag", ">=", 0.95)
    h["H11"] = r3.zero_hypothesis(summary, "Gp", NEW_SPLITS)
    cells = {f"{p}/{s}": r3.rate_hypothesis(summary, p, s, "Gp", ">=", 0.95) for p in ("P1", "P3a", "P3b") for s in NEW_SPLITS}
    h["H12"] = {"predictor": "P1, P3a, P3b", "check": "Gp", "flagged": sum(v["flagged"] for v in cells.values()), "steps": sum(v["steps"] for v in cells.values()),
                "by_group": {k: v["flagged"] for k, v in cells.items()}, "criterion": "share >= 0.95 in every group", "pass": all(v["pass"] for v in cells.values())}
    h["H13"] = ranking_hypothesis(groups, split, "Gp", "D3")
    return h, {"rates": rates, "floors": floors}


def series_of(steps):
    g = np.array([r["G"] for r in steps])
    out = {"D4": [r["D4"] for r in steps], "A": np.cumsum(g).tolist(), "A_rss": np.sqrt(np.cumsum(g ** 2)).tolist(),
           "C": np.cumsum([r["D3"] for r in steps]).tolist(), "E": [r[f"E_{PRIMARY}"] for r in steps], "k": list(range(1, len(steps) + 1))}
    for key in ("S", "Eor", "E_r6", "E_r4", "E_r6u"):
        out[key] = [r[key] for r in steps]
    return out


def paired_tracking(series, keys, y="D4"):
    names = sorted(series)
    point = {x: r3.within_step(series, x, y, names) for x in keys}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    replicates = {x: [] for x in keys}
    for _ in range(BOOTSTRAP):
        sample = [names[i] for i in rng.integers(0, len(names), len(names))]
        for x in keys:
            replicates[x].append(r3.within_step(series, x, y, sample)[0])
    replicates = {x: np.array(v) for x, v in replicates.items()}
    interval = lambda v: [float(q) for q in np.nanpercentile(v, [2.5, 97.5])]
    out = {x: {"mean_rho": point[x][0], "per_step": point[x][1], "ci95": interval(replicates[x]), "non_finite_replicates": int(np.sum(np.isnan(replicates[x])))} for x in keys}
    for x in keys:
        if x != "E":
            diff = replicates["E"] - replicates[x]
            out[x]["delta_vs_E"] = {"delta": point["E"][0] - point[x][0], "ci95": interval(diff), "non_finite_replicates": int(np.sum(np.isnan(diff)))}
    return out


def calibration(series, key, horizon):
    return [float(np.median([series[n][key][k] / series[n]["D4"][k] for n in series])) for k in range(horizon)]


def alarm_of(s, key, level=LEVEL):
    return [not np.isfinite(v) or v >= level for v in s[key]]


def lead_times(records):
    return [r["crossing"] - r["alarm"] for r in records if r["crossing"] is not None and r["alarm"] is not None]


def rollout_summary(rows, level=LEVEL, nets=ROLLED_NETS):
    by = r3.rollout_arrays(rows)
    out = {"tracking": {}, "calibration": {}, "by_step": {}, "alarm": {}, "lead_times": {}}
    records = {"E": {}, "A": {}, "S": {}, "Eor": {}}
    for predictor, trajectories in sorted(by.items()):
        series = {n: series_of(steps) for n, steps in trajectories.items()}
        horizon = len(next(iter(series.values()))["D4"])
        stats = ("D4", "D4loc", "G", "Gp", "D3", "lam", "lin_err", "fp_change") + tuple(f"E_{v}" for v in VARIANTS) + tuple(f"dhat_err_{v}" for v in VARIANTS) + ("Eor", "S")
        out["by_step"][predictor] = [{"step": k + 1, **{s: float(np.median(r3.finite([trajectories[n][k].get(s) for n in trajectories])))
                                                        for s in stats if r3.finite([trajectories[n][k].get(s) for n in trajectories])},
                                      "A_median": float(np.median([series[n]["A"][k] for n in series])),
                                      "ftle_median": float(np.median([np.sum(np.log([trajectories[n][j]["lam"] for j in range(k + 1)])) / ((k + 1) * 0.1) for n in trajectories])),
                                      "flagged": {key: sum(trajectories[n][k]["flags"][key] for n in trajectories) for key in ("D1", "D3", "D2pp", "Gp", "any3")}}
                                     for k in range(horizon)]
        if predictor in nets:
            out["tracking"][predictor] = paired_tracking(series, SERIES)
            out["calibration"][predictor] = {key: calibration(series, key, horizon) for key in ("E", "Eor", "A", "S", "E_r6", "E_r4", "E_r6u")}
        for name, s in series.items():
            for key in records:
                records[key].setdefault(predictor, {})[name] = r3.alarm_record(s, alarm_of(s, key, level if key == "E" else LEVEL))
    for key, by_predictor in records.items():
        out["alarm"][key] = {p: r3.alarm_rates(list(v.values())) for p, v in sorted(by_predictor.items())}
        pooled = {}
        for p in nets:
            for name, record in by_predictor.get(p, {}).items():
                pooled.setdefault(name, []).append(record)
        out["alarm"][key]["nets_pooled"] = {**r3.alarm_rates([r for v in pooled.values() for r in v]), **r3.bootstrap_alarm(pooled)}
        out["alarm"][key]["records"] = {p: v for p, v in sorted(by_predictor.items())}
        out["lead_times"][key] = {p: lead_times(by_predictor[p].values()) for p in nets if p in by_predictor}
    return out


def tracking_hypothesis(rollout, nets=ROLLED_NETS):
    by, tracks, discriminates = {}, True, True
    for p in nets:
        t = rollout["tracking"][p]
        e = t["E"]
        meets = e["mean_rho"] >= 0.8 and e["ci95"][0] >= 0.6 and e["per_step"][-1] >= 0.7
        beats = {x: t[x]["delta_vs_E"]["delta"] >= 0.1 and t[x]["delta_vs_E"]["ci95"][0] > 0 for x in ("A", "C")}
        by[p] = {"E": {"mean_rho": e["mean_rho"], "ci95": e["ci95"], "rho_last": e["per_step"][-1]}, "pass": meets,
                 "delta_vs_A": t["A"]["delta_vs_E"], "delta_vs_C": t["C"]["delta_vs_E"], "discriminates": all(beats.values())}
        tracks, discriminates = tracks and meets, discriminates and all(beats.values())
    return {"predictor": ", ".join(nets), "check": f"within-step Spearman(E_{PRIMARY}, D4)", "by_group": by,
            "criterion": "each net: mean rho >= 0.8, CI95 low >= 0.6, rho at k=20 >= 0.7; discrimination: delta vs A and vs C >= 0.1 with paired CI95 low > 0",
            "pass": tracks, "discriminates": discriminates, "verdict": "FAIL" if not tracks else "PASS" if discriminates else "NON-DISCRIMINATIVE"}


def calibration_hypothesis(rollout, nets=ROLLED_NETS):
    by = {p: rollout["calibration"][p]["E"] for p in nets}
    inside = {p: all(1 / 1.5 <= v <= 1.5 for v in by[p]) for p in nets}
    return {"predictor": ", ".join(nets), "check": f"median E_{PRIMARY}/D4 per step", "by_group": {p: {"median_ratio": by[p], "pass": inside[p]} for p in nets},
            "criterion": "median ratio in [1/1.5, 1.5] at every step, each net", "pass": all(inside.values())}


def control_hypothesis(rollout, controls):
    alarms = {p: rollout["alarm"]["E"][p]["alarms"] for p in ("P0", "P0f32")}
    p1 = rollout["alarm"]["E"]["P1"]
    new = [c for c in controls if c["new"]]
    passed = sum(alarms.values()) == 0 and not new and p1["on_time_share"] is not None and p1["on_time_share"] >= 0.95
    return {"predictor": "P0, P0f32, P1 rollouts", "check": f"E_{PRIMARY} alarm", "alarms": alarms, "P1": {k: v for k, v in p1.items()},
            "control_flags": len(controls), "new_false_positives": len(new),
            "new_by_check": {k: sum(c["check"] == k for c in new) for k in sorted({c["check"] for c in new})},
            "criterion": "0 E alarms on P0/P0f32 rollouts; 0 new false positives from any check; P1 E alarm on time >= 0.95", "pass": passed}


def alarm_hypothesis(rollout):
    e, a = rollout["alarm"]["E"]["nets_pooled"], rollout["alarm"]["A"]["nets_pooled"]
    meets = lambda v: v["on_time_share"] is not None and v["on_time_share"] >= 0.9 and v["on_time_ci95"][0] >= 0.8 and v["premature_share"] <= 0.1
    return {"predictor": "+".join(ROLLED_NETS), "check": f"alarm E_{PRIMARY} >= {LEVEL} before D4 > {LEVEL}", **e,
            "reference_A": {**a, "meets_criterion": meets(a)},
            "lead_times": {k: {p: sorted(v) for p, v in rollout["lead_times"][k].items()} for k in ("E", "A")},
            "criterion": "on-time share >= 0.9, its CI95 low >= 0.8, premature share <= 0.1 (A is reported as the round-3 reference, not as a comparator)",
            "pass": meets(e)}


def control_flags(rows, rollout):
    out = []
    for r in rows:
        if r["predictor"] not in ("P0", "P0f32"):
            continue
        for check in r3.CONTROL_CHECKS:
            if r["flags"][check]:
                explained = check in EXPLAINED_BY and np.isfinite(r[EXPLAINED_BY[check]]) and r[EXPLAINED_BY[check]] < 0
                out.append({"predictor": r["predictor"], "split": r["split"], "seed": r["trajectory"], "step": r["step"], "check": check, "value": r[check],
                            "debugger_check": check in DEBUGGER_CHECKS, "explained_by": f"{EXPLAINED_BY[check]} < 0" if explained else None,
                            "new": check in DEBUGGER_CHECKS or not explained})
    for key in ("E", "A"):
        for p in ("P0", "P0f32"):
            for name, record in rollout["alarm"][key]["records"].get(p, {}).items():
                if record["alarm"] is not None:
                    out.append({"predictor": p, "split": ROLL, "seed": name, "step": record["alarm"], "check": f"{key}_alarm", "value": None,
                                "debugger_check": True, "explained_by": None, "new": True})
    return out


def flag_all(results, t1, t2, t3):
    for r in results.get("onestep", []) + results.get("rollout", []):
        r["flags"] = r3.flag(r, t1, t2, t3)


def summarize(results, t1, t2, t3, t4):
    flag_all(results, t1, t2, t3)
    groups = {}
    for r in results["onestep"] + results["rollout"]:
        groups.setdefault(f"{r['predictor']}/{r['split']}", []).append(r)
    summary = {g: r3.group_summary(rows) for g, rows in sorted(groups.items())}
    h, sweep_out = sanity(results, groups, summary, t1, t2, t3)
    rollout = rollout_summary(results["rollout"], t4["E_alarm"])
    controls = control_flags(results["onestep"] + results["rollout"], rollout)
    h["H17"] = tracking_hypothesis(rollout)
    h["H18"] = calibration_hypothesis(rollout)
    h["H19"] = control_hypothesis(rollout, controls)
    h["H20"] = alarm_hypothesis(rollout)
    ranking = {g: {s: spearman([r[s] for r in rows], [r["D4"] for r in rows])["rho"] for s in ("G", "G6", "Gp", "D3", "D3p", "D2", "D2p", "D2pp")}
               for g, rows in sorted(groups.items()) if g.startswith("P2") and not g.endswith(ROLL)}
    return {"thresholds": {"round1": t1, "round2": t2, "round3": t3, "round4": t4}, "primary": PRIMARY, "hypotheses": h, "groups": summary, "sweep": sweep_out,
            "rollout": rollout, "control_flags": controls, "exploratory": {"ranking_spearman_vs_D4": ranking}}


def evaluate(machine, data, preds, jobs):
    start = time.perf_counter()
    results = compute(data, preds, jobs)
    seconds = time.perf_counter() - start
    verdicts = summarize(results, *thresholds())
    verdicts["machine"], verdicts["seconds"], verdicts["jobs"] = machine, seconds, jobs
    out = R4 / "results" / machine
    for part, rows in results.items():
        write_json(out / f"{part}.json", rows)
    write_json(out / "verdicts.json", verdicts)
    write_json(out / "environment.json", environment())
    for name, v in verdicts["hypotheses"].items():
        print(f"{name}: {v['predictor']} {v['check']} {'PASS' if v['pass'] else 'FAIL'} {v.get('verdict', '')}", flush=True)


def load(machine):
    base = R4 / "results" / machine
    return {part: json.loads((base / f"{part}.json").read_text()) for part in ("onestep", "sweep", "rollout")}


def ledgers():
    results = R4 / "results"
    machines = sorted(p.name for p in results.iterdir() if (p / "verdicts.json").is_file())
    t1, t2, t3, t4 = thresholds()
    stats = r3.STATS + NEW_STATS + ("E0", "E1")
    false_positives, index, sweep_index, alarm_index = [], {}, {}, {}
    difference = {s: 0.0 for s in stats}
    for m in machines:
        loaded = load(m)
        verdicts = summarize(loaded, t1, t2, t3, t4)
        false_positives += [{"machine": m, **c, "status": "open"} for c in verdicts["control_flags"]]
        for r in loaded["onestep"] + loaded["rollout"]:
            index.setdefault((r["predictor"], r["split"], r["trajectory"], r["step"]), {})[m] = r
        for key in ("E", "A"):
            for p, records in verdicts["rollout"]["alarm"][key]["records"].items():
                for name, record in records.items():
                    alarm_index.setdefault((key, p, name), {})[m] = record
        for r in loaded["sweep"]:
            sweep_index.setdefault((r["split"], r["trajectory"], r["step"], r["family"], r["sign"], r["m"]), {})[m] = r
    discrepancies = []
    for key, rows in sorted(index.items()):
        if len(rows) < 2:
            continue
        for s in stats:
            values = [rows[m].get(s) for m in rows]
            if all(v is not None and np.isfinite(v) for v in values):
                difference[s] = max(difference[s], max(values) - min(values))
        for k in r3.KEYS:
            verdict = {m: rows[m]["flags"][k] for m in rows}
            if len(set(verdict.values())) > 1:
                discrepancies.append({"kind": "step", "predictor": key[0], "split": key[1], "seed": key[2], "step": key[3], "check": k, "verdict": verdict,
                                      "values": {m: {s: rows[m].get(s) for s in stats} for m in rows}})
    for key, rows in sorted(sweep_index.items(), key=lambda item: str(item[0])):
        if len(rows) < 2:
            continue
        for k in rows[next(iter(rows))]["flags"]:
            verdict = {m: rows[m]["flags"][k] for m in rows}
            if len(set(verdict.values())) > 1:
                discrepancies.append({"kind": "sweep", "split": key[0], "seed": key[1], "step": key[2], "family": key[3], "sign": key[4], "m": key[5], "check": k, "verdict": verdict})
    for key, rows in sorted(alarm_index.items()):
        if len(rows) > 1 and len({json.dumps(v, sort_keys=True) for v in rows.values()}) > 1:
            discrepancies.append({"kind": "rollout_alarm", "rule": key[0], "predictor": key[1], "seed": key[2], "verdict": rows})
    (R4 / "ledgers").mkdir(parents=True, exist_ok=True)
    for name, entries in (("false_positives", false_positives), ("discrepancies", discrepancies)):
        with (R4 / "ledgers" / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
    verdicts = {m: json.loads((results / m / "verdicts.json").read_text())["hypotheses"] for m in machines}
    checks = sorted({e["check"] for e in false_positives})
    write_json(results / "comparison.json", {
        "machines": machines, "max_abs_difference_between_machines": difference, "discrepancies": len(discrepancies),
        "false_positives_by_machine_check_split": {m: {c: {s: sum(e["machine"] == m and e["check"] == c and e["split"] == s for e in false_positives)
                                                            for s in sorted({e["split"] for e in false_positives if e["check"] == c})} for c in checks} for m in machines},
        "new_false_positives_by_machine": {m: sum(e["machine"] == m and e["new"] for e in false_positives) for m in machines},
        "hypotheses_by_machine": {m: {h: v.get("verdict", "PASS" if v["pass"] else "FAIL") for h, v in hs.items()} for m, hs in verdicts.items()}})
    print(f"machines {machines}: {len(discrepancies)} discrepancies, {len(false_positives)} control flags, "
          f"{sum(e['new'] for e in false_positives)} new", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine")
    parser.add_argument("--data", type=Path, default=R4 / "data")
    parser.add_argument("--preds", type=Path, default=R4 / "preds")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--ledgers", action="store_true")
    args = parser.parse_args()
    ledgers() if args.ledgers else evaluate(args.machine, args.data, args.preds, args.jobs)


if __name__ == "__main__":
    main()
