import argparse
import math
import time

import torch
from torch.nn import functional as F

from pd import SPLITS, environment, np, sha256, write_json
from pd.fno import FNO
from pd.train import BATCH, EPOCHS, LR, PATIENCE, mean_loss, pairs, predict
from round2 import GRADED_EPOCHS, NEW_SPLITS, R1, R2

GRADED_SEED = 2


def save_predictions(model, label, splits, device):
    for split in splits:
        (R2 / "preds" / label / split).mkdir(parents=True, exist_ok=True)
        for name in SPLITS[split][0]:
            reference = np.load(R2 / "data" / split / f"{name}.npy")
            np.save(R2 / "preds" / label / split / f"{name}.npy", predict(model, reference[:-1], device))


def checkpoints(device):
    for seed in (0, 1):
        model = FNO().to(device)
        model.load_state_dict(torch.load(R1 / "checkpoints" / f"P2s{seed}.pt", map_location=device))
        save_predictions(model, f"P2s{seed}", NEW_SPLITS, device)
        print(f"P2s{seed} predicted", flush=True)


def graded(device):
    torch.manual_seed(GRADED_SEED)
    generator = torch.Generator().manual_seed(GRADED_SEED)
    model = FNO().to(device)
    train_x, train_y = (t.to(device) for t in pairs(R1 / "data", "train"))
    val_x, val_y = (t.to(device) for t in pairs(R1 / "data", "val"))
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    best, best_epoch, best_state, history, saved = math.inf, 0, None, [], {}
    start = time.perf_counter()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total = 0.0
        for batch in torch.randperm(len(train_x), generator=generator).split(BATCH):
            batch = batch.to(device)
            loss = F.mse_loss(model(train_x[batch]), train_y[batch])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item() * len(batch)
        val = mean_loss(model, val_x, val_y)
        history.append({"epoch": epoch, "train_mse": total / len(train_x), "val_mse": val, "seconds": time.perf_counter() - start})
        print(f"seed={GRADED_SEED} epoch={epoch} train_mse={total / len(train_x):.6e} val_mse={val:.6e}", flush=True)
        if epoch in GRADED_EPOCHS:
            saved[f"P2ge{epoch}"] = {k: v.detach().clone() for k, v in model.state_dict().items()}
        if val < best:
            best, best_epoch = val, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= PATIENCE:
            break
    saved["P2gbest"] = best_state
    report = {"seed": GRADED_SEED, "best_epoch": best_epoch, "best_val_mse": best, "epochs_run": len(history), "history": history, "checkpoints": {}}
    (R2 / "checkpoints").mkdir(parents=True, exist_ok=True)
    for label, state in saved.items():
        path = R2 / "checkpoints" / f"{label}.pt"
        torch.save(state, path)
        model.load_state_dict(state)
        save_predictions(model, label, ("r2test",), device)
        report["checkpoints"][label] = sha256(path)
        print(f"{label} predicted", flush=True)
    report["environment"] = environment(device)
    write_json(R2 / "logs" / "war" / "graded_training.json", report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("checkpoints", "graded"))
    args = parser.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.benchmark = False
    checkpoints(device) if args.mode == "checkpoints" else graded(device)


if __name__ == "__main__":
    main()
