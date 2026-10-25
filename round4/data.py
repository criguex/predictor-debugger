import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import SPLITS, environment, flow, np, write_json
from pd.data import generate
from round3.data import long_trajectory
from round4 import NEW_SPLITS, R4, ROLL


def generate4(out):
    generate(out, NEW_SPLITS)
    solver = flow()
    names, k0 = SPLITS[ROLL]
    (out / ROLL).mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    for name in names:
        states = long_trajectory(solver, name, k0)
        if not np.all(np.isfinite(states)):
            raise FloatingPointError(f"non-finite reference: {ROLL}/{name}")
        np.save(out / ROLL / f"{name}.npy", states)
    print(f"{ROLL}: {len(names)} trajectories of {len(states) - 1} steps in {time.perf_counter() - start:.1f} s", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=R4 / "data")
    parser.add_argument("--environment", type=Path)
    args = parser.parse_args()
    if args.environment:
        write_json(args.environment, environment())
    generate4(args.out)


if __name__ == "__main__":
    main()
