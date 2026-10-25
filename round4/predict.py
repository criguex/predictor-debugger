import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch

from pd import SPLITS, environment, np, sha256, write_json
from pd.fno import FNO
from pd.train import predict
from round3.predict import rollout
from round4 import NEW_SPLITS, R1, R2, R4, ROLL

CHECKPOINTS = {"P2s0": R1 / "checkpoints" / "P2s0.pt", "P2s1": R1 / "checkpoints" / "P2s1.pt",
               "P2ge4": R2 / "checkpoints" / "P2ge4.pt", "P2gbest": R2 / "checkpoints" / "P2gbest.pt"}
ONE_STEP_NETS = ("P2s0", "P2s1")


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.benchmark = False
    report = {"checkpoints": {}, "seconds": {}}
    for label, file in CHECKPOINTS.items():
        start = time.perf_counter()
        model = FNO().to(device)
        model.load_state_dict(torch.load(file, map_location=device))
        report["checkpoints"][label] = sha256(file)
        splits = tuple(NEW_SPLITS) if label in ONE_STEP_NETS else ()
        for split in splits:
            (R4 / "preds" / label / split).mkdir(parents=True, exist_ok=True)
            for name in SPLITS[split][0]:
                reference = np.load(R4 / "data" / split / f"{name}.npy")
                np.save(R4 / "preds" / label / split / f"{name}.npy", predict(model, reference[:-1], device))
        (R4 / "preds" / label / ROLL).mkdir(parents=True, exist_ok=True)
        for name in SPLITS[ROLL][0]:
            reference = np.load(R4 / "data" / ROLL / f"{name}.npy")
            np.save(R4 / "preds" / label / ROLL / f"{name}.npy", rollout(model, reference[0], device))
        report["seconds"][label] = time.perf_counter() - start
        print(f"{label} predicted ({', '.join(splits + (ROLL,))}) in {report['seconds'][label]:.1f} s", flush=True)
    report["environment"] = environment(device)
    write_json(R4 / "logs" / "war" / "predict.json", report)


if __name__ == "__main__":
    main()
