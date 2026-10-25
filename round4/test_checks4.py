import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import flow, np
from pd.checks import norm
from pd.data import advance
from pd.initial import random_field
from round4.evaluate import transport_rows
from round4.transport import breeding_direction, defects, jvp, tl_advance


def main():
    solver = flow()
    u = advance(solver, random_field(solver, 65432, 3))
    v = breeding_direction(solver, "65432")
    w = breeding_direction(solver, "65433")
    base, (tl_v, tl_w, tl_mix) = tl_advance(solver, u, [v, w, 2 * v - 3 * w])
    assert np.array_equal(base, advance(solver, u))
    assert norm(tl_mix - (2 * tl_v - 3 * tl_w)) <= 1e-12 * norm(tl_mix)
    s = solver.project(solver.transform(u))
    assert norm(jvp(solver, s, 1e-9 * v) / 1e-9 - jvp(solver, s, v)) <= 1e-12 * norm(jvp(solver, s, v))

    direction = solver.physical(v) * norm(u) / norm(solver.physical(v))
    differences = {}
    for eps in (1e-3, 1e-4):
        fd = lambda e: (solver.transform(advance(solver, u + e * direction)) - solver.transform(advance(solver, u - e * direction))) / (2 * e)
        exact = tl_advance(solver, u, [solver.transform(direction)])[1][0]
        central, richardson = fd(eps), (4 * fd(eps) - fd(2 * eps)) / 3
        differences[eps] = (float(norm(central - exact) / norm(exact)), float(norm(richardson - exact) / norm(exact)))
    print("tangent-linear map vs finite differences of the solver step (relative):",
          {f"{e:.0e}": {"central": c, "richardson": r} for e, (c, r) in differences.items()})
    assert differences[1e-4][0] < 1e-9 and differences[1e-3][1] < 1e-11

    u0 = random_field(solver, 65434, 3)
    exact_step = advance(solver, u0)
    estimates, _ = defects(solver, u0, exact_step)
    assert norm(estimates["fp3"]) < 1e-6 * norm(solver.transform(exact_step))
    kick = solver.physical(breeding_direction(solver, "65435"))
    kick *= 0.01 * norm(exact_step) / norm(kick)
    estimates, change = defects(solver, u0, exact_step + kick)
    errors = {k: float(norm(e - solver.transform(kick)) / norm(solver.transform(kick))) for k, e in estimates.items()}
    print("defect reconstruction error for a 1 % solenoidal kick:", errors, "fixed-point change", change)
    assert errors["fp3"] < 0.05 and errors["fp3"] < errors["r6"]

    reference = [u0]
    for _ in range(5):
        reference.append(advance(solver, reference[-1]))
    reference = np.array(reference)
    states, state = [], u0
    for k in range(5):
        kick = solver.physical(breeding_direction(solver, str(65440 + k)))
        state = advance(solver, state) + 0.003 * norm(state) / norm(kick) * kick
        states.append(state)
    rows = transport_rows(solver, "synthetic", "test", "65440", reference, np.array(states))
    ratios = [(r["E_fp3"] / r["D4"], r["Eor"] / r["D4"]) for r in rows]
    print("synthetic rollout E/D4 and oracle/D4 per step:", [(round(a, 4), round(b, 4)) for a, b in ratios])
    assert all(abs(a - 1) < 0.05 and abs(b - 1) < 0.01 for a, b in ratios)
    print("round4/test_checks4.py: all checks passed")


if __name__ == "__main__":
    main()
