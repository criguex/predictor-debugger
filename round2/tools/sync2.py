import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import sync

sync.REMOTE = "C:/ADN/pd-exp-r2"
sync.LOG = sync.BASE / "round2" / "logs" / "transfers.tsv"

if __name__ == "__main__":
    sync.main()
