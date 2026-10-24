import argparse
import math
import time
from pathlib import Path

import torch
from torch.nn import functional as F

from pd import ROOT, SPLITS, STEPS, environment, np, sha256, write_json
from pd.fno import FNO, HIDDEN, LAYERS, MODES, WIDTH
from pd.predictors import EVALUATED_SPLITS

LR, BATCH, EPOCHS, PATIENCE = 1e-3, 8, 100, 10


def pairs(data, split):
    arrays = [np.load(data / split / f"{name}.npy") for name in SPLITS[split][0]]
    inputs = np.concatenate([a[:-1] for a in arrays]).astype(np.float32)
    targets = np.concatenate([a[1:] for a in arrays]).astype(np.float32)
    return torch.from_numpy(inputs), torch.from_numpy(targets)


@torch.no_grad()
def mean_loss(model, inputs, targets):
    model.eval()
    total = sum(F.mse_loss(model(inputs[i:i + BATCH]), targets[i:i + BATCH], reduction="sum").item() for i in range(0, len(inputs), BATCH))
    return total / targets.numel()


def train(seed, data, device):
    torch.manual_seed(seed)
    generator = torch.Generator().manual_seed(seed)
    model = FNO().to(device)
    train_x, train_y = (t.to(device) for t in pairs(data, "train"))
    val_x, val_y = (t.to(device) for t in pairs(data, "val"))
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    best, best_epoch, best_state, history = math.inf, 0, None, []
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
        print(f"seed={seed} epoch={epoch} train_mse={total / len(train_x):.6e} val_mse={val:.6e} t={time.perf_counter() - start:.1f}s", flush=True)
        if val < best:
            best, best_epoch = val, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= PATIENCE:
            break
    model.load_state_dict(best_state)
    return model, {"best_epoch": best_epoch, "best_val_mse": best, "epochs_run": len(history), "seconds": time.perf_counter() - start, "history": history}


@torch.no_grad()
def predict(model, states, device):
    model.eval()
    return model(torch.from_numpy(states.astype(np.float32)).to(device)).double().cpu().numpy()


@torch.no_grad()
def rollout(model, initial, device):
    model.eval()
    state = torch.from_numpy(initial[None].astype(np.float32)).to(device)
    states = []
    for _ in range(STEPS):
        state = model(state)
        states.append(state[0].double().cpu().numpy())
    return np.array(states)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--preds", type=Path, default=ROOT / "preds")
    parser.add_argument("--checkpoints", type=Path, default=ROOT / "checkpoints")
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.backends.cudnn.benchmark = False
    model, report = train(args.seed, args.data, device)
    label = f"P2s{args.seed}"
    args.checkpoints.mkdir(parents=True, exist_ok=True)
    checkpoint = args.checkpoints / f"{label}.pt"
    torch.save(model.state_dict(), checkpoint)
    start = time.perf_counter()
    for split in EVALUATED_SPLITS:
        (args.preds / label / split).mkdir(parents=True, exist_ok=True)
        for name in SPLITS[split][0]:
            reference = np.load(args.data / split / f"{name}.npy")
            np.save(args.preds / label / split / f"{name}.npy", predict(model, reference[:-1], device))
    (args.preds / label / "rollout").mkdir(parents=True, exist_ok=True)
    for name in SPLITS["test"][0]:
        reference = np.load(args.data / "test" / f"{name}.npy")
        np.save(args.preds / label / "rollout" / f"{name}.npy", rollout(model, reference[0], device))
    report.update({
        "seed": args.seed, "device": device, "dtype": "float32",
        "architecture": {"width": WIDTH, "modes": MODES, "layers": LAYERS, "head_hidden": HIDDEN, "activation": "GELU", "grid_coordinates": False},
        "optimizer": {"name": "Adam", "lr": LR, "batch": BATCH, "max_epochs": EPOCHS, "patience": PATIENCE, "loss": "MSE on u(t+0.1)"},
        "parameters": sum(p.numel() for p in model.parameters()),
        "checkpoint_sha256": sha256(checkpoint),
        "prediction_seconds": time.perf_counter() - start,
        "environment": environment(device),
    })
    write_json(args.log, report)


if __name__ == "__main__":
    main()
