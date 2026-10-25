# Resultados · Ronda 3 · Piso de detección, alarma G′ y rollouts

Corrida el 2026-10-25 (UTC) bajo `round3/DESIGN.md`, sin enmiendas. Las rondas 1 y 2 no se tocaron y siguen verificando en las tres máquinas: **EEC9-09E0-F77D** y **D506-F58F-3838**.

## Orden y tiempos

| Paso | Commit | Hora (UTC) |
| --- | --- | --- |
| Piloto sobre datos ya vistos (validación y rollouts de la ronda 1, `r2test`, `r2ood5`, `r2ood6`) | incluido en el prerregistro | 04:03–04:30 |
| **Prerregistro** `round3/DESIGN.md` + código | `8fcbd16` (GitHub privado, rama `ronda-3`) | **04:30:01** |
| Umbrales desde validación | `9c01efb` | 04:31:24 |
| **Primer dato de evaluación** (generación de `r3test`, `r3ood5`, `r3ood6`, `r3roll`) | — | **04:31:25**, terminó 04:36:41 |
| Inferencia y rollouts de P2 en WAR | `847ce0a` | 04:39–04:50 |
| Corrida del depurador en el Mac (`--jobs 2`) | `fd1b3ec` | 04:50–05:24 |
| Recomputación completa en el Mac (`verify.py --jobs 2`) | | 05:26–06:00 |
| Corridas en WAR (04:57–06:07) y GUERRA (04:57–08:11) | `29f06de` | traídas a las 11:49 |
| Ledgers, verificación de las rondas 1–2 en remoto, limpieza | `29f06de` y este commit | 11:50–11:56 |

Entre las 06:10 y las 11:45 la sesión quedó detenida por una caída del clasificador de permisos; las corridas remotas ya estaban lanzadas y terminaron solas. Tiempos de cada etapa en `round3/logs/mac/timeline.log` y `round3/logs/mac/orchestration.log`.

## Hipótesis prerregistradas (datos nuevos)

`r3test` = semillas 3000–3039 (k₀ = 3, 400 pasos por predictor); `r3ood5` = 3100–3119 (k₀ = 5) y `r3ood6` = 3200–3219 (k₀ = 6), 200 pasos cada uno; `r3roll` = 3300–3339 (k₀ = 3), rollouts de 20 pasos. Mismo veredicto, mismos números, en Mac, WAR y GUERRA.

| Id | Criterio | Resultado (las tres máquinas) | Veredicto |
| --- | --- | --- | --- |
| H1 / H1b | P0 / P0f32 marcados ≤ 5 % (D1, D2, D3 de la ronda 1) | 0/400 · 0/400 | pasa |
| H2 / H3 / H4 | P3a por D1, P3b por D2, P1 por D3 ≥ 95 % | 400/400 · 400/400 · 400/400 | pasa |
| H5 | D2′ marca 0 pasos de P0/P0f32 en los tres splits | 0/1.600 | pasa |
| H6 | P3b marcado por D2′ solo por magnitud ≥ 95 % | 400/400 | pasa |
| H7 | ρ(G, D4) ≥ 0,8 e IC inf. ≥ 0,6 en P2s0 y P2s1; **comparador D3 debe fallar** | G: 0,938 [0,930; 0,944] · 0,980 [0,976; 0,982]. D3: −0,181 [−0,252; −0,120] · +0,062 [−0,010; 0,119] (falla) | **pasa** |
| **H9** | D2″ marca 0 pasos de P0/P0f32 en `r3test`, `r3ood5`, `r3ood6` | 0/1.600 | **pasa** |
| **H10** | Piso de D2″ al menos una década por debajo del de D2′, cada split y signo | 6/6 celdas (tabla abajo) | **pasa** |
| H10b | P3b marcado por D2″ solo por magnitud ≥ 95 % | 400/400 | pasa |
| **H11** | G′ marca 0 pasos de P0/P0f32 en los tres splits | 0/1.600 | **pasa** |
| **H12** | G′ marca P1, P3a y P3b ≥ 95 % en cada split | 2.400/2.400 | **pasa** |
| **H13** | ρ(G′, D4) ≥ 0,8 e IC inf. ≥ 0,6 en P2s0 y P2s1; **comparador D3 debe fallar** | G′: 0,936 [0,928; 0,943] · 0,979 [0,975; 0,981]. D3 falla (como en H7) | **pasa** |
| **H14** | Media sobre los 20 pasos del ρ entre trayectorias de A_k = ΣG contra D4_k ≥ 0,7 e IC inf. ≥ 0,5, en las cuatro redes; **comparador ΣD3 debe fallar** | A: P2s0 0,800 [0,657; 0,893] · P2s1 0,815 [0,692; 0,890] · P2ge4 0,747 [0,535; 0,863] · **P2gbest 0,635 [0,413; 0,795]**. ΣD3: 0,785 · 0,851 · 0,810 · 0,654 (cumple en tres de cuatro) | **FALLA** |
| **H15** | Alarma A_k ≥ 5 % a tiempo (≤ paso en que D4 > 5 %) ≥ 0,9 con IC inf. ≥ 0,8, y prematuras (D4 < 2,5 %) ≤ 0,1; **comparador: depurador de la ronda 2** | 160/160 a tiempo [1,00; 1,00], 0/160 prematuras [0; 0]. Comparador: 160/160 a tiempo pero 160/160 prematuras (falla) | **pasa** |
| **H16** | 0 alarmas acumuladas y 0 marcas de G′ en los rollouts de P0/P0f32; P1 a tiempo ≥ 95 % | 0/80 alarmas, 0/1.600 marcas; P1 40/40 | **pasa** |

IC = bootstrap por trayectoria (40 trayectorias con reemplazo, 2.000 réplicas, `default_rng(20261024)`, percentiles 2,5–97,5). Ninguna réplica dio estadístico no finito.

`round3/verify.py` imprime la huella **6319-537B-7167** en el Mac, re-aplicando umbrales (`round3/logs/mac/verify_saved.log`) y recalculando todo desde las predicciones (`round3/logs/mac/verify_recompute.log`; a ese log se le quitaron las líneas de `RuntimeWarning` de numpy, que vienen de Spearman sobre columnas constantes de P0); la salida completa, sin filtrar, de un segundo recálculo está en `round3/logs/mac/verify_recompute_raw.log` (25-oct, 12:59–14:13 UTC, misma huella y mismos veredictos, con sus 2 líneas de `RuntimeWarning`), y la misma en WAR y GUERRA (`round3/logs/{war,guerra}/verify_saved.log`). Esta vez todos los `round3/*.py` se copiaron a las dos máquinas antes de verificar, y la primera huella remota salió bien. En WAR y GUERRA también se verificaron las rondas anteriores con sus resultados guardados: EEC9-09E0-F77D y D506-F58F-3838 (`round3/logs/{war,guerra}/verify_r{1,2}_saved.log`).

## Debilidad 1: el piso de sensibilidad de D2′

Barrido de mutaciones graduadas sobre cada paso exacto (P0) de los tres splits (800 pasos). **Piso** = la menor magnitud de la grilla a partir de la cual se marca ≥ 95 % de los pasos en esa magnitud y en todas las mayores. Familia de energía: reescalado uniforme con E(u₁′) − E(u₁) = ±m·E₀ (+ inyecta, − es disipación de más). Pisos por magnitud sola (`_mag`); con la regla de aumento de energía ningún piso cambia (`round3/results/mac/verdicts.json`, `sweep`).

| Split | Signo | D2 (ronda 1, τ 3,31e-3) | D2′ (ronda 2, τ 1,19e-6) | **D2″** (ronda 3, τ 1,19e-6) | marcados con m = 0 (D2 / D2′ / D2″) |
| --- | --- | --- | --- | --- | --- |
| `r3test` | + | 3,2e-3 | 3,2e-4 | **3,2e-6** | 0 % / 0 % / 0 % |
| `r3test` | − | 1,0e-2 | 3,2e-4 | **3,2e-6** | 0 % / 0 % / 0 % |
| `r3ood5` | + | 3,2e-3 | 1,0e-2 | **1,0e-4** | 11 % / 0 % / 0 % |
| `r3ood5` | − | 1,0e-2 | 1,0e-2 | **1,0e-4** | 11 % / 0 % / 0 % |
| `r3ood6` | + | 3,2e-3 | 1,0e-2 | **3,2e-4** | 40 % / 0 % / 0 % |
| `r3ood6` | − | 3,2e-2 | 1,0e-2 | **3,2e-4** | 40 % / 0 % / 0 % |

- **D2′ no ve errores de energía de 3·10⁻⁴ en distribución ni de 10⁻² fuera** (k₀ = 5 y 6): ese es el piso que la ronda 2 había anunciado sin medir. Fuera de distribución D2′ ve inyecciones *peor* que el D2 viejo (1e-2 contra 3,2e-3), porque la corrección que resta crece con k₀.
- **D2″ baja el piso dos décadas en distribución (3,2e-6) y entre 1,5 y 2 fuera (1e-4, 3,2e-4)**, sin una sola marca sobre los controles (H9) y igual para los dos signos (H10).
- El D2 viejo es asimétrico: ve una inyección de 3,2e-3 pero necesita 1e-2–3,2e-2 de disipación de más, porque el residuo propio del trapecio tiene signo y la disipación lo cancela. Fuera de distribución su piso además está contaminado: marca 11 % y 40 % de los pasos exactos sin mutación.
- Momento (perturbación solenoidal aleatoria con D4 = m exacto), pisos de D3 / G / G6 / **G′**: `r3test` 1e-2 / 1e-4 / 1e-6 / **1e-5**; `r3ood5` ninguno (> 1e-2) / 1e-4 / 1e-6 / **1e-4**; `r3ood6` ninguno / 1e-4 / 1e-6 / **3,2e-4**. Marcados con m = 0: G 0 / 0 / 10 %, G6 0 / 9 % / 10 %, D3 y G′ 0 en los tres. D3 no ve un error de estado de 1 % fuera de distribución.

## Debilidad 2: G como alarma fuera de distribución

**Diagnóstico.** De las tres causas candidatas (paso 0, espectro cerca del borde de la máscara 2/3, truncamiento de la cuadratura) no son alternativas: las falsas alarmas son truncamiento de la cuadratura, grande en el paso 0 porque el espectro de k₀ = 6 empieza con energía en el borde de la máscara, que es la parte más rápida del flujo.

- Sobre los 800 pasos de P0 en los tres splits, G es su propia corrección de truncamiento T = G6 − G′: ρ(G, T) = 0,9999996 y la mediana de G/T es 0,999.
- G cae con el paso: ρ(G, paso) = −0,82. Medianas de G en `r3ood6` del paso 0 al 9: 1,45e-4, 6,5e-5, 3,1e-5, …, 8,8e-7; en `r3test`, 6,6e-6 → 2,1e-7; en validación (k₀ = 3), 6,9e-6 → 2,2e-7.
- La fracción de energía en el borde de la máscara (max\|kᵢ\| ≥ 0,8·32/3) en el paso 0 es 2,6 % con k₀ = 6, 0,57 % con k₀ = 5 y 8e-6 con k₀ = 3. Con k₀ = 5 y 6 decae con el tiempo (νk² llega a ≈ 15 en esos modos); con k₀ = 3 sube un poco por la cascada y se queda en ~5e-5. ρ(G, borde) = 0,57.
- La validación (k₀ = 3) no tiene ese régimen, así que τ_G = 7,8e-5 queda por debajo de los 1,45e-4 del paso 0 con k₀ = 6. Con datos nuevos G marca P0 y P0f32 en el paso 0 de las 20 trayectorias de `r3ood6`, igual que en la ronda 2.

Subir el orden no basta: G6 (sexto orden, sin resta) con su umbral de validación marca 18/200 pasos de control en `r3ood5` y 40/200 en `r3ood6`. Lo que quita las falsas alarmas es restar la corrección.

**G′ = G6 − T** no da ni una falsa alarma (H11: 0/1.600 pasos de control; también 0/1.600 en los rollouts de P0 y P0f32) y sigue marcando P1, P3a y P3b en todos los pasos de los tres splits (H12), y P2s0 y P2s1 también en todos. Ordena igual que G (H13: 0,936 y 0,979 contra 0,938 y 0,980), con D3 fallando el mismo criterio. El precio es el de D2″: su piso de momento fuera de distribución (1e-4, 3,2e-4) es peor que el de G6 (1e-6), aunque en k₀ = 6 G6 y G tienen 10 % de falsas alarmas y G′ ninguna.

## Debilidad 3: rollouts

Rollouts de 20 pasos (t ∈ [0, 2]) desde 40 estados iniciales nuevos, cada red alimentada con su propia salida float32 en la GPU de WAR.

| Red | D4 paso 1 | D4 paso 20 | A_20 | G paso 1 → 20 | D4loc paso 1 → 20 | ρ(G, D4loc) | G/D4loc | cruce de 5 % (paso) | alarma (paso) | anticipación |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2s0 | 1,04 % | 7,2 % | 13,2 % | 1,14 % → 0,40 % | 1,04 % → 0,42 % | 0,9997 | 0,99 | 11 (9–13) | 6 | 5 (4–7) |
| P2s1 | 1,00 % | 10,7 % | 14,7 % | 1,08 % → 0,56 % | 1,00 % → 0,57 % | 0,9992 | 1,00 | 9 (8–10) | 6 | 3 (2–4) |
| P2ge4 | 1,76 % | 13,1 % | 21,1 % | 1,89 % → 0,64 % | 1,76 % → 0,69 % | 0,9996 | 0,97 | 5 (4–5) | 4 | 1 (0–2) |
| P2gbest | 0,74 % | 6,1 % | 10,2 % | 0,80 % → 0,33 % | 0,74 % → 0,35 % | 0,9987 | 0,96 | 16 (13–18) | 8 | 8 (6–9) |

Medianas sobre las 40 trayectorias (entre paréntesis, rango). D4loc es el error de un paso desde el propio estado del rollout.

- **G mide el error local a lo largo del rollout** (ρ(G, D4loc) ≥ 0,9987; G/D4loc entre 0,96 y 1,00), aunque el estado ya no sea el de la referencia. Exploratorio.
- **El error local baja con el tiempo y el acumulado crece menos que la suma**: A_k sobrestima D4_k en un factor de ~1,1 en el paso 1 y de 1,4–1,8 en el paso 20.
- **H14 falla, y su comparador tampoco hace lo que se esperaba.** La acumulación de G ordena las trayectorias por error de rollout con ρ = 0,99 en el paso 1, pero ese orden se degrada con el tiempo (0,45–0,73 en el paso 20) y la media no llega a 0,7 en P2gbest (0,635, IC [0,413; 0,795]); en P2ge4 el extremo inferior queda en 0,535. Al mismo tiempo, ΣD3, que en un paso ordena al revés, acumulado sí ordena entre trayectorias (0,785, 0,851, 0,810, 0,654) y cumple el criterio en tres redes. Qué significa: **el depurador sabe cuánto se equivoca la red en cada paso, pero no sabe a qué trayectoria la llevan peor esos errores**, porque cuánto crece el error acumulado depende de la dinámica de cada trayectoria (cuánto amortigua o amplifica errores pasados), y eso ni G ni su suma lo ven. ΣD3 lo hace algo mejor por una razón que no es física: su normalizador ‖N(u₀)‖ cambia de trayectoria a trayectoria de un modo que correlaciona con ese crecimiento. El piloto (10 pasos, P2s1: 0,835) ya lo insinuaba; el criterio no se cambió.
- **H15 pasa.** Las 160 trayectorias de las cuatro redes cruzan D4 > 5 % dentro de los 20 pasos; la alarma acumulada suena antes o en el mismo paso en 160/160, con 0 a 9 pasos de anticipación (0 = el mismo paso, solo en P2ge4), y nunca con D4 < 2,5 %. El depurador de la ronda 2 también "suena a tiempo" en 160/160, pero siempre en el paso 1 con D4 ≈ 1 %: 160/160 prematuras; lo mismo `any3` (la ronda 3 paso a paso). La alarma acumulada es la única de las tres que dice *cuándo* el rollout se vuelve malo y no solo que la red no es exacta. Como sobrestima, es conservadora: con P2gbest suena en el paso 8 y D4 cruza en el 16.
- **H16 pasa.** Ninguna alarma acumulada ni marca de G′ en los 80 rollouts de P0 y P0f32 (P0f32 encadena el solver redondeado a float32); con P1 la alarma y el cruce caen en el paso 1 en 40/40.
- Exploratorio: juntando todos los pasos, A, ΣD3 y el número de paso ordenan D4 con ρ entre 0,987 y 0,998: por eso esa no podía ser la prueba. D3 por paso solo marca 29/800 pasos del rollout de P2gbest; D1 y G′ los marcan todos.

## Ledgers

- `round3/ledgers/discrepancies.jsonl`: **0 entradas** (todo paso, predictor, split y marca de `KEYS`, cada detección del barrido y cada registro de alarma de rollout, en las tres máquinas).
- `round3/ledgers/false_positives.jsonl`: **960 entradas, ninguna de un chequeo del depurador de la ronda 3** (D1, D3, D2″, G′, alarma acumulada: 0). Por máquina, iguales en las tres: 204 del D2 viejo (`r3ood5` pasos 0–1, `r3ood6` pasos 0–3), 40 de G (`r3ood6` paso 0) y 76 de G6 (`r3ood5` y `r3ood6`, primeros pasos). D2′ también 0.
- **Explicadas a mano, con evidencia de los mismos datos**: en las 612 entradas de D2, D2′ < 0, es decir, el residuo del trapecio es menor que su propia corrección de cuadratura (|R₄| < |C|); en las 120 de G, G/T = 0,994 (G es su propio truncamiento) y G′ < 0; en las 228 de G6, G′ < 0 (‖r₆‖ < ‖r₆ − r₄‖). La ronda 2 ya mostró con subintervalos que esos residuos caen como orden 2 y 4. En el archivo quedan `open`, como pide el diseño; **contadas así: 960 explicadas, 0 abiertas**.

## Reproducibilidad entre máquinas

| | Mac | WAR | GUERRA |
| --- | --- | --- | --- |
| Splits de la ronda 3 regenerados, bit-idénticos al Mac | (canónicos) | 0 / 120 | 0 / 120 |
| Diferencia absoluta máxima contra los archivos del Mac | | 7,2e-16 | 7,2e-16 |
| Tiempo del depurador (todo) | 1.956 s (2 procesos) | 3.436 s (6 procesos) | 9.457 s (6 procesos) |
| `tests/test_checks.py`, `round2/test_checks2.py`, `round3/test_checks3.py` | pasan | pasan | pasan |
| Huella r1 / r2 / r3 | EEC9-09E0-F77D / D506-F58F-3838 / 6319-537B-7167 | igual | igual |

La mayor diferencia entre máquinas en cualquier estadístico fue 4,4e-16 (D4s) y 3,3e-16 (D3); G, G6 y G′ difieren a lo sumo en 5,6e-17; D2″ en 2,8e-16; D4loc y E₀ salieron bit-idénticos. numpy 1.26.4 en las tres; Python 3.9.6 (Mac), 3.12.10 (WAR, torch 2.7.0+cu128 para la inferencia), 3.12.3 (GUERRA).

Transferencias (`round3/logs/transfers.tsv`, 1.064 filas, SHA-256 verificado en ambos extremos):

| Dirección | Archivos | Bytes | Reintentos | Fallidos |
| --- | --- | --- | --- | --- |
| Mac → WAR | 194 | 1,69 GB | 0 | 0 |
| Mac → GUERRA | 510 | 5,31 GB | 0 | 0 |
| WAR → Mac | 344 | 3,80 GB | 0 | 0 |
| GUERRA → Mac | 16 | 28 MB | 0 | 0 |

`C:\ADN\pd-exp-r3\` se borró en WAR (653 archivos, 6,8 GB) y GUERRA (645 archivos, 6,7 GB) después de traer y verificar todo, junto con el `.ps1` temporal de `C:\Users\Public` (`round3/logs/{war,guerra}/cleanup.log`). Espacio libre en C:: WAR 60,02 GB al empezar y 59,79 GB después; GUERRA 92,44 GB y 92,39 GB. La pequeña diferencia no es de esta carpeta, que ya no existe. No se tocó nada más en esas máquinas; las GPU estaban ociosas al empezar y la fábrica de vídeo siguió en pausa.

## Lo que no salió como se diseñó, o no se hizo

- **H14 falla** y su comparador (ΣD3) cumple el criterio en tres redes: el contraste que se esperaba discriminativo no lo fue. No se cambió nada para arreglarlo.
- El primer lanzamiento remoto (04:50 en WAR, 04:56 en GUERRA) pasó los argumentos con comillas literales y no corrió nada; se corrigió `round3/tools/launch.ps1` (parámetros `-Machine`, `-Jobs`) y se relanzó a las 04:57, antes de que existiera ningún resultado remoto. Los logs vacíos quedan como `evaluate_run_quoting_failed.log`.
- El barrido de momento del piloto se corrió antes de añadirle D3; por eso el piloto no tiene piso de D3.
- Las mutaciones son de una sola forma por familia (reescalado uniforme; una dirección solenoidal suave por paso). Otras formas de error pueden tener otros pisos.
- No se repitió H8 (ranking del set graduado en un paso); las redes graduadas se usaron en rollouts.
- GUERRA tardó unas 5 veces lo que el Mac en tiempo total aun con el triple de procesos; terminó sola durante la caída del clasificador.
- Los resultados por máquina pesan ~26 MB (`sweep.json` 13,6 MB) y quedan en git como en las rondas anteriores.

## Límites (de DESIGN, sin cambios)

Misma caja 32³, viscosidad, Δ y arquitectura. D2″ y G′ siguen cambiando sensibilidad por robustez, solo que a un nivel más bajo. Horizonte de 20 pasos, solo k₀ = 3, y redes entrenadas para un paso. Nada de esto dice algo sobre el problema del milenio ni sobre turbulencia real.

## Archivos

`round3/DESIGN.md` · `round3/thresholds.json` · `round3/MANIFEST.sha256` · `round3/results/{mac,war,guerra}/` (`onestep.json`, `rollout.json`, `sweep.json`, `verdicts.json`, `environment.json`) · `round3/results/comparison.json` · `round3/ledgers/` · `round3/logs/` · `round3/pilot/` · `round3/verify.py`. Datos y predicciones (~4,8 GB) fuera de git, con hash en el manifiesto.
