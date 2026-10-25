import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pd import ROOT, SOLVER_SHA256, SPLITS, np, sha256, write_json
from round3.verify import check_files, rounded
from round4 import NEW_SPLITS, R4, ROLL
from round4.data import generate4
from round4.evaluate import compute, load, summarize, thresholds

MANIFEST = R4 / "MANIFEST.sha256"
INPUTS = ("round4/data/", "round4/preds/", "round4/r1/data/val/", "round4/r1/thresholds.json", "round4/r1/round2/thresholds.json",
          "round4/r1/round3/thresholds.json", "round4/thresholds.json", "vendor/")
THRESHOLD_FILES = ("round4/thresholds.json", "round4/r1/thresholds.json", "round4/r1/round2/thresholds.json", "round4/r1/round3/thresholds.json", "vendor/")


def manifest():
    entries = {}
    for line in MANIFEST.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        entries[name.strip()] = digest
    return entries


def verdict_digest(verdicts):
    return {"hypotheses": rounded(verdicts["hypotheses"]), "flagged": {g: v["flagged"] for g, v in verdicts["groups"].items()},
            "floors": verdicts["sweep"]["floors"]}


def fingerprint(entries, verdicts):
    files = sorted([*(ROOT / "pd").glob("*.py"), *(ROOT / "round2").glob("*.py"), *(ROOT / "round3").glob("*.py"), *R4.glob("*.py")])
    code = {p.relative_to(ROOT).as_posix(): sha256(p) for p in files}
    inputs = {p: d for p, d in entries.items() if p.startswith(INPUTS)}
    text = json.dumps({"numpy": np.__version__, "solver": SOLVER_SHA256, "code": code, "inputs": inputs, "verdicts": verdict_digest(verdicts)}, sort_keys=True)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:]}"


def regenerate(out, report):
    entries = manifest()
    generate4(out)
    rows = []
    for split in tuple(NEW_SPLITS) + (ROLL,):
        for name in SPLITS[split][0]:
            canonical = f"round4/data/{split}/{name}.npy"
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
    print(f"regenerated {len(rows)} files, {sum(r['identical'] for r in rows)} bit-identical to round4/MANIFEST.sha256")
    return 0


def line(name, h):
    if "flagged" in h and "steps" in h:
        value = f"{h['flagged']:>5}/{h['steps']}"
    elif name in ("H7", "H13"):
        value = " ".join(f"rho={v['rho']:.3f} [{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}]" for v in h["by_group"].values())
        value += " | D3 " + " ".join(f"{v['rho']:.3f}" for v in h["comparator"]["by_group"].values())
    elif name == "H10":
        value = " ".join(f"{k}:{v['D2pp_mag_floor']}<{v['D2p_mag_floor']}" for k, v in h["by_group"].items())
    elif name == "H17":
        value = " ".join(f"{p}={v['E']['mean_rho']:.3f}[{v['E']['ci95'][0]:.3f}] k20={v['E']['rho_last']:.3f} dA={v['delta_vs_A']['delta']:+.3f}"
                         f"[{v['delta_vs_A']['ci95'][0]:+.3f}] dC={v['delta_vs_C']['delta']:+.3f}[{v['delta_vs_C']['ci95'][0]:+.3f}]" for p, v in h["by_group"].items())
    elif name == "H18":
        value = " ".join(f"{p}={min(v['median_ratio']):.3f}-{max(v['median_ratio']):.3f}" for p, v in h["by_group"].items())
    elif name == "H19":
        value = f"alarms={h['alarms']} new_fp={h['new_false_positives']} P1_on_time={h['P1']['on_time_share']}"
    else:
        value = f"on_time={h['on_time_share']} premature={h['premature_share']:.3f} crossing={h['crossing']} | A on_time={h['reference_A']['on_time_share']}"
    return f"  {name:<4} {h['check'][:38]:<38} {value}  {h.get('verdict', 'PASS' if h['pass'] else 'FAIL')}"


def main():
    parser = argparse.ArgumentParser(description="Re-verify the round-4 predictor-debugger evidence")
    parser.add_argument("--saved", metavar="MACHINE", help="re-apply the thresholds to round4/results/MACHINE without recomputing")
    parser.add_argument("--compare", metavar="MACHINE", default="mac")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--regenerate", type=Path, metavar="DIR", help="regenerate the round-4 splits into DIR and compare with the manifest")
    parser.add_argument("--report", type=Path, default=Path("regeneration.json"))
    args = parser.parse_args()
    print(f"predictor-debugger round-4 verify · {platform.system()} {platform.machine()} · Python {platform.python_version()} · numpy {np.__version__}")
    if args.regenerate:
        return regenerate(args.regenerate, args.report)
    entries = manifest()
    problems = check_files(entries, THRESHOLD_FILES)
    if args.saved:
        results = load(args.saved)
        saved = json.loads((R4 / "results" / args.saved / "verdicts.json").read_text())
    else:
        problems += check_files(entries, INPUTS)
        if problems:
            print("\n".join(problems))
            return 1
        results = compute(R4 / "data", R4 / "preds", args.jobs)
        saved = json.loads((R4 / "results" / args.compare / "verdicts.json").read_text())
    with np.errstate(all="ignore"):
        verdicts = summarize(results, *thresholds())
    for name, h in verdicts["hypotheses"].items():
        print(line(name, h))
    same = verdict_digest(verdicts) == verdict_digest(saved)
    print(f"  verdicts equal to saved round4/results/{args.saved or args.compare}/verdicts.json: {same}")
    for p in problems:
        print("  " + p)
    print(f"  fingerprint: {fingerprint(entries, verdicts)}")
    return 0 if same and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
