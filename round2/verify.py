import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import ROOT, SOLVER_SHA256, SPLITS, np, sha256, write_json
from pd.data import generate
from round2 import NEW_SPLITS, R2
from round2.evaluate import compute, summarize, thresholds

MANIFEST = R2 / "MANIFEST.sha256"
INPUTS = ("round2/data/", "round2/preds/", "round2/r1/data/val/", "round2/r1/thresholds.json", "round2/thresholds.json", "vendor/")


def manifest():
    entries = {}
    for line in MANIFEST.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        entries[name.strip()] = digest
    return entries


def check_files(entries, prefixes):
    problems = []
    for name, digest in sorted(entries.items()):
        if name.startswith(prefixes):
            file = ROOT / name
            if not file.is_file():
                problems.append(f"missing {name}")
            elif sha256(file) != digest:
                problems.append(f"changed {name}")
    return problems


def verdict_digest(verdicts):
    hypotheses = {}
    for name, h in verdicts["hypotheses"].items():
        keep = {k: h[k] for k in ("pass", "flagged", "steps") if k in h}
        if "rho" in h:
            keep.update(rho=round(h["rho"], 6), ci95=[round(v, 6) for v in h["ci95"]])
        if "by_group" in h:
            keep["by_group"] = {g: v if isinstance(v, int) else {"rho": round(v["rho"], 6), "ci95": [round(c, 6) for c in v["ci95"]]} for g, v in h["by_group"].items()}
        hypotheses[name] = keep
    return {"hypotheses": hypotheses, "flagged": {g: v["flagged"] for g, v in verdicts["groups"].items()}}


def fingerprint(entries, verdicts):
    code = {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted([*(ROOT / "pd").glob("*.py"), *R2.glob("*.py")])}
    inputs = {p: d for p, d in entries.items() if p.startswith(INPUTS)}
    text = json.dumps({"numpy": np.__version__, "solver": SOLVER_SHA256, "code": code, "inputs": inputs, "verdicts": verdict_digest(verdicts)}, sort_keys=True)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:]}"


def regenerate(out, report):
    entries = manifest()
    generate(out, NEW_SPLITS)
    rows = []
    for split in NEW_SPLITS:
        for name in SPLITS[split][0]:
            canonical = f"round2/data/{split}/{name}.npy"
            digest = sha256(out / split / f"{name}.npy")
            row = {"file": canonical, "manifest_sha256": entries.get(canonical), "regenerated_sha256": digest, "identical": digest == entries.get(canonical)}
            if row["identical"]:
                row["max_abs_difference"] = 0.0
            elif (ROOT / canonical).is_file():
                row["max_abs_difference"] = float(np.max(np.abs(np.load(out / split / f"{name}.npy") - np.load(ROOT / canonical))))
            else:
                row["max_abs_difference"] = None
            rows.append(row)
    write_json(report, {"files": len(rows), "identical": sum(r["identical"] for r in rows), "rows": rows})
    print(f"regenerated {len(rows)} files, {sum(r['identical'] for r in rows)} bit-identical to round2/MANIFEST.sha256")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Re-verify the round-2 predictor-debugger evidence")
    parser.add_argument("--saved", metavar="MACHINE", help="re-apply the thresholds to round2/results/MACHINE/stats.json without recomputing")
    parser.add_argument("--compare", metavar="MACHINE", default="mac")
    parser.add_argument("--regenerate", type=Path, metavar="DIR", help="regenerate the round-2 splits into DIR and compare with the manifest")
    parser.add_argument("--report", type=Path, default=Path("regeneration.json"))
    args = parser.parse_args()
    print(f"predictor-debugger round-2 verify · {platform.system()} {platform.machine()} · Python {platform.python_version()} · numpy {np.__version__}")
    if args.regenerate:
        return regenerate(args.regenerate, args.report)
    entries = manifest()
    problems = check_files(entries, ("round2/thresholds.json", "round2/r1/thresholds.json", "vendor/"))
    if args.saved:
        records = json.loads((R2 / "results" / args.saved / "stats.json").read_text())
        saved = json.loads((R2 / "results" / args.saved / "verdicts.json").read_text())
    else:
        problems += check_files(entries, INPUTS)
        if problems:
            print("\n".join(problems))
            return 1
        records = compute(R2 / "data", R2 / "preds")
        saved = json.loads((R2 / "results" / args.compare / "verdicts.json").read_text())
    verdicts = summarize(records, *thresholds())
    for name, h in verdicts["hypotheses"].items():
        value = f"{h['flagged']:>4}/{h['steps']}" if "flagged" in h else " ".join(f"rho={v['rho']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]" for v in h["by_group"].values()) if "by_group" in h else f"rho={h['rho']:.3f} [{h['ci95'][0]:.3f}, {h['ci95'][1]:.3f}]"
        print(f"  {name:<4} {h['predictor'][:16]:<16} {h['check']:<16} {value}  {h['criterion']:<40} {'PASS' if h['pass'] else 'FAIL'}")
    same = verdict_digest(verdicts) == verdict_digest(saved)
    print(f"  verdicts equal to saved round2/results/{args.saved or args.compare}/verdicts.json: {same}")
    for line in problems:
        print("  " + line)
    print(f"  fingerprint: {fingerprint(entries, verdicts)}")
    return 0 if same and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
