import datetime
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLVER = ROOT / "vendor" / "fluid_solver.py"
SOLVER_SHA256 = "87d3372edf646da285731f5144551c2a626987f3718c6985b47a6c816f3bdc50"

N, NU, DT, SUBSTEPS, STEPS = 32, 0.05, 0.01, 10, 10
DELTA = DT * SUBSTEPS
ENERGY = 0.125
SPLITS = {
    "train": ([f"{s:03d}" for s in range(0, 160)], 3),
    "val": ([f"{s:03d}" for s in range(160, 180)], 3),
    "test": ([f"{s:03d}" for s in range(180, 220)], 3),
    "ood": ([f"{s:03d}" for s in range(300, 320)] + ["tg"], 5),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_solver():
    digest = sha256(SOLVER)
    if digest != SOLVER_SHA256:
        raise SystemExit(f"vendor/fluid_solver.py SHA-256 mismatch: {digest}")
    spec = importlib.util.spec_from_file_location("fluid_solver", SOLVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fluid_solver = load_solver()
np = fluid_solver.np


def flow():
    return fluid_solver.SpectralFlow(N)


def cpu_name():
    if sys.platform == "darwin":
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    return platform.processor()


def environment(device="CPU"):
    info = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version,
        "numpy": np.__version__,
        "os": platform.platform(),
        "machine": platform.machine(),
        "processor": cpu_name(),
        "hostname": platform.node(),
        "device": device,
        "solver_sha256": SOLVER_SHA256,
        "numpy_finfo": {
            name: {"eps": float(np.finfo(name).eps), "tiny": float(np.finfo(name).tiny), "max": float(np.finfo(name).max)}
            for name in ("float32", "float64")
        },
    }
    try:
        import torch
        info["torch"] = torch.__version__
        info["torch_finfo"] = {
            str(dtype): {"eps": torch.finfo(dtype).eps, "tiny": torch.finfo(dtype).tiny}
            for dtype in (torch.float32, torch.float64)
        }
        if torch.cuda.is_available():
            info["cuda_device"] = torch.cuda.get_device_name(0)
            info["cuda"] = torch.version.cuda
    except ImportError:
        info["torch"] = None
    return info


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
