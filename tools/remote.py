import hashlib
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    command, args = sys.argv[1], sys.argv[2:]
    if command == "mkdirs":
        for name in args:
            (BASE / name).mkdir(parents=True, exist_ok=True)
    elif command == "hash":
        for name in args:
            path = BASE / name
            files = sorted(f for f in path.rglob("*") if f.is_file()) if path.is_dir() else [path] if path.is_file() else []
            for file in files:
                print(f"{sha256(file)}  {file.relative_to(BASE).as_posix()}")


if __name__ == "__main__":
    main()
