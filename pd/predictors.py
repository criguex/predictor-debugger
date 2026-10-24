import argparse
from pathlib import Path

from pd import ROOT, SPLITS, flow, np
from pd.checks import norm
from pd.initial import random_phases

ONE_STEP = ("P0", "P0f32", "P1", "P2s0", "P2s1", "P3a", "P3b")
NATIVE_DTYPE = {"P0": "float64", "P1": "float64", "P0f32": "float32", "P2s0": "float32", "P2s1": "float32", "P3a": "float32", "P3b": "float32"}
SAVED = ("P2s0", "P2s1", "P3a", "P3b")
EVALUATED_SPLITS = ("val", "test", "ood")


def identity(name):
    return 1000 if name == "tg" else int(name)


def gradient_field(flow, velocity, name, step):
    rng = np.random.default_rng([7, identity(name), step])
    phi = random_phases(flow, rng, 3, flow.k2.shape) * flow.mask
    gradient = flow.physical(1j * flow.k * phi)
    return gradient * (0.05 * norm(velocity) / norm(gradient))


def one_step(predictor, reference, split, name, preds):
    inputs, targets = reference[:-1], reference[1:]
    if predictor == "P0":
        return targets
    if predictor == "P0f32":
        return targets.astype(np.float32).astype(np.float64)
    if predictor == "P1":
        return inputs
    return np.load(preds / predictor / split / f"{name}.npy")


def build_p3(preds):
    solver = flow()
    for split in EVALUATED_SPLITS:
        for name in SPLITS[split][0]:
            p2 = np.load(preds / "P2s0" / split / f"{name}.npy")
            p3a = np.array([u + gradient_field(solver, u, name, step) for step, u in enumerate(p2)])
            for label, values in (("P3a", p3a), ("P3b", 1.05 * p2)):
                (preds / label / split).mkdir(parents=True, exist_ok=True)
                np.save(preds / label / split / f"{name}.npy", values.astype(np.float64))
        print(f"P3a/P3b built for {split}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preds", type=Path, default=ROOT / "preds")
    build_p3(parser.parse_args().preds)


if __name__ == "__main__":
    main()
