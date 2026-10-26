import argparse
import hashlib
import http.client
import posixpath
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "criguex/predictor-debugger"
ROUNDS = {"r1": "", "r2": "round2/", "r3": "round3/", "r4": "round4/"}
KINDS = ("data", "preds", "checkpoints")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def manifest(root, round_name):
    entries = {}
    for line in (root / ROUNDS[round_name] / "MANIFEST.sha256").read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        entries[path.strip()] = digest
    return entries


def folders(entries, prefix, kinds):
    found = set()
    for path in entries:
        if not path.startswith(prefix):
            continue
        parts = path[len(prefix):].split("/")
        if len(parts) >= 2 and parts[0] in kinds:
            found.add(prefix + parts[0] + "/" + parts[1])
    return sorted(found)


def tar_name(folder):
    return folder.replace("/", "--").removesuffix(".pt") + ".tar"


def parse_sums(text):
    sums = {}
    for line in text.splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            sums[name.strip().lstrip("*")] = digest.lower()
    return sums


def download(url, dest, attempts=5):
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, attempts + 1):
        done = part.stat().st_size if part.exists() else 0
        request = urllib.request.Request(url, headers={"Range": f"bytes={done}-"} if done else {})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                with open(part, "ab" if done and response.getcode() == 206 else "wb") as out:
                    shutil.copyfileobj(response, out, 1 << 20)
            part.replace(dest)
            return
        except urllib.error.HTTPError as error:
            if error.code == 416 and done:
                part.replace(dest)
                return
            if error.code < 500 and error.code != 429:
                raise RuntimeError(f"{url}: HTTP {error.code}") from error
            reason = f"HTTP {error.code}"
        except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
            reason = str(error)
        print(f"  intento {attempt}/{attempts} falló ({reason}); reanudo", flush=True)
        time.sleep(min(60, 5 * attempt))
    raise RuntimeError(f"{url}: no se pudo descargar tras {attempts} intentos")


def safe_members(tar, folder):
    members = []
    for member in tar.getmembers():
        name = member.name
        if name.startswith("/") or "\\" in name or ":" in name:
            raise ValueError(f"ruta absoluta o no POSIX en el tar: {name}")
        if ".." in name.split("/"):
            raise ValueError(f"ruta con '..' en el tar: {name}")
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"miembro que no es archivo ni carpeta (symlink, enlace o dispositivo): {name}")
        member.name = posixpath.normpath(name)
        inside = member.name == folder or member.name.startswith(folder + "/")
        ancestor = member.isdir() and (folder + "/").startswith(member.name + "/")
        if not (inside or ancestor):
            raise ValueError(f"miembro fuera de {folder}: {name}")
        members.append(member)
    return members


def extract(tar_path, folder, root):
    with tarfile.open(tar_path) as tar:
        members = safe_members(tar, folder)
        options = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
        tar.extractall(root, members=members, **options)


def fetch_one(name, folder, base, sums, root):
    if name not in sums:
        raise RuntimeError(f"{name} no aparece en SHA256SUMS")
    tar_path = root / name
    for attempt in (1, 2):
        if not tar_path.exists():
            print(f"descargando {name}", flush=True)
            download(f"{base}/{name}", tar_path)
        if sha256(tar_path) == sums[name]:
            break
        tar_path.unlink()
        print(f"  {name}: sha256 distinto de SHA256SUMS", flush=True)
    else:
        raise RuntimeError(f"{name}: sha256 distinto de SHA256SUMS, no se extrae")
    try:
        extract(tar_path, folder, root)
    finally:
        tar_path.unlink()


def check_manifest(entries, folders_done, root):
    problems = []
    checked = 0
    for path, digest in sorted(entries.items()):
        if any(path == f or path.startswith(f + "/") for f in folders_done):
            checked += 1
            file = root / path
            if not file.is_file():
                problems.append(f"falta {path}")
            elif sha256(file) != digest:
                problems.append(f"distinto {path}")
    return checked, problems


def main(argv=None, root=ROOT, base=None):
    parser = argparse.ArgumentParser(description="Descarga y verifica los datos, predicciones y checkpoints publicados")
    parser.add_argument("--rounds", nargs="+", choices=list(ROUNDS), default=list(ROUNDS))
    parser.add_argument("--what", nargs="+", choices=KINDS, default=list(KINDS))
    parser.add_argument("--release", default="data-v1")
    args = parser.parse_args(argv)
    base = base or f"https://github.com/{REPO}/releases/download/{args.release}"
    try:
        with urllib.request.urlopen(f"{base}/SHA256SUMS", timeout=60) as response:
            sums = parse_sums(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as error:
        print(f"no pude leer SHA256SUMS de {base}: {error}")
        return 1
    failures = []
    for round_name in args.rounds:
        entries = manifest(root, round_name)
        done = []
        for folder in folders(entries, ROUNDS[round_name], args.what):
            try:
                fetch_one(tar_name(folder), folder, base, sums, root)
                done.append(folder)
            except (RuntimeError, ValueError, tarfile.TarError, OSError) as error:
                failures.append(f"{round_name}: {error}")
        checked, problems = check_manifest(entries, done, root)
        failures += [f"{round_name}: {p}" for p in problems]
        print(f"{round_name}: {checked} archivos comparados con {ROUNDS[round_name]}MANIFEST.sha256, {len(problems)} fallos", flush=True)
    if failures:
        print("FALLOS:")
        print("\n".join("  " + f for f in failures))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
