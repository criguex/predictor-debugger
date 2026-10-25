import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import round3.evaluate as r3
from pd import SPLITS, write_json
from round4 import LEVEL, R4, ROLLED, ROLLED_NETS
from round4.evaluate import SERIES, chunks, control_flags, flag_all, rollout_summary, rollout_task, run

OUT = R4 / "pilot"
SPLIT = "r3roll"
STEPS_SHOWN = (1, 5, 10, 20)


def summary():
    rows = json.loads((OUT / "pilot_rows.json").read_text())
    t1, t2, t3 = r3.thresholds()
    flag_all({"rollout": rows}, t1, t2, t3)
    rollout = rollout_summary(rows, LEVEL)
    out = {"tracking": {}, "calibration": {}, "alarm": {}, "lead_times": rollout["lead_times"], "by_step": rollout["by_step"]}
    for p in ROLLED_NETS:
        t = rollout["tracking"][p]
        out["tracking"][p] = {x: {"mean_rho": t[x]["mean_rho"], "ci95": t[x]["ci95"], "rho_at": {k: t[x]["per_step"][k - 1] for k in STEPS_SHOWN},
                                  "delta_vs_E": t[x].get("delta_vs_E")} for x in SERIES}
        out["calibration"][p] = {x: {"min": min(v), "max": max(v), "at": {k: v[k - 1] for k in STEPS_SHOWN}} for x, v in rollout["calibration"][p].items()}
    for key, a in rollout["alarm"].items():
        out["alarm"][key] = {p: v for p, v in a.items() if p != "records"}
    controls = control_flags(rows, rollout)
    out["control_flags"] = {"total": len(controls), "new": sum(c["new"] for c in controls), "by_check": {c: sum(e["check"] == c for e in controls) for c in sorted({e["check"] for e in controls})}}
    write_json(OUT / "pilot_summary.json", out)
    for p, t in out["tracking"].items():
        for x, v in t.items():
            delta = v["delta_vs_E"]
            print(f"{p:8} {x:6} mean={v['mean_rho']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] k=1,5,10,20: " + " ".join(f"{r:.3f}" for r in v["rho_at"].values())
                  + (f"  E-{x}={delta['delta']:+.3f} [{delta['ci95'][0]:+.3f}, {delta['ci95'][1]:+.3f}]" if delta else ""))
    for p, c in out["calibration"].items():
        print(p, {x: f"{v['min']:.3f}-{v['max']:.3f}" for x, v in c.items()})
    for key, a in out["alarm"].items():
        print(key, {p: (v["alarms"], v["crossing"], v["on_time_share"], round(v["premature_share"], 3)) for p, v in a.items() if p != "nets_pooled"}, a["nets_pooled"])
    print("control flags", out["control_flags"])
    for p in ROLLED:
        s = out["by_step"][p]
        print(p, "median by step k=1,5,10,20:", {key: [f"{s[k - 1].get(key, float('nan')):.3g}" for k in STEPS_SHOWN]
                                                for key in ("D4", "E_fp3", "Eor", "lam", "dhat_err_fp3", "dhat_err_r6", "dhat_err_r6u", "lin_err", "fp_change")})


def main():
    if "--summary" in sys.argv:
        return summary()
    jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 1
    start = time.perf_counter()
    plan = [("rollout", rollout_task, (R4 / "r1" / "round3" / "data", R4 / "r1" / "round3" / "preds", SPLIT, p, c)) for p in ROLLED for c in chunks(SPLITS[SPLIT][0])]
    results = run(plan, jobs)
    write_json(OUT / "pilot_rows.json", results["rollout"])
    print(f"pilot rollouts on {SPLIT}: {len(results['rollout'])} steps in {time.perf_counter() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
