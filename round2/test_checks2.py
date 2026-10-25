import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import flow, np
from pd.data import advance
from pd.initial import random_field
from pd.predictors import gradient_field
from round2.checks import statistics2, tendency


def main():
    solver = flow()
    u0 = random_field(solver, 12345, 3)
    u1 = advance(solver, u0)
    h0 = solver.project(solver.transform(u0))
    n, m = tendency(solver, h0)
    s = 1e-4
    numeric = (solver.rhs(h0 + s * n, 0.05) - solver.rhs(h0 - s * n, 0.05)) / (2 * s)
    assert np.max(np.abs(numeric - m)) < 1e-9 * np.max(np.abs(m))

    exact = statistics2(solver, u0, u1, u1)
    assert exact["D2h"] < exact["D2"] / 50 and exact["D2p"] < 0
    assert exact["G"] < exact["D3"] / 50 and exact["D4"] == 0
    assert abs(exact["G"] ** 2 - exact["Gs"] ** 2 - exact["Gc"] ** 2) < 1e-12 * exact["G"] ** 2

    scaled = statistics2(solver, u0, 1.05 * u1, u1)
    assert scaled["D2p"] > 1e-2 and abs(scaled["G"] - scaled["D4"] / 1.05) < 0.1 * scaled["G"]

    broken = statistics2(solver, u0, u1 + gradient_field(solver, u1, "12345", 0), u1)
    assert abs(broken["Gc"] / broken["G"] - 1) < 1e-3 and abs(broken["D4c"] - 0.05) < 1e-12

    persistence = statistics2(solver, u0, u0, u1)
    assert abs(persistence["G"] / persistence["D4"] - 1) < 0.1
    print("round2/test_checks2.py: all checks passed")


if __name__ == "__main__":
    main()
