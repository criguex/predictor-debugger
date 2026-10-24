import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

from pd import ROOT, SOLVER_SHA256, SPLITS, np, sha256, write_json
from pd.data import generate
from pd.evaluate import compute, summarize

INPUTS = ("data/val/", "data/test/", "data/ood/", "preds/")


def manifest():
    entries = {}
    for line in (ROOT / "MANIFEST.sha256").read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        entries[path.strip()] = digest
    return entries


def check_files(entries, prefixes):
    problems = []
    for path, digest in sorted(entries.items()):
        if path.startswith(prefixes):
            file = ROOT / path
            if not file.is_file():
                problems.append(f"missing {path}")
            elif sha256(file) != digest:
                problems.append(f"changed {path}")
    return problems


def verdict_digest(verdicts):
    return {
        "hypotheses": {k: {"pass": h["pass"], "flagged": h["flagged"], "steps": h["steps"]} for k, h in verdicts["hypotheses"].items()},
        "flagged": {g: v["flagged"] for g, v in verdicts["groups"].items()},
        "confusion": {label: e["confusion_test"] for label, e in verdicts["exploratory"].items()},
    }


def fingerprint(entries, verdicts):
    code = {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted((ROOT / "pd").glob("*.py"))}
    inputs = {p: d for p, d in entries.items() if p.startswith(INPUTS)}
    text = json.dumps({
        "numpy": np.__version__, "solver": SOLVER_SHA256, "code": code,
        "thresholds": sha256(ROOT / "thresholds.json"), "inputs": inputs, "verdicts": verdict_digest(verdicts),
    }, sort_keys=True)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:]}"


def regenerate(out, splits, report):
    entries = manifest()
    generate(out, splits)
    rows = []
    for split in splits:
        for name in SPLITS[split][0]:
            path = f"data/{split}/{name}.npy"
            digest = sha256(out / split / f"{name}.npy")
            row = {"file": path, "manifest_sha256": entries.get(path), "regenerated_sha256": digest, "identical": digest == entries.get(path)}
            if row["identical"]:
                row["max_abs_difference"] = 0.0
            elif (ROOT / path).is_file():
                row["max_abs_difference"] = float(np.max(np.abs(np.load(out / split / f"{name}.npy") - np.load(ROOT / path))))
            else:
                row["max_abs_difference"] = None
            rows.append(row)
    write_json(report, {"files": len(rows), "identical": sum(r["identical"] for r in rows), "rows": rows})
    print(f"regenerated {len(rows)} files, {sum(r['identical'] for r in rows)} bit-identical to MANIFEST")
    return all(r["identical"] for r in rows)


def main():
    parser = argparse.ArgumentParser(description="Re-verify the predictor-debugger evidence")
    parser.add_argument("--saved", metavar="MACHINE", help="re-apply thresholds.json to results/MACHINE/stats.json without recomputing")
    parser.add_argument("--compare", metavar="MACHINE", default="mac", help="saved verdicts to compare a recomputation with")
    parser.add_argument("--regenerate", type=Path, metavar="DIR", help="regenerate the dataset into DIR and compare with MANIFEST")
    parser.add_argument("--splits", nargs="+", default=["val", "test", "ood"])
    parser.add_argument("--report", type=Path, default=Path("regeneration.json"))
    args = parser.parse_args()
    print(f"predictor-debugger verify · {platform.system()} {platform.machine()} · Python {platform.python_version()} · numpy {np.__version__}")
    if args.regenerate:
        return 0 if regenerate(args.regenerate, args.splits, args.report) else 1
    entries = manifest()
    problems = check_files(entries, ("thresholds.json", "vendor/"))
    thresholds = json.loads((ROOT / "thresholds.json").read_text())["thresholds"]
    if args.saved:
        records = json.loads((ROOT / "results" / args.saved / "stats.json").read_text())
        saved = json.loads((ROOT / "results" / args.saved / "verdicts.json").read_text())
    else:
        problems += check_files(entries, INPUTS)
        if problems:
            print("\n".join(problems))
            return 1
        records = compute(ROOT / "data", ROOT / "preds")
        saved = json.loads((ROOT / "results" / args.compare / "verdicts.json").read_text())
    verdicts = summarize(records, thresholds)
    for name, h in verdicts["hypotheses"].items():
        print(f"  {name}  {h['predictor']:<6} {h['check']:<4} {h['flagged']:>4}/{h['steps']}  {h['criterion']:<15} {'PASS' if h['pass'] else 'FAIL'}")
    same = verdict_digest(verdicts) == verdict_digest(saved)
    print(f"  verdicts equal to saved results/{args.saved or args.compare}/verdicts.json: {same}")
    for line in problems:
        print("  " + line)
    print(f"  fingerprint: {fingerprint(entries, verdicts)}")
    return 0 if same and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
