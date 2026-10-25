import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pd import SPLITS, STEPS, environment, flow, np, write_json
from pd.checks import norm
from pd.data import advance
from pd.evaluate import HYPOTHESES, spearman
from pd.predictors import gradient_field, one_step
from round2.evaluate import BOOTSTRAP, BOOTSTRAP_SEED, cluster_bootstrap
from round2.evaluate import flag as flag2
from round3 import HORIZON, NEW_SPLITS, ONE_STEP, R1, R2, R3, ROLL, ROLLED, ROLLED_NETS
from round3.checks import statistics3
from round3.sweep import MAGNITUDES, MOMENTUM_MAGNITUDES, SIGNS, floor, sweep

KEYS = ("D1", "D2", "D3", "any", "D2p", "D2p_mag", "G", "any2", "D2pp", "D2pp_mag", "G6", "Gp", "any3")
STATS = ("D1", "D2", "D2h", "D2p", "D2pp", "D2h6", "D3", "D3p", "G", "G6", "Gp", "Gs", "Gc", "D4", "D4s", "D4c", "edge")
CONTROL_CHECKS = ("D1", "D2", "D3", "D2p", "D2pp", "G", "G6", "Gp")
DEBUGGER3 = ("D1", "D3", "D2pp", "Gp")
LEVEL = 0.05
EARLY = LEVEL / 2
ENERGY_CHECKS = ("D2", "D2_mag", "D2p", "D2p_mag", "D2pp", "D2pp_mag")
MOMENTUM_CHECKS = ("D3", "G", "G6", "Gp")
SWEEP_SPLITS = tuple(NEW_SPLITS)


def edge_fraction(solver, u):
    h = solver.transform(np.asarray(u, dtype=np.float64))
    power = np.sum(np.abs(h) ** 2, axis=0)
    edge = np.any(np.abs(solver.k) >= 0.8 * solver.n / 3, axis=0) & solver.mask
    return float(np.sum(power[edge]) / np.sum(power))


def predicted(predictor, reference, split, name, preds):
    if predictor in ("P3a", "P3b"):
        solver = flow()
        p2 = np.load(preds / "P2s0" / split / f"{name}.npy")
        if predictor == "P3b":
            return 1.05 * p2
        return np.array([u + gradient_field(solver, u, name, step) for step, u in enumerate(p2)])
    return one_step(predictor, reference, split, name, preds)


def onestep_task(args):
    data, preds, split, predictors = args
    solver, out = flow(), []
    for name in SPLITS[split][0]:
        reference = np.load(data / split / f"{name}.npy")
        for predictor in predictors:
            states = predicted(predictor, reference, split, name, preds)
            for step in range(STEPS):
                stats = statistics3(solver, reference[step], states[step], reference[step + 1])
                out.append({"predictor": predictor, "split": split, "trajectory": name, "step": step, **stats,
                            "edge": edge_fraction(solver, states[step])})
    return out


def rolled_states(solver, predictor, reference, name, preds):
    if predictor == "P0":
        return reference[1:]
    if predictor == "P1":
        return np.array([reference[0]] * HORIZON)
    if predictor == "P0f32":
        states, state = [], reference[0]
        for _ in range(HORIZON):
            state = advance(solver, state).astype(np.float32).astype(np.float64)
            states.append(state)
        return np.array(states)
    return np.load(preds / predictor / ROLL / f"{name}.npy")


def rollout_task(args):
    data, preds, predictor = args
    solver, out = flow(), []
    for name in SPLITS[ROLL][0]:
        reference = np.load(data / ROLL / f"{name}.npy")
        states = rolled_states(solver, predictor, reference, name, preds)
        previous = reference[0]
        for step in range(HORIZON):
            row = {"predictor": predictor, "split": ROLL, "trajectory": name, "step": step,
                   **statistics3(solver, previous, states[step], reference[step + 1]), "edge": edge_fraction(solver, states[step])}
            if predictor in ROLLED_NETS + ("P0f32",):
                exact = advance(solver, previous)
                row["D4loc"] = float(norm(states[step] - exact) / norm(exact))
            out.append(row)
            previous = states[step]
    return out


def sweep_task(args):
    data, split = args
    solver, out = flow(), []
    for name in SPLITS[split][0]:
        out += [{"split": split, **r} for r in sweep(solver, np.load(data / split / f"{name}.npy"), name)]
    return out


def tasks(data, preds):
    out = [("onestep", onestep_task, (R1 / "data", preds, "val", ("P0", "P0f32")))]
    out += [("onestep", onestep_task, (data, preds, split, ONE_STEP)) for split in NEW_SPLITS]
    out += [("rollout", rollout_task, (data, preds, p)) for p in ROLLED]
    return out + [("sweep", sweep_task, (data, split)) for split in SWEEP_SPLITS]


def compute(data, preds, jobs=1):
    plan = tasks(data, preds)
    results = {"onestep": [], "rollout": [], "sweep": []}
    start = time.perf_counter()
    if jobs == 1:
        outputs = map(lambda t: t[1](t[2]), plan)
        for (part, _, args), rows in zip(plan, outputs):
            results[part] += rows
            print(f"{part} {args[2] if part != 'sweep' else args[1]} done {time.perf_counter() - start:.0f}s", flush=True)
    else:
        with ProcessPoolExecutor(jobs) as pool:
            futures = [pool.submit(t[1], t[2]) for t in plan]
            for (part, _, args), future in zip(plan, futures):
                results[part] += future.result()
                print(f"{part} {args[2] if part != 'sweep' else args[1]} done {time.perf_counter() - start:.0f}s", flush=True)
    return results


def thresholds():
    t1 = json.loads((R1 / "thresholds.json").read_text())["thresholds"]
    t2 = json.loads((R2 / "thresholds.json").read_text())["thresholds"]
    t3 = json.loads((R3 / "thresholds.json").read_text())["thresholds"]
    return t1, t2, t3


def exceeds(value, tau):
    return not np.isfinite(value) or value > tau


def flag(r, t1, t2, t3):
    out = flag2(r, t1, t2)
    energy = not np.isfinite(r["E0"]) or not np.isfinite(r["E1"]) or r["E1"] > r["E0"]
    out["D2pp_mag"] = exceeds(r["D2pp"], t3["D2pp"])
    out["D2pp"] = out["D2pp_mag"] or energy
    out["G6"] = exceeds(r["G6"], t3["G6"])
    out["Gp"] = exceeds(r["Gp"], t3["Gp"])
    out["any3"] = any(out[k] for k in DEBUGGER3)
    return out


def sweep_flags(r, t1, t2, t3):
    if r["family"] == "momentum":
        out = {"G": exceeds(r["G"], t2["G"]), "G6": exceeds(r["G6"], t3["G6"]), "Gp": exceeds(r["Gp"], t3["Gp"])}
        if "D3" in r:
            out["D3"] = exceeds(r["D3"], t1["D3"])
        return out
    energy = not np.isfinite(r["E0"]) or not np.isfinite(r["E1"]) or r["E1"] > r["E0"]
    out = {"D2_mag": exceeds(r["D2"], t1["D2"]), "D2p_mag": exceeds(r["D2p"], t2["D2p"]), "D2pp_mag": exceeds(r["D2pp"], t3["D2pp"])}
    for k in ("D2", "D2p", "D2pp"):
        out[k] = out[f"{k}_mag"] or energy
    return out


def finite(values):
    return [v for v in values if v is not None and np.isfinite(v)]


def group_summary(group):
    out = {"steps": len(group), "flagged": {k: sum(r["flags"][k] for r in group) for k in KEYS}}
    for s in STATS + ("D4loc",):
        values = finite([r.get(s) for r in group])
        if values:
            out[s] = {"min": min(values), "median": float(np.median(values)), "max": max(values), "non_finite": len(group) - len(values)}
    return out


def rate_hypothesis(summary, predictor, split, key, op, bound):
    g = summary[f"{predictor}/{split}"]
    share = g["flagged"][key] / g["steps"]
    return {"predictor": predictor, "check": key, "split": split, "flagged": g["flagged"][key], "steps": g["steps"], "share": share,
            "criterion": f"share {op} {bound}", "pass": share <= bound if op == "<=" else share >= bound}


def zero_hypothesis(summary, key, splits):
    groups = {f"{p}/{s}": summary[f"{p}/{s}"]["flagged"][key] for p in ("P0", "P0f32") for s in splits}
    return {"predictor": "P0, P0f32", "check": key, "flagged": sum(groups.values()), "steps": sum(summary[g]["steps"] for g in groups),
            "by_group": groups, "criterion": "0 flagged in every group", "pass": sum(groups.values()) == 0}


def ranking_hypothesis(groups, labels, gauge, comparator):
    target = {label: cluster_bootstrap(groups[f"{label}/r3test"], gauge) for label in labels}
    against = {label: cluster_bootstrap(groups[f"{label}/r3test"], comparator) for label in labels}
    meets = lambda v: v["rho"] >= 0.8 and v["ci95"][0] >= 0.6
    passed = all(meets(v) for v in target.values())
    comparator_passes = all(meets(v) for v in against.values())
    return {"predictor": ", ".join(labels), "check": f"Spearman({gauge}, D4)", "by_group": target,
            "comparator": {"check": f"Spearman({comparator}, D4)", "by_group": against, "meets_criterion": comparator_passes},
            "criterion": "rho >= 0.8 and CI95 low >= 0.6 for each; comparator must fail", "pass": passed,
            "verdict": "FAIL" if not passed else "NON-DISCRIMINATIVE" if comparator_passes else "PASS"}


def sweep_summary(rows, t1, t2, t3, splits=SWEEP_SPLITS):
    for r in rows:
        r["flags"] = sweep_flags(r, t1, t2, t3)
    cells = {}
    for r in rows:
        cells.setdefault((r["split"], r["family"], r["sign"], r["m"]), []).append(r)
    rates, floors = {}, {}
    for split in splits:
        for family, signs, checks, grid in (("energy", SIGNS, ENERGY_CHECKS, MAGNITUDES), ("momentum", (0,), MOMENTUM_CHECKS, MOMENTUM_MAGNITUDES)):
            base = cells[(split, family, 0, 0.0)]
            for sign in signs:
                for check in [c for c in checks if c in base[0]["flags"]]:
                    by_m = {m: sum(r["flags"][check] for r in cells[(split, family, sign, m)]) / len(cells[(split, family, sign, m)]) for m in grid}
                    key = f"{split}/{family}/{'+' if sign > 0 else '-' if sign < 0 else '0'}/{check}"
                    rates[key] = {"baseline_m0": sum(r["flags"][check] for r in base) / len(base), "steps": len(base), "by_m": {f"{m:.1e}": v for m, v in by_m.items()}}
                    found = floor(by_m)
                    floors[key] = {"floor": found, "index": grid.index(found) if found is not None else len(grid)}
    return rates, floors


def floor_hypothesis(floors):
    by_cell, ok = {}, True
    for split in SWEEP_SPLITS:
        for sign in ("+", "-"):
            new, old = floors[f"{split}/energy/{sign}/D2pp_mag"], floors[f"{split}/energy/{sign}/D2p_mag"]
            passed = new["index"] <= old["index"] - 2
            by_cell[f"{split}/{sign}"] = {"D2pp_mag_floor": new["floor"], "D2p_mag_floor": old["floor"], "pass": passed}
            ok = ok and passed
    return {"predictor": "P0 + graded energy error", "check": "floor(D2pp_mag) vs floor(D2p_mag)", "by_group": by_cell,
            "criterion": "D2pp floor at least one decade (2 grid points) below D2p floor, every split and sign", "pass": ok}


def rollout_arrays(rows):
    horizon = 1 + max(r["step"] for r in rows)
    by = {}
    for r in rows:
        by.setdefault(r["predictor"], {}).setdefault(r["trajectory"], [None] * horizon)[r["step"]] = r
    return by


def within_step(series, x, y, names):
    values = []
    for k in range(len(series[names[0]][x])):
        rho = spearman([series[n][x][k] for n in names], [series[n][y][k] for n in names])["rho"]
        values.append(rho if rho is not None and np.isfinite(rho) else np.nan)
    return float(np.nanmean(values)), values


def bootstrap_within(series, x, y="D4"):
    names = sorted(series)
    point, per_step = within_step(series, x, y, names)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    values = [within_step(series, x, y, [names[i] for i in rng.integers(0, len(names), len(names))])[0] for _ in range(BOOTSTRAP)]
    low, high = np.nanpercentile(values, [2.5, 97.5])
    return {"mean_rho": point, "per_step": per_step, "ci95": [float(low), float(high)], "replicates": BOOTSTRAP, "seed": BOOTSTRAP_SEED,
            "non_finite_replicates": int(np.sum(np.isnan(values)))}


def series_of(steps):
    g = np.array([r["G"] for r in steps])
    d3 = np.array([r["D3"] for r in steps])
    out = {"G": g.tolist(), "D4": [r["D4"] for r in steps], "A": np.cumsum(g).tolist(), "A_rss": np.sqrt(np.cumsum(g ** 2)).tolist(),
           "C": np.cumsum(d3).tolist(), "Ap": np.cumsum([r["Gp"] for r in steps]).tolist(), "k": list(range(1, len(steps) + 1))}
    return out


def first(values, test):
    return next((k + 1 for k, v in enumerate(values) if test(v)), None)


def alarm_record(s, alarm):
    crossing = first(s["D4"], lambda v: not np.isfinite(v) or v > LEVEL)
    raised = first(alarm, bool)
    premature = raised is not None and s["D4"][raised - 1] < EARLY
    return {"crossing": crossing, "alarm": raised, "on_time": crossing is not None and raised is not None and raised <= crossing, "premature": premature}


def alarm_rates(records):
    crossing = [r for r in records if r["crossing"] is not None]
    raised = [r for r in records if r["alarm"] is not None]
    on_time = sum(r["on_time"] for r in crossing) / len(crossing) if crossing else None
    premature = sum(r["premature"] for r in raised) / len(raised) if raised else 0.0
    return {"rollouts": len(records), "crossing": len(crossing), "alarms": len(raised), "on_time_share": on_time, "premature_share": premature}


def bootstrap_alarm(by_name):
    names = sorted(by_name)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    on_time, premature = [], []
    for _ in range(BOOTSTRAP):
        sample = [r for i in rng.integers(0, len(names), len(names)) for r in by_name[names[i]]]
        rates = alarm_rates(sample)
        on_time.append(np.nan if rates["on_time_share"] is None else rates["on_time_share"])
        premature.append(rates["premature_share"])
    return {"on_time_ci95": [float(v) for v in np.nanpercentile(on_time, [2.5, 97.5])], "premature_ci95": [float(v) for v in np.nanpercentile(premature, [2.5, 97.5])]}


def rollout_summary(rows, nets=ROLLED_NETS):
    by = rollout_arrays(rows)
    out = {"tracking": {}, "alarm": {}, "by_step": {}, "pooled": {}}
    alarms = {"A": {}, "any2": {}, "any3": {}}
    for predictor, trajectories in sorted(by.items()):
        series = {n: series_of(steps) for n, steps in trajectories.items()}
        out["by_step"][predictor] = [{"step": k + 1, **{s: float(np.median(finite([trajectories[n][k].get(s) for n in trajectories]))) for s in ("D4", "D4loc", "G", "Gp", "D3", "D1") if finite([trajectories[n][k].get(s) for n in trajectories])},
                                      "A_median": float(np.median([series[n]["A"][k] for n in series])),
                                      "flagged": {key: sum(trajectories[n][k]["flags"][key] for n in trajectories) for key in ("D1", "D3", "D2pp", "Gp", "any2", "any3")}}
                                     for k in range(len(next(iter(trajectories.values()))))]
        flat = [r for steps in trajectories.values() for r in steps]
        out["pooled"][predictor] = {"rho_A_D4": spearman([v for s in series.values() for v in s["A"]], [v for s in series.values() for v in s["D4"]])["rho"],
                                    "rho_step_D4": spearman([v for s in series.values() for v in s["k"]], [v for s in series.values() for v in s["D4"]])["rho"],
                                    "rho_C_D4": spearman([v for s in series.values() for v in s["C"]], [v for s in series.values() for v in s["D4"]])["rho"]}
        if "D4loc" in flat[0]:
            out["pooled"][predictor]["rho_G_D4loc"] = spearman([r["G"] for r in flat], [r["D4loc"] for r in flat])["rho"]
            out["pooled"][predictor]["median_G_over_D4loc"] = float(np.median([r["G"] / r["D4loc"] for r in flat]))
        if predictor in nets:
            out["tracking"][predictor] = {x: bootstrap_within(series, x) for x in ("A", "C", "A_rss", "Ap", "G")}
        for name, s in series.items():
            steps = trajectories[name]
            alarms["A"].setdefault(predictor, {})[name] = alarm_record(s, [a >= LEVEL or not np.isfinite(a) for a in s["A"]])
            alarms["any2"].setdefault(predictor, {})[name] = alarm_record(s, [r["flags"]["any2"] for r in steps])
            alarms["any3"].setdefault(predictor, {})[name] = alarm_record(s, [r["flags"]["any3"] for r in steps])
    for rule, by_predictor in alarms.items():
        out["alarm"][rule] = {p: alarm_rates(list(v.values())) for p, v in sorted(by_predictor.items())}
        pooled = {}
        for p in nets:
            for name, record in by_predictor[p].items():
                pooled.setdefault(name, []).append(record)
        out["alarm"][rule]["nets_pooled"] = {**alarm_rates([r for v in pooled.values() for r in v]), **bootstrap_alarm(pooled)}
        out["alarm"][rule]["records"] = {p: v for p, v in sorted(by_predictor.items())}
    return out


def tracking_hypothesis(rollout):
    by, ok, comparator_ok = {}, True, True
    for p in ROLLED_NETS:
        t = rollout["tracking"][p]
        meets = lambda v: v["mean_rho"] >= 0.7 and v["ci95"][0] >= 0.5
        by[p] = {"A": {k: t["A"][k] for k in ("mean_rho", "ci95")}, "C": {k: t["C"][k] for k in ("mean_rho", "ci95")}, "pass": meets(t["A"]), "comparator_meets": meets(t["C"])}
        ok, comparator_ok = ok and meets(t["A"]), comparator_ok and meets(t["C"])
    return {"predictor": ", ".join(ROLLED_NETS), "check": "mean over steps of within-step Spearman(A_k, D4_k)", "by_group": by,
            "comparator": {"check": "cumulative D3, C_k", "meets_criterion": comparator_ok},
            "criterion": "mean rho >= 0.7 and CI95 low >= 0.5 for each net; comparator must fail", "pass": ok,
            "verdict": "FAIL" if not ok else "NON-DISCRIMINATIVE" if comparator_ok else "PASS"}


def alarm_hypothesis(rollout):
    a, c = rollout["alarm"]["A"]["nets_pooled"], rollout["alarm"]["any2"]["nets_pooled"]
    meets = lambda v: v["on_time_share"] is not None and v["on_time_share"] >= 0.9 and v["on_time_ci95"][0] >= 0.8 and v["premature_share"] <= 0.1
    return {"predictor": "+".join(ROLLED_NETS), "check": f"alarm A_k >= {LEVEL} before D4 > {LEVEL}", **{k: a[k] for k in a},
            "comparator": {"check": "round-2 debugger any2 at the first flagged step", **{k: c[k] for k in c}, "meets_criterion": meets(c)},
            "criterion": "on-time share >= 0.9, its CI95 low >= 0.8, premature share <= 0.1; comparator must fail", "pass": meets(a),
            "verdict": "FAIL" if not meets(a) else "NON-DISCRIMINATIVE" if meets(c) else "PASS"}


def control_rollout_hypothesis(rollout, rollout_groups):
    alarms = {p: rollout["alarm"]["A"][p]["alarms"] for p in ("P0", "P0f32")}
    gp = {p: rollout_groups[f"{p}/{ROLL}"]["flagged"]["Gp"] for p in ("P0", "P0f32")}
    p1 = rollout["alarm"]["A"]["P1"]
    passed = sum(alarms.values()) == 0 and sum(gp.values()) == 0 and p1["on_time_share"] is not None and p1["on_time_share"] >= 0.95
    return {"predictor": "P0, P0f32, P1 rollouts", "check": "A alarm and Gp", "alarms": alarms, "Gp_flags": gp, "P1": p1,
            "criterion": "0 A alarms and 0 Gp flags on P0/P0f32 rollouts; P1 on time >= 0.95", "pass": passed}


def summarize(results, t1, t2, t3):
    for r in results["onestep"] + results["rollout"]:
        r["flags"] = flag(r, t1, t2, t3)
    groups = {}
    for r in results["onestep"] + results["rollout"]:
        groups.setdefault(f"{r['predictor']}/{r['split']}", []).append(r)
    summary = {g: group_summary(rows) for g, rows in sorted(groups.items())}
    h = {name: rate_hypothesis(summary, p, "r3test", key, op, bound) for name, (p, key, op, bound) in HYPOTHESES.items()}
    h["H5"] = zero_hypothesis(summary, "D2p", NEW_SPLITS)
    h["H6"] = rate_hypothesis(summary, "P3b", "r3test", "D2p_mag", ">=", 0.95)
    h["H7"] = ranking_hypothesis(groups, ("P2s0", "P2s1"), "G", "D3")
    h["H9"] = zero_hypothesis(summary, "D2pp", NEW_SPLITS)
    rates, floors = sweep_summary(results["sweep"], t1, t2, t3)
    h["H10"] = floor_hypothesis(floors)
    h["H10b"] = rate_hypothesis(summary, "P3b", "r3test", "D2pp_mag", ">=", 0.95)
    h["H11"] = zero_hypothesis(summary, "Gp", NEW_SPLITS)
    cells = {f"{p}/{s}": rate_hypothesis(summary, p, s, "Gp", ">=", 0.95) for p in ("P1", "P3a", "P3b") for s in NEW_SPLITS}
    h["H12"] = {"predictor": "P1, P3a, P3b", "check": "Gp", "flagged": sum(v["flagged"] for v in cells.values()), "steps": sum(v["steps"] for v in cells.values()),
                "by_group": {k: v["flagged"] for k, v in cells.items()}, "criterion": "share >= 0.95 in every group", "pass": all(v["pass"] for v in cells.values())}
    h["H13"] = ranking_hypothesis(groups, ("P2s0", "P2s1"), "Gp", "D3")
    rollout = rollout_summary(results["rollout"])
    h["H14"] = tracking_hypothesis(rollout)
    h["H15"] = alarm_hypothesis(rollout)
    h["H16"] = control_rollout_hypothesis(rollout, summary)
    controls = [r for r in groups.get("P0/r3test", []) + groups.get("P0/r3ood5", []) + groups.get("P0/r3ood6", [])]
    diagnosis = {
        "rho_G_truncation_P0": spearman([r["G"] for r in controls], [r["G6"] - r["Gp"] for r in controls])["rho"],
        "median_G_over_truncation_P0": float(np.median([r["G"] / (r["G6"] - r["Gp"]) for r in controls])),
        "rho_G_edge_P0": spearman([r["G"] for r in controls], [r["edge"] for r in controls])["rho"],
        "rho_G_step_P0": spearman([r["G"] for r in controls], [r["step"] for r in controls])["rho"],
        "median_G_by_split_step_P0": {s: [float(np.median([r["G"] for r in groups[f"P0/{s}"] if r["step"] == k])) for k in range(STEPS)] for s in ("val",) + tuple(NEW_SPLITS)},
        "median_edge_by_split_step_P0": {s: [float(np.median([r["edge"] for r in groups[f"P0/{s}"] if r["step"] == k])) for k in range(STEPS)] for s in ("val",) + tuple(NEW_SPLITS)},
    }
    ranking = {g: {s: spearman([r[s] for r in rows], [r["D4"] for r in rows])["rho"] for s in ("G", "G6", "Gp", "D3", "D3p", "D2", "D2p", "D2pp")}
               for g, rows in sorted(groups.items()) if g.startswith("P2") and not g.endswith(ROLL)}
    control_flags = {g: {k: summary[g]["flagged"][k] for k in CONTROL_CHECKS} for g in summary if g.split("/")[0] in ("P0", "P0f32")}
    return {"thresholds": {"round1": t1, "round2": t2, "round3": t3}, "hypotheses": h, "groups": summary,
            "sweep": {"rates": rates, "floors": floors}, "rollout": rollout,
            "exploratory": {"g_diagnosis": diagnosis, "ranking_spearman_vs_D4": ranking, "control_flags": control_flags}}


def evaluate(machine, data, preds, jobs):
    start = time.perf_counter()
    results = compute(data, preds, jobs)
    seconds = time.perf_counter() - start
    verdicts = summarize(results, *thresholds())
    verdicts["machine"], verdicts["seconds"], verdicts["jobs"] = machine, seconds, jobs
    out = R3 / "results" / machine
    for part, rows in results.items():
        write_json(out / f"{part}.json", rows)
    write_json(out / "verdicts.json", verdicts)
    write_json(out / "environment.json", environment())
    for name, v in verdicts["hypotheses"].items():
        print(f"{name}: {v['predictor']} {v['check']} {'PASS' if v['pass'] else 'FAIL'} {v.get('verdict', '')}", flush=True)


def load(machine):
    base = R3 / "results" / machine
    return {part: json.loads((base / f"{part}.json").read_text()) for part in ("onestep", "rollout", "sweep")}


def ledgers():
    results = R3 / "results"
    machines = sorted(p.name for p in results.iterdir() if (p / "verdicts.json").is_file())
    t1, t2, t3 = thresholds()
    limits = {**t1, **t2, **t3}
    false_positives, index, sweep_index, alarm_index = [], {}, {}, {}
    for m in machines:
        loaded = load(m)
        verdicts = summarize(loaded, t1, t2, t3)
        for r in loaded["onestep"] + loaded["rollout"]:
            index.setdefault((r["predictor"], r["split"], r["trajectory"], r["step"]), {})[m] = r
            if r["predictor"] in ("P0", "P0f32"):
                for check in CONTROL_CHECKS:
                    if r["flags"][check]:
                        false_positives.append({"machine": m, "predictor": r["predictor"], "split": r["split"], "seed": r["trajectory"], "step": r["step"],
                                                "check": check, "value": r[check], "threshold": limits[check], "E0": r["E0"], "E1": r["E1"],
                                                "debugger_check": check in DEBUGGER3, "status": "open", "explanation": None})
        for p in ("P0", "P0f32"):
            for name, record in verdicts["rollout"]["alarm"]["A"]["records"][p].items():
                alarm_index.setdefault((p, name), {})[m] = record
                if record["alarm"] is not None:
                    false_positives.append({"machine": m, "predictor": p, "split": ROLL, "seed": name, "step": record["alarm"], "check": "A_alarm",
                                            "value": None, "threshold": LEVEL, "debugger_check": True, "status": "open", "explanation": None})
        for p in ROLLED_NETS + ("P1",):
            for name, record in verdicts["rollout"]["alarm"]["A"]["records"][p].items():
                alarm_index.setdefault((p, name), {})[m] = record
        for r in loaded["sweep"]:
            sweep_index.setdefault((r["split"], r["trajectory"], r["step"], r["family"], r["sign"], r["m"]), {})[m] = r
    stats = STATS + ("D4loc", "E0", "E1")
    discrepancies, difference = [], {s: 0.0 for s in stats}
    for key, rows in sorted(index.items()):
        if len(rows) < 2:
            continue
        for s in stats:
            values = [rows[m].get(s) for m in rows]
            if all(v is not None and np.isfinite(v) for v in values):
                difference[s] = max(difference[s], max(values) - min(values))
        for k in KEYS:
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
                discrepancies.append({"kind": "sweep", "split": key[0], "seed": key[1], "step": key[2], "family": key[3], "sign": key[4], "m": key[5], "check": k,
                                      "verdict": verdict, "values": {m: {s: rows[m].get(s) for s in ("D2", "D2p", "D2pp", "G", "G6", "Gp", "D3", "E0", "E1")} for m in rows}})
    for key, rows in sorted(alarm_index.items()):
        if len(rows) > 1 and len({json.dumps(v, sort_keys=True) for v in rows.values()}) > 1:
            discrepancies.append({"kind": "rollout_alarm", "predictor": key[0], "seed": key[1], "verdict": rows})
    (R3 / "ledgers").mkdir(parents=True, exist_ok=True)
    for name, entries in (("false_positives", false_positives), ("discrepancies", discrepancies)):
        with (R3 / "ledgers" / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
    hypotheses = {m: {h: v.get("verdict", "PASS" if v["pass"] else "FAIL") for h, v in json.loads((results / m / "verdicts.json").read_text())["hypotheses"].items()} for m in machines}
    write_json(results / "comparison.json", {"machines": machines, "max_abs_difference_between_machines": difference, "discrepancies": len(discrepancies),
                                             "false_positives_by_machine_check": {m: {c: sum(e["check"] == c and e["machine"] == m for e in false_positives) for c in CONTROL_CHECKS + ("A_alarm",)} for m in machines},
                                             "hypotheses_by_machine": hypotheses})
    print(f"machines {machines}: {len(discrepancies)} discrepancies, {len(false_positives)} control flags", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine")
    parser.add_argument("--data", type=Path, default=R3 / "data")
    parser.add_argument("--preds", type=Path, default=R3 / "preds")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--ledgers", action="store_true")
    args = parser.parse_args()
    ledgers() if args.ledgers else evaluate(args.machine, args.data, args.preds, args.jobs)


if __name__ == "__main__":
    main()
