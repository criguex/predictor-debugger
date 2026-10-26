import contextlib
import hashlib
import io
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import fetch_data

PAYLOAD = b"velocidad de prueba"
BASE = Path(tempfile.mkdtemp())


def add(tar, name, data=PAYLOAD, kind=tarfile.REGTYPE, link=""):
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = link
    info.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
    info.size = len(data) if kind == tarfile.REGTYPE else 0
    tar.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)


def release(root, members, digest=None):
    folder = root / "release"
    folder.mkdir(exist_ok=True)
    with tarfile.open(folder / "data--val.tar", "w") as tar:
        for member in members:
            add(tar, *member)
    real = fetch_data.sha256(folder / "data--val.tar")
    (folder / "SHA256SUMS").write_text(f"{digest or real}  data--val.tar\n")
    return folder.as_uri()


def run(root, base):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = fetch_data.main(["--rounds", "r1", "--what", "data"], root=root, base=base)
    return code, out.getvalue()


def case(manifest_digest=None):
    root = Path(tempfile.mkdtemp(dir=BASE))
    good = hashlib.sha256(PAYLOAD).hexdigest()
    (root / "MANIFEST.sha256").write_text(f"{manifest_digest or good}  data/val/160.npy\nabc  thresholds.json\n")
    return root


def main():
    root = case()
    code, out = run(root, release(root, [("data/val", b"", tarfile.DIRTYPE), ("data/val/160.npy",)]))
    assert code == 0 and out.rstrip().endswith("OK"), out
    assert (root / "data/val/160.npy").read_bytes() == PAYLOAD
    assert not (root / "data--val.tar").exists()

    root = case()
    code, out = run(root, release(root, [("data/val/160.npy",)], digest="0" * 64))
    assert code == 1 and "SHA256SUMS" in out, out
    assert not (root / "data/val/160.npy").exists() and not (root / "data--val.tar").exists()

    root = case(manifest_digest="f" * 64)
    code, out = run(root, release(root, [("data/val/160.npy",)]))
    assert code == 1 and "distinto data/val/160.npy" in out, out

    hostile = [
        [("data/val/../../evil.txt",)],
        [("/tmp/evil.txt",)],
        [("data/val/link", b"", tarfile.SYMTYPE, "/etc/passwd")],
        [("data/val/hard", b"", tarfile.LNKTYPE, "pd/__init__.py")],
        [("pd/__init__.py",)],
        [("data/valx/160.npy",)],
    ]
    for members in hostile:
        root = case()
        code, out = run(root, release(root, members))
        assert code == 1 and "FALLOS" in out, (members, out)
        assert not (root / "data").exists() and not (root / "pd").exists(), members
        assert not (root.parent / "evil.txt").exists() and not (root / "data--val.tar").exists(), members

    assert fetch_data.tar_name("checkpoints/P2s0.pt") == "checkpoints--P2s0.tar"
    assert fetch_data.tar_name("round3/preds/P2gbest") == "round3--preds--P2gbest.tar"
    entries = fetch_data.manifest(fetch_data.ROOT, "r2")
    found = fetch_data.folders(entries, "round2/", fetch_data.KINDS)
    assert "round2/data/r2test" in found and "round2/checkpoints/P2gbest.pt" in found
    assert not any("/r1/" in f for f in found), found
    shutil.rmtree(BASE)
    print("tests/test_fetch_data.py: all checks passed")


if __name__ == "__main__":
    main()
