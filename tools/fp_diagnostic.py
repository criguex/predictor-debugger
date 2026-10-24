import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import DT, NU, ROOT, SUBSTEPS, flow, np, write_json
from pd.checks import energy_enstrophy


def budget(solver, u0, substeps_per_interval):
    spectral = solver.project(solver.transform(u0))
    e0, z = energy_enstrophy(solver, spectral)
    integral = 0.0
    for _ in range(SUBSTEPS // substeps_per_interval):
        for _ in range(substeps_per_interval):
            spectral = solver.step(spectral, NU, DT)
        e1, z1 = energy_enstrophy(solver, spectral)
        integral += NU * DT * substeps_per_interval * (z + z1)
        z = z1
    return abs(e1 - e0 + integral) / e0


def main():
    solver = flow()
    stats = json.loads((ROOT / "results" / "mac" / "stats.json").read_text())
    rows = []
    for r in stats:
        if r["predictor"] == "P0" and r["flags"]["any"]:
            u0 = np.load(ROOT / "data" / r["split"] / f"{r['trajectory']}.npy")[r["step"]]
            values = {f"h={DT * m:.2f}": budget(solver, u0, m) for m in (10, 5, 2, 1)}
            rows.append({"split": r["split"], "seed": r["trajectory"], "step": r["step"], "D2_recorded": r["D2"], "trapezoid_residual": values})
            print(rows[-1], flush=True)
    write_json(ROOT / "results" / "fp_diagnostic.json", {
        "purpose": "energy-budget residual of the exact solver with finer trapezoid sub-intervals; a residual falling about 4x per halving of h is quadrature error of the D2 statistic, not an error of the predictor",
        "rows": rows,
    })


if __name__ == "__main__":
    main()
