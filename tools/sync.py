import argparse
import datetime
import subprocess
import sys
from pathlib import Path

from remote import BASE, sha256

REMOTE = "C:/ADN/pd-exp"
PYTHON = r"C:\ADN\voz\venv\Scripts\python.exe"
LOG = BASE / "logs" / "transfers.tsv"
ATTEMPTS = 5


def ssh(host, *args):
    result = subprocess.run(["ssh", host, *args], capture_output=True, text=True)
    return result.stdout.replace("\0", "")


def remote_hashes(host, names):
    out = ssh(host, PYTHON, REMOTE.replace("/", "\\") + "\\tools\\remote.py", "hash", *names)
    return {line.split("  ", 1)[1].strip(): line.split("  ", 1)[0] for line in out.splitlines() if "  " in line}


def local_files(names):
    files = []
    for name in names:
        path = BASE / name
        files += sorted(f for f in path.rglob("*") if f.is_file() and "__pycache__" not in f.parts) if path.is_dir() else [path]
    return [f.relative_to(BASE).as_posix() for f in files]


def log(rows):
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as handle:
        if new:
            handle.write("utc\tsource\tdestination\tfile\tbytes\tsource_sha256\tdestination_sha256\tattempts\tok\n")
        for row in rows:
            handle.write("\t".join(str(v) for v in row) + "\n")


def groups(files):
    out = {}
    for file in files:
        out.setdefault(str(Path(file).parent.as_posix()), []).append(file)
    return out


def transfer(host, direction, names):
    if direction == "push":
        files = local_files(names)
        source = {f: sha256(BASE / f) for f in files}
        ssh(host, PYTHON, REMOTE.replace("/", "\\") + "\\tools\\remote.py", "mkdirs", *sorted(groups(files)))
    else:
        source = remote_hashes(host, names)
        files = sorted(source)
        for parent in groups(files):
            (BASE / parent).mkdir(parents=True, exist_ok=True)
    pending, attempts, destination = list(files), {f: 0 for f in files}, {}
    for _ in range(ATTEMPTS):
        if not pending:
            break
        for parent, batch in groups(pending).items():
            for start in range(0, len(batch), 40):
                chunk = batch[start:start + 40]
                for f in chunk:
                    attempts[f] += 1
                if direction == "push":
                    command = ["scp", "-C", "-q", *[str(BASE / f) for f in chunk], f"{host}:{REMOTE}/{parent}/"]
                else:
                    command = ["scp", "-C", "-q", *[f"{host}:{REMOTE}/{f}" for f in chunk], str(BASE / parent) + "/"]
                subprocess.run(command, capture_output=True)
        if direction == "push":
            destination.update(remote_hashes(host, sorted(groups(pending))))
        else:
            destination.update({f: sha256(BASE / f) for f in pending if (BASE / f).is_file()})
        pending = [f for f in pending if destination.get(f) != source[f]]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    src, dst = ("mac", host) if direction == "push" else (host, "mac")
    log([(now, src, dst, f, (BASE / f).stat().st_size if (BASE / f).is_file() else "", source[f], destination.get(f, ""), attempts[f], destination.get(f) == source[f]) for f in files])
    failed = [f for f in files if destination.get(f) != source[f]]
    print(f"{direction} {host}: {len(files) - len(failed)}/{len(files)} files verified, {sum(attempts.values()) - len(files)} retries")
    for f in failed:
        print(f"FAILED {f}")
    return not failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("direction", choices=("push", "pull"))
    parser.add_argument("host")
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()
    sys.exit(0 if transfer(args.host, args.direction, args.names) else 1)


if __name__ == "__main__":
    main()
