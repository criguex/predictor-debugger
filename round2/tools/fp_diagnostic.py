import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pd import DT, NU, SUBSTEPS, flow, np, write_json
from pd.checks import energy_enstrophy, norm
from round2 import R2
from round2.checks import enstrophy_rate, tendency


def composite(solver, u0, m):
    h = DT * SUBSTEPS / m
    s = solver.project(solver.transform(u0))
    e0, z = energy_enstrophy(solver, s)
    n, d = tendency(solver, s)
    y0 = enstrophy_rate(solver, s, n)
    start, quad, integral = s, 0.0, 0.0
    for _ in range(m):
        t = s
        for _ in range(SUBSTEPS // m):
            t = solver.step(t, NU, DT)
        e1, z1 = energy_enstrophy(solver, t)
        n1, d1 = tendency(solver, t)
        integral += NU * h * (z + z1)
        quad = quad + h / 2 * (n + n1) + h * h / 12 * (d - d1)
        s, z, n, d = t, z1, n1, d1
    y1 = enstrophy_rate(solver, s, n)
    trapezoid = e1 - e0 + integral
    return {"D2": abs(trapezoid) / e0, "D2h": abs(trapezoid + NU * h * h / 6 * (y0 - y1)) / e0, "G": norm(s - start - quad) / norm(s)}


def main():
    solver = flow()
    stats = json.loads((R2 / "results" / "mac" / "stats.json").read_text())
    rows = []
    for r in stats:
        if r["predictor"] == "P0" and (r["flags"]["D2"] or r["flags"]["G"]):
            u0 = np.load(R2 / "data" / r["split"] / f"{r['trajectory']}.npy")[r["step"]]
            rows.append({"split": r["split"], "seed": r["trajectory"], "step": r["step"], "flags": {k: r["flags"][k] for k in ("D2", "D2p", "G")},
                         "recorded": {k: r[k] for k in ("D2", "D2h", "D2p", "G")}, "by_h": {f"h={0.1 / m:.3f}": composite(solver, u0, m) for m in (1, 2, 5)}})
    ratios = {k: [row["by_h"]["h=0.100"][k] / row["by_h"]["h=0.050"][k] for row in rows] for k in ("D2", "D2h", "G")}
    write_json(R2 / "results" / "fp_diagnostic.json", {
        "purpose": "exact-solver steps flagged by the old D2 or by G, recomputed with finer quadrature sub-intervals; a residual falling about 4x (trapezoid) or 16x (Hermite) per halving of h is quadrature error of the statistic, not an error of the predictor",
        "steps": len(rows),
        "halving_ratio_h0.1_over_h0.05": {k: {"min": min(v), "max": max(v)} for k, v in ratios.items()},
        "rows": rows,
    })
    print(json.dumps({"steps": len(rows), "ratios": {k: [min(v), max(v)] for k, v in ratios.items()}}))


if __name__ == "__main__":
    main()
