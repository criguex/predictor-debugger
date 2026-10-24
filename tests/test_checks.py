import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import flow, np
from pd.checks import flags, statistics
from pd.data import advance
from pd.initial import energy, random_field
from pd.predictors import gradient_field

LOOSE = {"D1": 1e-10, "D2": 1e-2, "D3": 1e-1}


def main():
    solver = flow()
    u0 = random_field(solver, 12345, 3)
    assert abs(energy(u0) - 0.125) < 1e-14
    u1 = advance(solver, u0)
    exact = statistics(solver, u0, u1, u1)
    assert not flags(exact, LOOSE)["any"], exact
    assert exact["D1"] < 1e-14 and exact["D4"] == 0

    broken = u1 + gradient_field(solver, u1, "12345", 0)
    assert abs(np.linalg.norm(broken - u1) / np.linalg.norm(u1) - 0.05) < 1e-12
    assert flags(statistics(solver, u0, broken, u1), LOOSE)["D1"]

    scaled = statistics(solver, u0, 1.05 * u1, u1)
    assert scaled["D2"] > 10 * exact["D2"] and flags(scaled, LOOSE)["D2"]

    persistence = statistics(solver, u0, u0, u1)
    assert abs(persistence["D3"] - 1) < 1e-12 and flags(persistence, LOOSE)["D3"]

    nan = u1.copy()
    nan[0, 0, 0, 0] = np.nan
    nan_flags = flags(statistics(solver, u0, nan, u1), {"D1": np.inf, "D2": np.inf, "D3": np.inf})
    assert all(nan_flags.values()), nan_flags
    print("tests/test_checks.py: all checks passed")


if __name__ == "__main__":
    main()
