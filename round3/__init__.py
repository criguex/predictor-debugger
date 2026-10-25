from pd import ROOT, SPLITS
from pd.predictors import NATIVE_DTYPE
from round2 import GRADED

R3 = ROOT / "round3"
R1 = R3 / "r1"
R2 = R1 / "round2"
HORIZON = 20
ROLL = "r3roll"
NEW_SPLITS = {
    "r3test": ([str(s) for s in range(3000, 3040)], 3),
    "r3ood5": ([str(s) for s in range(3100, 3120)], 5),
    "r3ood6": ([str(s) for s in range(3200, 3220)], 6),
}
ROLL_SPLIT = {ROLL: ([str(s) for s in range(3300, 3340)], 3)}
SPLITS.update(NEW_SPLITS)
SPLITS.update(ROLL_SPLIT)
ONE_STEP = ("P0", "P0f32", "P1", "P2s0", "P2s1", "P3a", "P3b")
ROLLED_NETS = ("P2s0", "P2s1", "P2ge4", "P2gbest")
ROLLED = ("P0", "P0f32", "P1") + ROLLED_NETS
NATIVE_DTYPE.update({label: "float32" for label in GRADED})
