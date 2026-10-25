from pd import DELTA, NU, np
from pd.checks import energy_enstrophy, norm
from round2.checks import enstrophy_rate, statistics2, tendency


def curvature(flow, spectral, n, m):
    return 0.5 * (flow.rhs(spectral + m, NU) - flow.rhs(spectral - m, NU)) + flow.rhs(n, NU) + flow.rhs(-n, NU)


def energy_terms(flow, spectral):
    e, z = energy_enstrophy(flow, spectral)
    n, m = tendency(flow, spectral)
    w, wn = flow.curl(spectral), flow.curl(n)
    rate = np.mean(np.sum(w * wn, axis=0))
    acceleration = np.mean(np.sum(wn * wn, axis=0)) + np.mean(np.sum(w * flow.curl(m), axis=0))
    return {"E": e, "Z": z, "Zdot": rate, "Zddot": acceleration, "N": n, "M": m}


def energy_checks(t0, t1):
    r2 = t1["E"] - t0["E"] + NU * DELTA * (t0["Z"] + t1["Z"])
    c4 = NU * DELTA ** 2 / 6 * (t0["Zdot"] - t1["Zdot"])
    r4 = r2 + c4
    r6 = r2 + NU * DELTA ** 2 / 5 * (t0["Zdot"] - t1["Zdot"]) + NU * DELTA ** 3 / 60 * (t0["Zddot"] + t1["Zddot"])
    e0 = t0["E"]
    return {"D2": abs(r2) / e0, "D2p": (abs(r4) - abs(c4)) / e0, "D2pp": (abs(r6) - abs(r6 - r4)) / e0,
            "D2h": abs(r4) / e0, "D2h6": abs(r6) / e0, "E0": e0, "E1": t1["E"]}


def momentum_checks(flow, h0, h1, n0, m0, q0, n1, m1, q1):
    residual = (h1 - h0) / DELTA - 0.5 * (n0 + n1)
    r4 = residual - DELTA / 12 * (m0 - m1)
    r6 = residual - DELTA / 10 * (m0 - m1) - DELTA ** 2 / 120 * (q0 + q1)
    scale = DELTA / norm(h1)
    return {"G": scale * norm(r4), "G6": scale * norm(r6), "Gp": scale * (norm(r6) - norm(r6 - r4))}


def statistics3(flow, u0, u1, reference):
    out = statistics2(flow, u0, u1, reference)
    u0, u1 = (np.asarray(a, dtype=np.float64) for a in (u0, u1))
    with np.errstate(all="ignore"):
        h0, h1 = flow.transform(u0), flow.transform(u1)
        t0, t1 = energy_terms(flow, h0), energy_terms(flow, h1)
        q0, q1 = curvature(flow, h0, t0["N"], t0["M"]), curvature(flow, h1, t1["N"], t1["M"])
        values = {**energy_checks(t0, t1), **momentum_checks(flow, h0, h1, t0["N"], t0["M"], q0, t1["N"], t1["M"], q1)}
    for key in ("D2pp", "D2h6", "G6", "Gp"):
        out[key] = float(values[key])
    out["G_r3"], out["D2p_r3"] = float(values["G"]), float(values["D2p"])
    return out
