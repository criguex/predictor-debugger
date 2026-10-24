import argparse
import time
from pathlib import Path

from pd import DT, NU, ROOT, SPLITS, STEPS, SUBSTEPS, environment, flow, np, write_json
from pd.initial import initial_state


def advance(flow, velocity):
    spectral = flow.project(flow.transform(velocity))
    for _ in range(SUBSTEPS):
        spectral = flow.step(spectral, NU, DT)
    return flow.physical(spectral)


def trajectory(flow, velocity):
    states = [velocity]
    for _ in range(STEPS):
        states.append(advance(flow, states[-1]))
    return np.array(states, dtype=np.float64)


def generate(out, splits):
    solver = flow()
    for split in splits:
        names, k0 = SPLITS[split]
        (out / split).mkdir(parents=True, exist_ok=True)
        start = time.perf_counter()
        for name in names:
            states = trajectory(solver, initial_state(solver, name, k0))
            if not np.all(np.isfinite(states)):
                raise FloatingPointError(f"non-finite reference: {split}/{name}")
            np.save(out / split / f"{name}.npy", states)
        print(f"{split}: {len(names)} trajectories in {time.perf_counter() - start:.1f} s", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "data")
    parser.add_argument("--splits", nargs="+", default=list(SPLITS))
    parser.add_argument("--environment", type=Path)
    args = parser.parse_args()
    if args.environment:
        write_json(args.environment, environment())
    generate(args.out, args.splits)


if __name__ == "__main__":
    main()
