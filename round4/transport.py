from pd import DELTA, DT, NU, SUBSTEPS, np
from pd.checks import norm
from pd.initial import random_phases
from pd.predictors import identity
from round2.checks import tendency
from round3.checks import curvature

FIXED_POINT = 3


def jvp(flow, s, v):
    size = norm(v)
    if size == 0:
        return np.zeros_like(v)
    a = norm(s) / size
    return 0.5 * (flow.rhs(s + a * v, NU) - flow.rhs(s - a * v, NU)) / a


def tl_step(flow, s, tangents):
    k1 = flow.rhs(s, NU)
    d1 = [jvp(flow, s, t) for t in tangents]
    a2 = s + 0.5 * DT * k1
    k2 = flow.rhs(a2, NU)
    d2 = [jvp(flow, a2, t + 0.5 * DT * x) for t, x in zip(tangents, d1)]
    a3 = s + 0.5 * DT * k2
    k3 = flow.rhs(a3, NU)
    d3 = [jvp(flow, a3, t + 0.5 * DT * x) for t, x in zip(tangents, d2)]
    a4 = s + DT * k3
    k4 = flow.rhs(a4, NU)
    d4 = [jvp(flow, a4, t + DT * x) for t, x in zip(tangents, d3)]
    out = flow.project(s + DT * (k1 + 2 * k2 + 2 * k3 + k4) / 6)
    return out, [flow.project(t + DT * (a + 2 * b + 2 * c + d) / 6) for t, a, b, c, d in zip(tangents, d1, d2, d3, d4)]


def tl_advance(flow, u, tangents):
    s = flow.project(flow.transform(np.asarray(u, dtype=np.float64)))
    tangents = [flow.project(t) for t in tangents]
    for _ in range(SUBSTEPS):
        s, tangents = tl_step(flow, s, tangents)
    return flow.physical(s), tangents


def residuals(flow, h0, h1):
    n0, m0 = tendency(flow, h0)
    n1, m1 = tendency(flow, h1)
    q0, q1 = curvature(flow, h0, n0, m0), curvature(flow, h1, n1, m1)
    residual = (h1 - h0) / DELTA - 0.5 * (n0 + n1)
    return {"r4": residual - DELTA / 12 * (m0 - m1), "r6": residual - DELTA / 10 * (m0 - m1) - DELTA ** 2 / 120 * (q0 + q1)}


def defects(flow, u0, u1):
    h0, h1 = flow.transform(np.asarray(u0, dtype=np.float64)), flow.transform(np.asarray(u1, dtype=np.float64))
    projected = residuals(flow, flow.project(h0), h1)
    literal = residuals(flow, h0, h1)
    out = {"r6": DELTA * projected["r6"], "r4": DELTA * projected["r4"], "r6u": DELTA * literal["r6"]}
    previous = delta = out["r6"]
    for _ in range(FIXED_POINT):
        previous, delta = delta, out["r6"] + 0.5 * DELTA * jvp(flow, h1, delta)
    out["fp3"] = delta
    return out, float(norm(delta - previous) / norm(delta))


def breeding_direction(flow, name):
    rng = np.random.default_rng([41, identity(name)])
    b = flow.project(random_phases(flow, rng, 3, flow.k.shape))
    b = flow.transform(flow.physical(b))
    return b / norm(b)
