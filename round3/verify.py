import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import ROOT, SOLVER_SHA256, SPLITS, np, sha256, write_json
from round3 import NEW_SPLITS, R3, ROLL
from round3.data import generate3
from round3.evaluate import compute, load, summarize, thresholds

MANIFEST = R3 / "MANIFEST.sha256"
INPUTS = ("round3/data/", "round3/preds/", "round3/r1/data/val/", "round3/r1/thresholds.json", "round3/r1/round2/thresholds.json", "round3/thresholds.json", "vendor/")
THRESHOLD_FILES = ("round3/thresholds.json", "round3/r1/thresholds.json", "round3/r1/round2/thresholds.json", "vendor/")


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


def rounded(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items() if k not in ("per_step", "records")}
    if isinstance(value, list):
        return [rounded(v) for v in value]
    return value


def verdict_digest(verdicts):
    return {"hypotheses": rounded(verdicts["hypotheses"]), "flagged": {g: v["flagged"] for g, v in verdicts["groups"].items()},
            "floors": verdicts["sweep"]["floors"]}


def fingerprint(entries, verdicts):
    code = {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted([*(ROOT / "pd").glob("*.py"), *(ROOT / "round2").glob("*.py"), *R3.glob("*.py")])}
    inputs = {p: d for p, d in entries.items() if p.startswith(INPUTS)}
    text = json.dumps({"numpy": np.__version__, "solver": SOLVER_SHA256, "code": code, "inputs": inputs, "verdicts": verdict_digest(verdicts)}, sort_keys=True)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:]}"


def regenerate(out, report):
    entries = manifest()
    generate3(out)
    rows = []
    for split in tuple(NEW_SPLITS) + (ROLL,):
        for name in SPLITS[split][0]:
            canonical = f"round3/data/{split}/{name}.npy"
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
    print(f"regenerated {len(rows)} files, {sum(r['identical'] for r in rows)} bit-identical to round3/MANIFEST.sha256")
    return 0


def line(name, h):
    if "flagged" in h and "steps" in h:
        value = f"{h['flagged']:>5}/{h['steps']}"
    elif name in ("H7", "H13"):
        value = " ".join(f"rho={v['rho']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]" for v in h["by_group"].values())
        value += " | D3 " + " ".join(f"{v['rho']:.3f}" for v in h["comparator"]["by_group"].values())
    elif name == "H14":
        value = " ".join(f"{p}={v['A']['mean_rho']:.3f}[{v['A']['ci95'][0]:.3f}]/C={v['C']['mean_rho']:.3f}" for p, v in h["by_group"].items())
    elif name == "H15":
        value = f"on_time={h['on_time_share']} premature={h['premature_share']:.3f} crossing={h['crossing']}"
    elif name == "H16":
        value = f"alarms={h['alarms']} Gp={h['Gp_flags']} P1_on_time={h['P1']['on_time_share']}"
    else:
        value = " ".join(f"{k}:{v['D2pp_mag_floor']}<{v['D2p_mag_floor']}" for k, v in h["by_group"].items())
    return f"  {name:<4} {h['check'][:34]:<34} {value}  {h.get('verdict', 'PASS' if h['pass'] else 'FAIL')}"


def main():
    parser = argparse.ArgumentParser(description="Re-verify the round-3 predictor-debugger evidence")
    parser.add_argument("--saved", metavar="MACHINE", help="re-apply the thresholds to round3/results/MACHINE without recomputing")
    parser.add_argument("--compare", metavar="MACHINE", default="mac")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--regenerate", type=Path, metavar="DIR", help="regenerate the round-3 splits into DIR and compare with the manifest")
    parser.add_argument("--report", type=Path, default=Path("regeneration.json"))
    args = parser.parse_args()
    print(f"predictor-debugger round-3 verify · {platform.system()} {platform.machine()} · Python {platform.python_version()} · numpy {np.__version__}")
    if args.regenerate:
        return regenerate(args.regenerate, args.report)
    entries = manifest()
    problems = check_files(entries, THRESHOLD_FILES)
    if args.saved:
        results = load(args.saved)
        saved = json.loads((R3 / "results" / args.saved / "verdicts.json").read_text())
    else:
        problems += check_files(entries, INPUTS)
        if problems:
            print("\n".join(problems))
            return 1
        results = compute(R3 / "data", R3 / "preds", args.jobs)
        saved = json.loads((R3 / "results" / args.compare / "verdicts.json").read_text())
    verdicts = summarize(results, *thresholds())
    for name, h in verdicts["hypotheses"].items():
        print(line(name, h))
    same = verdict_digest(verdicts) == verdict_digest(saved)
    print(f"  verdicts equal to saved round3/results/{args.saved or args.compare}/verdicts.json: {same}")
    for p in problems:
        print("  " + p)
    print(f"  fingerprint: {fingerprint(entries, verdicts)}")
    return 0 if same and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
