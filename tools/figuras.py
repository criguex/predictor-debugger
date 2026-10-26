import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets"

NAVY, DEEP, PANEL, GRID = "#071B2B", "#0D2638", "#123448", "#214456"
MINT, GOLD, CORAL = "#55DFBD", "#FFC56E", "#FB8176"
WHITE, MUTED = "#F4F7F5", "#ABC0C8"
FONT = "font-family=\"-apple-system,Segoe UI,Helvetica,Arial,sans-serif\""

ROUNDS = [
    ("1", "results/mac/verdicts.json", "EEC9-09E0-F77D"),
    ("2", "round2/results/comparison.json", "D506-F58F-3838"),
    ("3", "round3/results/comparison.json", "6319-537B-7167"),
    ("4", "round4/results/comparison.json", "681D-143B-64A3"),
]

ENVS = [
    ("Mac", "macOS", "rrrr"),
    ("WAR", "RTX 5070 · Win", "rrrr"),
    ("GUERRA", "RTX 4060 · Win", "rrrr"),
    ("Linux WSL2", "GUERRA", "rsss"),
    ("GitHub CI", "Ubuntu", "rrss"),
    ("Linux IA", "data-v1", "rrrr"),
]


def verdicts(path):
    d = json.loads((ROOT / path).read_text())
    if "hypotheses_by_machine" in d:
        h = d["hypotheses_by_machine"]["mac"]
        return {k: v in (True, "PASS") for k, v in h.items()}
    return {k: v["pass"] for k, v in d["hypotheses"].items()}


def order(name):
    n, suffix = re.fullmatch(r"H(\d+)(\w*)", name).groups()
    return int(n), suffix


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {FONT}>'
            f'<rect width="{w}" height="{h}" rx="14" fill="{NAVY}"/>{body}</svg>\n')


def banner():
    body = (f'<rect x="0" y="0" width="8" height="200" fill="{MINT}"/>'
            f'<text x="48" y="78" fill="{WHITE}" font-size="40" font-weight="700">predictor-debugger</text>'
            f'<text x="48" y="116" fill="{MUTED}" font-size="20">Depurador físico para predicciones de fluidos 3D</text>'
            f'<text x="48" y="146" fill="{MUTED}" font-size="20">Rondas preregistradas · fallos incluidos · huellas reproducibles</text>'
            f'<text x="48" y="178" fill="{MINT}" font-size="15" font-weight="600">Cristian Guerra · QA · Medellín</text>')
    for i, (r, _, fp) in enumerate(ROUNDS):
        y = 52 + i * 34
        body += (f'<rect x="700" y="{y - 20}" width="220" height="28" rx="6" fill="{DEEP}" stroke="{GRID}"/>'
                 f'<text x="714" y="{y - 1}" fill="{MUTED}" font-size="13">R{r}</text>'
                 f'<text x="744" y="{y - 1}" fill="{WHITE}" font-size="13" font-family="Menlo,Consolas,monospace">{fp}</text>')
    return svg(960, 200, body)


def rondas():
    body = (f'<text x="32" y="44" fill="{WHITE}" font-size="22" font-weight="700">Cada hipótesis preregistrada, ronda por ronda</text>'
            f'<text x="32" y="70" fill="{MUTED}" font-size="14">El umbral se fija antes de correr. Lo que falla se publica igual.</text>')
    y = 108
    for r, path, fp in ROUNDS:
        v = verdicts(path)
        ok = sum(v.values())
        body += (f'<text x="32" y="{y}" fill="{WHITE}" font-size="15" font-weight="600">Ronda {r}</text>'
                 f'<text x="110" y="{y}" fill="{MUTED}" font-size="14">{ok}/{len(v)} pasan</text>'
                 f'<text x="212" y="{y}" fill="{MUTED}" font-size="14">huella</text>'
                 f'<text x="262" y="{y}" fill="{WHITE}" font-size="14" font-family="Menlo,Consolas,monospace">{fp}</text>')
        for i, name in enumerate(sorted(v, key=order)):
            x = 32 + i * 50
            fill, mark = (MINT, "✓") if v[name] else (CORAL, "✗")
            body += (f'<rect x="{x}" y="{y + 12}" width="46" height="28" rx="6" fill="{fill}"/>'
                     f'<text x="{x + 23}" y="{y + 31}" fill="{NAVY}" font-size="12" font-weight="700" text-anchor="middle">{name} {mark}</text>')
        y += 76
    body += (f'<rect x="32" y="{y - 10}" width="14" height="14" rx="3" fill="{MINT}"/>'
             f'<text x="54" y="{y + 2}" fill="{MUTED}" font-size="13">✓ pasa</text>'
             f'<rect x="124" y="{y - 10}" width="14" height="14" rx="3" fill="{CORAL}"/>'
             f'<text x="146" y="{y + 2}" fill="{MUTED}" font-size="13">✗ falla: H14 pedía ρ ≥ 0,7 en las cuatro redes y P2gbest dio 0,635</text>')
    return svg(960, y + 26, body)


def reproduccion():
    body = (f'<text x="32" y="44" fill="{WHITE}" font-size="22" font-weight="700">Las mismas huellas en seis entornos</text>'
            f'<text x="32" y="70" fill="{MUTED}" font-size="14">Recalculado desde los datos, o huella comprobada sobre los resultados guardados.</text>')
    x0, cw, y0, rh = 150, 132, 104, 46
    for j, (name, sub, _) in enumerate(ENVS):
        cx = x0 + j * cw + cw / 2
        body += (f'<text x="{cx}" y="{y0}" fill="{WHITE}" font-size="14" font-weight="600" text-anchor="middle">{name}</text>'
                 f'<text x="{cx}" y="{y0 + 18}" fill="{MUTED}" font-size="12" text-anchor="middle">{sub}</text>')
    for i, (r, _, fp) in enumerate(ROUNDS):
        y = y0 + 40 + i * rh
        body += (f'<text x="32" y="{y + 20}" fill="{WHITE}" font-size="15" font-weight="600">Ronda {r}</text>'
                 f'<text x="32" y="{y + 36}" fill="{MUTED}" font-size="11" font-family="Menlo,Consolas,monospace">{fp}</text>')
        for j, (_, _, cells) in enumerate(ENVS):
            x = x0 + j * cw + 10
            if cells[i] == "r":
                body += (f'<rect x="{x}" y="{y + 4}" width="{cw - 20}" height="32" rx="6" fill="{MINT}"/>'
                         f'<text x="{x + (cw - 20) / 2}" y="{y + 25}" fill="{NAVY}" font-size="12" font-weight="700" text-anchor="middle">recalculado</text>')
            else:
                body += (f'<rect x="{x + 1}" y="{y + 5}" width="{cw - 22}" height="30" rx="6" fill="{DEEP}" stroke="{MINT}" stroke-width="2"/>'
                         f'<text x="{x + (cw - 20) / 2}" y="{y + 25}" fill="{WHITE}" font-size="12" text-anchor="middle">huella</text>')
    y = y0 + 40 + len(ROUNDS) * rh + 24
    body += (f'<text x="32" y="{y}" fill="{GOLD}" font-size="13">Mac, WAR y GUERRA son mías. Linux IA lo operó un asistente de IA bajo mi dirección: no es una revisión independiente.</text>')
    return svg(960, y + 22, body)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    figs = {"banner.svg": banner(), "rondas.svg": rondas(), "reproduccion.svg": reproduccion()}
    assert sum(len(verdicts(p)) for _, p, _ in ROUNDS) == 49
    assert not verdicts("round3/results/comparison.json")["H14"]
    for name, text in figs.items():
        (OUT / name).write_text(text)
        print(OUT / name)


if __name__ == "__main__":
    main()
