from pd import DELTA, NU, np

CHECKS = ("D1", "D2", "D3")


def norm(values):
    return np.sqrt(np.sum(np.abs(values) ** 2))


def energy_enstrophy(flow, spectral):
    velocity = flow.physical(spectral)
    omega = flow.curl(spectral)
    return 0.5 * np.mean(np.sum(velocity * velocity, axis=0)), 0.5 * np.mean(np.sum(omega * omega, axis=0))


def statistics(flow, u0, u1, reference):
    u0, u1, reference = (np.asarray(a, dtype=np.float64) for a in (u0, u1, reference))
    with np.errstate(all="ignore"):
        h0, h1 = flow.transform(u0), flow.transform(u1)
        e0, z0 = energy_enstrophy(flow, h0)
        e1, z1 = energy_enstrophy(flow, h1)
        n0, n1 = flow.rhs(h0, NU), flow.rhs(h1, NU)
        values = {
            "D1": norm(np.sum(flow.k * h1, axis=0)) / np.sqrt(np.sum(flow.k2 * np.abs(h1) ** 2)),
            "D2": abs(e1 - e0 + NU * DELTA * (z0 + z1)) / e0,
            "E0": e0,
            "E1": e1,
            "D3": norm((h1 - h0) / DELTA - 0.5 * (n0 + n1)) / norm(n0),
            "D4": norm(u1 - reference) / norm(reference),
        }
    return {key: float(value) for key, value in values.items()}


def flags(stats, thresholds):
    finite = {key: bool(np.isfinite(stats[key])) for key in CHECKS + ("E0", "E1")}
    out = {check: not finite[check] or stats[check] > thresholds[check] for check in CHECKS}
    out["D2"] = out["D2"] or not finite["E0"] or not finite["E1"] or stats["E1"] > stats["E0"]
    out["any"] = any(out[check] for check in CHECKS)
    return out
