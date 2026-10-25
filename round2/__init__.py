from pd import ROOT, SPLITS
from pd.predictors import NATIVE_DTYPE

R2 = ROOT / "round2"
R1 = R2 / "r1"
NEW_SPLITS = {
    "r2test": ([str(s) for s in range(2000, 2040)], 3),
    "r2ood5": ([str(s) for s in range(2100, 2120)], 5),
    "r2ood6": ([str(s) for s in range(2200, 2220)], 6),
}
SPLITS.update(NEW_SPLITS)
ONE_STEP = ("P0", "P0f32", "P1", "P2s0", "P2s1", "P3a", "P3b")
GRADED_EPOCHS = (1, 2, 4, 8)
GRADED = tuple(f"P2ge{e}" for e in GRADED_EPOCHS) + ("P2gbest",)
NATIVE_DTYPE.update({label: "float32" for label in GRADED})
