from pd import DELTA, STEPS, np
from pd.checks import norm
from pd.initial import random_phases
from pd.predictors import identity
from round3.checks import curvature, energy_checks, energy_terms, momentum_checks

MAGNITUDES = tuple(float(f"{10 ** (-7 + j / 2):.1e}") for j in range(12))
MOMENTUM_MAGNITUDES = MAGNITUDES[:11]
SIGNS = (1, -1)


def direction(flow, name, step):
    rng = np.random.default_rng([31, identity(name), step])
    xi = flow.physical(flow.project(random_phases(flow, rng, 3, flow.k.shape)))
    return xi / norm(xi)


def energy_rows(flow, u0, u1):
    h0, h1 = flow.transform(u0), flow.transform(u1)
    t0, base = energy_terms(flow, h0), energy_terms(flow, h1)
    rows = [{"family": "energy", "sign": 0, "m": 0.0, **energy_checks(t0, base)}]
    for sign in SIGNS:
        for m in MAGNITUDES:
            alpha = np.sqrt(1 + sign * m * t0["E"] / base["E"])
            rows.append({"family": "energy", "sign": sign, "m": m, **energy_checks(t0, energy_terms(flow, alpha * h1))})
    return rows


def momentum_rows(flow, u0, u1, name, step):
    h0 = flow.transform(u0)
    t0 = energy_terms(flow, h0)
    q0 = curvature(flow, h0, t0["N"], t0["M"])
    xi = flow.transform(direction(flow, name, step) * norm(u1))
    rows = []
    for m in (0.0,) + MOMENTUM_MAGNITUDES:
        h1 = flow.transform(u1) + m * xi
        t1 = energy_terms(flow, h1)
        q1 = curvature(flow, h1, t1["N"], t1["M"])
        values = momentum_checks(flow, h0, h1, t0["N"], t0["M"], q0, t1["N"], t1["M"], q1)
        values["D3"] = norm((h1 - h0) / DELTA - 0.5 * (t0["N"] + t1["N"])) / norm(t0["N"])
        rows.append({"family": "momentum", "sign": 0, "m": m, **{k: float(v) for k, v in values.items()}})
    return rows


def sweep(flow, reference, name, momentum=True):
    out = []
    for step in range(STEPS):
        u0, u1 = reference[step], reference[step + 1]
        rows = energy_rows(flow, u0, u1) + (momentum_rows(flow, u0, u1, name, step) if momentum else [])
        out += [{"trajectory": name, "step": step, **{k: float(v) if isinstance(v, (float, np.floating)) else v for k, v in r.items()}} for r in rows]
    return out


def floor(rates, threshold=0.95):
    best = None
    for m in sorted(rates, reverse=True):
        if rates[m] >= threshold:
            best = m
        else:
            break
    return best
