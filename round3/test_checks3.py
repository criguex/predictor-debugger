import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import NU, flow, np
from pd.data import advance
from pd.initial import random_field
from pd.predictors import gradient_field
from round2.checks import tendency
from round3.checks import curvature, energy_checks, energy_terms, statistics3


def main():
    solver = flow()
    for k0 in (3, 6):
        u0 = random_field(solver, 54321 + k0, k0)
        u1 = advance(solver, u0)
        h0 = solver.project(solver.transform(u0))
        n, m = tendency(solver, h0)
        q = curvature(solver, h0, n, m)
        s = 1e-4
        numeric = (tendency(solver, h0 + s * n)[1] - tendency(solver, h0 - s * n)[1]) / (2 * s)
        assert np.max(np.abs(numeric - q)) < 1e-6 * np.max(np.abs(q))

        exact = statistics3(solver, u0, u1, u1)
        assert abs(exact["G_r3"] - exact["G"]) <= 1e-12 * exact["G"]
        assert abs(exact["D2p_r3"] - exact["D2p"]) <= 1e-12 * abs(exact["D2p"])
        assert exact["G6"] < exact["G"] / 20 and exact["Gp"] < 0
        assert exact["D2h6"] < exact["D2h"] / 5 and exact["D2pp"] < 0

        t0, t1 = energy_terms(solver, solver.transform(u0)), energy_terms(solver, solver.transform(u1))
        scaled = energy_checks(t0, energy_terms(solver, solver.transform(1.001 * u1)))
        assert scaled["D2pp"] > 1e-3 and scaled["D2pp"] > scaled["D2p"]
        assert abs(energy_checks(t0, t1)["D2"] - exact["D2"]) <= 1e-12 * exact["D2"]

        broken = statistics3(solver, u0, u1 + gradient_field(solver, u1, "12345", 0), u1)
        assert broken["Gp"] > 0.04 and broken["G6"] > 0.04
        persistence = statistics3(solver, u0, u0, u1)
        assert abs(persistence["Gp"] / persistence["D4"] - 1) < 0.2
    print("round3/test_checks3.py: all checks passed")


if __name__ == "__main__":
    main()
