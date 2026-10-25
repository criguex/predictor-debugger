from pd import ROOT, SPLITS
from round3 import HORIZON, ONE_STEP, ROLLED, ROLLED_NETS

R4 = ROOT / "round4"
R1 = R4 / "r1"
R2 = R1 / "round2"
R3 = R1 / "round3"
ROLL = "r4roll"
NEW_SPLITS = {
    "r4test": ([str(s) for s in range(4000, 4040)], 3),
    "r4ood5": ([str(s) for s in range(4100, 4120)], 5),
    "r4ood6": ([str(s) for s in range(4200, 4220)], 6),
}
ROLL_SPLIT = {ROLL: ([str(s) for s in range(4300, 4340)], 3)}
SPLITS.update(NEW_SPLITS)
SPLITS.update(ROLL_SPLIT)
LEVEL = 0.05
