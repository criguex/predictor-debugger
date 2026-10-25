from pd import DELTA, NU, np
from pd.checks import energy_enstrophy, norm, statistics

CHECKS2 = ("D1", "D2", "D3", "D2p")


def tendency(flow, spectral):
    n = flow.rhs(spectral, NU)
    return n, 0.5 * (flow.rhs(spectral + n, NU) - flow.rhs(spectral - n, NU))


def enstrophy_rate(flow, spectral, n):
    return np.mean(np.sum(flow.curl(spectral) * flow.curl(n), axis=0))


def statistics2(flow, u0, u1, reference):
    out = statistics(flow, u0, u1, reference)
    u0, u1, reference = (np.asarray(a, dtype=np.float64) for a in (u0, u1, reference))
    with np.errstate(all="ignore"):
        h0, h1, href = flow.transform(u0), flow.transform(u1), flow.transform(reference)
        e0, z0 = energy_enstrophy(flow, h0)
        e1, z1 = energy_enstrophy(flow, h1)
        n0, m0 = tendency(flow, h0)
        n1, m1 = tendency(flow, h1)
        trapezoid = e1 - e0 + NU * DELTA * (z0 + z1)
        correction = NU * DELTA ** 2 / 6 * (enstrophy_rate(flow, h0, n0) - enstrophy_rate(flow, h1, n1))
        residual = (h1 - h0) / DELTA - 0.5 * (n0 + n1)
        hermite = residual - DELTA / 12 * (m0 - m1)
        solenoidal = flow.project(hermite)
        error = h1 - href
        values = {
            "D2h": abs(trapezoid + correction) / e0,
            "D2p": (abs(trapezoid + correction) - abs(correction)) / e0,
            "G": DELTA * norm(hermite) / norm(h1),
            "Gs": DELTA * norm(solenoidal) / norm(h1),
            "Gc": DELTA * norm(hermite - solenoidal) / norm(h1),
            "D3p": norm(flow.project(residual)) / norm(n0),
            "D4s": norm(flow.project(error)) / norm(href),
            "D4c": norm(error - flow.project(error)) / norm(href),
        }
    out.update({key: float(value) for key, value in values.items()})
    return out
