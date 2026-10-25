# Resultados · Ronda 2 · Ranking y balance de energía fuera de distribución

Corrida el 2026-10-25 (UTC) bajo `round2/DESIGN.md`, sin enmiendas. La ronda 1 (`f1080ed`) no se tocó.

## Orden y tiempos

| Paso | Commit | Hora (UTC) |
| --- | --- | --- |
| Piloto sobre datos de la ronda 1 (ya vistos) | incluido en el prerregistro | terminó 01:11 |
| **Prerregistro** `round2/DESIGN.md` + código | `35cd38f` (en GitHub privado, rama `ronda-2`) | **01:13:23** |
| Umbrales desde validación | `07de15b` | 01:14:02 |
| **Primer dato de evaluación** (generación de `r2test`, `r2ood5`, `r2ood6`) | — | **01:14:08**, terminó 01:16:44 |
| Inferencia de P2 y entrenamiento graduado en WAR | `3d19791` | 01:19–01:24 |
| Corrida del depurador en el Mac | `806a8da` | 01:28–01:38 |
| Corridas en WAR (01:37–02:03) y GUERRA (01:37–02:49), ledgers, diagnóstico, limpieza | ver abajo | 02:50 |

Los tiempos de cada etapa están en `round2/logs/mac/timeline.log` y `round2/logs/mac/orchestration.log`.

## Hipótesis prerregistradas (datos nuevos)

`r2test` = semillas 2000–2039, k₀ = 3, 400 pasos por predictor. `r2ood5` = 2100–2119, k₀ = 5; `r2ood6` = 2200–2219, k₀ = 6; 200 pasos cada uno.

| Id | Criterio | Mac | WAR | GUERRA | Resultado |
| --- | --- | --- | --- | --- | --- |
| H1 | P0 marcado ≤ 5 % (D1, D2, D3 de la ronda 1) | 0/400 | 0/400 | 0/400 | pasa |
| H1b | P0f32 marcado ≤ 5 % | 0/400 | 0/400 | 0/400 | pasa |
| H2 | P3a marcado por D1 ≥ 95 % | 400/400 | 400/400 | 400/400 | pasa |
| H3 | P3b marcado por D2 ≥ 95 % | 400/400 | 400/400 | 400/400 | pasa |
| H4 | P1 marcado por D3 ≥ 95 % | 400/400 | 400/400 | 400/400 | pasa |
| **H5** | P0 y P0f32 marcados por D2′ en **0** pasos de `r2test`, `r2ood5` y `r2ood6` | 0/1600 | 0/1600 | 0/1600 | **pasa** |
| **H6** | P3b marcado por D2′ solo por magnitud (sin la regla de aumento de energía) ≥ 95 % | 400/400 | 400/400 | 400/400 | **pasa** |
| **H7** | ρ(G, D4) ≥ 0,8 y extremo inferior del IC 95 % ≥ 0,6, para P2 semilla 0 **y** semilla 1 | 0,934 [0,924; 0,942] · 0,974 [0,968; 0,979] | igual | igual | **pasa** |
| **H8** | ρ(G, D4) ≥ 0,9 y extremo inferior ≥ 0,8, juntando el set graduado | 0,9987 [0,9985; 0,9988] | igual | igual | **pasa** |

IC = bootstrap por trayectoria (40 trayectorias remuestreadas con reemplazo, 2.000 réplicas, `default_rng(20261024)`, percentiles 2,5–97,5). Ninguna réplica dio ρ no finito.

`round2/verify.py` imprime la huella **D506-F58F-3838** en el Mac, tanto re-aplicando umbrales a lo guardado como recalculando todo desde las predicciones (`round2/logs/mac/verify_recompute.log`, ~10 min), y la misma en WAR (`round2/logs/war/verify_saved_full_code.log`) y GUERRA (`round2/logs/guerra/verify_saved.log`). La primera verificación de WAR (`round2/logs/war/verify_saved.log`) dio **89F8-7D3B-24AA** con los mismos veredictos: a WAR no se le había copiado `round2/pilot.py`, y la huella incluye el hash de todo `round2/*.py`. Es el mismo tipo de diferencia que el 1A51… de la ronda 1. Copiado el archivo, WAR da D506-F58F-3838; a GUERRA se le copió antes de que verificara. Los dos logs se dejan tal como salieron. `uv.lock` SHA-256 `c94e4b1a…9eb43` (también en `round2/thresholds.json`).

## Debilidad 1: el ranking

**La causa que se sospechaba no era.** En la ronda 1 se pensó que D3 estaba dominado por la parte no solenoidal de la predicción. Con datos nuevos, proyectar primero (D3p, la propuesta original) deja el ranking igual de roto:

| Estadístico (`r2test`) | P2 semilla 0 | P2 semilla 1 |
| --- | --- | --- |
| D3 (ronda 1) | −0,205 [−0,277; −0,146] | +0,029 [−0,045; 0,089] |
| D3p: D3 sobre la predicción proyectada, dividido por ‖N(u₀)‖ | −0,226 [−0,298; −0,167] | +0,021 [−0,053; 0,080] |
| Gs: parte solenoidal del residuo de Hermite, en unidades de estado | 0,844 [0,829; 0,857] | 0,943 [0,931; 0,952] |
| **G**: residuo de Hermite completo, en unidades de estado | **0,934 [0,924; 0,942]** | **0,974 [0,968; 0,979]** |

Lo que rompía el ranking era el **normalizador** de D3, ‖N(u₀)‖, que cambia de paso a paso sin relación con el error. G multiplica el residuo por Δ y lo divide por ‖u₁‖: así queda en las unidades de D4, y de hecho lo estima sin ver la referencia. La mediana de G/D4 va de 1,07 a 1,23 según el predictor: G sobrestima D4 entre 7 % y 23 %, de forma estable, porque Δ·r ≈ (I − ΔJ/2) δ.

**Set graduado** (un entrenamiento nuevo de P2 en WAR, semilla torch 2, pesos tras las épocas 1, 2, 4, 8 y los mejores, época 54 de 64):

| Predictor | MSE de validación | D4 mediana (`r2test`) | ρ(G, D4) dentro | ρ(D3, D4) dentro |
| --- | --- | --- | --- | --- |
| P2ge1 | 9,4e-5 | 4,10 % | 1,000 | −0,677 |
| P2ge2 | 3,7e-5 | 2,59 % | 0,999 | −0,635 |
| P2ge4 | 1,3e-5 | 1,61 % | 0,964 | −0,658 |
| P2ge8 | 6,8e-6 | 1,18 % | 0,916 | −0,310 |
| P2gbest | 2,8e-6 | 0,74 % | 0,956 | −0,144 |
| Todos juntos (H8) | | 0,62 %–5,4 % | **0,9987** | 0,931 [0,929; 0,933] |

Ojo con H8: juntando niveles de error tan distintos, **D3 también ordena** (0,931 pasaría el mismo criterio de ρ ≥ 0,9). H8 muestra que G sirve en todo el rango, pero no distingue G de D3; la prueba que sí los distingue es H7 y la columna "dentro": dentro de cada predictor, D3 ordena al revés (ρ negativo en los cinco) y G ordena bien (0,92–1,00).

Fuera de distribución, sin pasa/falla: ρ(G, D4) = 1,000 en `r2ood5` y `r2ood6` para ambas semillas; allí D3 también ordena (0,998–0,999), porque el error de P2 (mediana 4–6 %, rango 2–17 %) varía mucho más que el normalizador.

## Debilidad 2: falsos positivos de D2 fuera de distribución

| Controles exactos (P0 + P0f32), pasos marcados | `r2test` | `r2ood5` (k₀ = 5) | `r2ood6` (k₀ = 6) |
| --- | --- | --- | --- |
| D2 de la ronda 1 (trapecio, τ = 3,31e-3) | 0 / 800 | **40 / 400** | **160 / 400** |
| D2′ = D2p (Hermite menos su corrección, τ = 1,19e-6) | 0 / 800 | **0 / 400** | **0 / 400** |

D2 repite la falla de la ronda 1 con trayectorias nuevas: en k₀ = 5 marca el paso 0 de las 20 trayectorias (4,54e-3–4,78e-3, igual que en la ronda 1), y en k₀ = 6 los pasos 0 a 3 de las 20 (80 por predictor, 3,79e-3–1,14e-2). D2p no marca ninguno; su máximo sobre los controles es negativo en los tres splits (−9,3e-5, −5,7e-4, −8,8e-4).

**Evidencia de que esas 200 marcas de D2 son error de cuadratura** (`round2/tools/fp_diagnostic.py`, salida `round2/results/fp_diagnostic.json`, hecho en el Mac después de ver los datos, sin tocar nada de lo prerregistrado): para los 100 pasos de P0 marcados por D2 o por G, el balance del solver exacto se recalcula con subintervalos más finos. Al partir h a la mitad, el residuo del trapecio cae entre 3,95 y 3,98 veces (orden 2), y el de Hermite (D2h) entre 15,4 y 15,8 veces, igual que G (15,8–15,9): orden 4. Las marcas de P0f32 caen en los mismos 100 pasos, con D2 igual al de P0 hasta 1,6e-7 relativo y G hasta 1,5e-5; los valores son idénticos en las tres máquinas.

**Sensibilidad de D2p** (exploratorio): P3b sigue marcado por magnitud en 400/400 (H6), y también en todo `r2ood5` y `r2ood6`. Además D2p ve errores de energía que D2 no veía: marca P2 semilla 0 en 360/400 pasos de `r2test` y semilla 1 en 323/400, donde D2 marcaba 0. El costo, dicho de antemano: un error de energía más chico que la propia corrección de cuadratura del paso no se ve.

**G como alarma no es transferible** (exploratorio, ya previsto en el piloto): con su umbral τ_G = 7,82e-5 marca P0 y P0f32 en el paso 0 de las 20 trayectorias de `r2ood6` (máximo 1,47e-4), por el mismo motivo de cuadratura. G se prerregistró como medidor, no como chequeo, y el depurador de la ronda 2 (D1, D2p, D3) no lo usa para marcar.

## Ledgers

- `round2/ledgers/discrepancies.jsonl`: **0 entradas** (todo paso, predictor, split y marca D1, D2, D3, D2p, D2p_mag, G, any, any2, en las tres máquinas).
- `round2/ledgers/false_positives.jsonl`: **720 entradas, ninguna de un chequeo del depurador de la ronda 2.** 600 son del D2 viejo (por máquina: 40 en `r2ood5`, 160 en `r2ood6`) y 120 de G, que no es chequeo (40 por máquina, `r2ood6`). En el archivo están todas `open`, como pide el diseño. **Explicadas a mano por la evidencia de cuadratura de arriba: 720 explicadas, 0 abiertas.** De D2p: 0. De D1 y D3: 0.
- Fuera de D2 y G, **no hubo marcas sobre los controles**: D1 y D3 tampoco marcaron P0/P0f32 en ningún split, incluido k₀ = 6 (D3 máximo 2,49e-2 contra τ 8,35e-2).

## Reproducibilidad entre máquinas

| | WAR | GUERRA |
| --- | --- | --- |
| Splits de la ronda 2 regenerados desde las semillas, bit-idénticos al Mac | 0 / 80 | 0 / 80 |
| Diferencia absoluta máxima contra los archivos del Mac | 6,7e-16 | 6,7e-16 |
| Tiempo del depurador (todos los predictores y splits) | 1.154 s | 3.190 s (Mac: 585 s) |
| `tests/test_checks.py` y `round2/test_checks2.py` | pasan | pasan |

Como en la ronda 1, ningún archivo regenerado en Windows fue bit-idéntico; los del Mac son los canónicos y las dos máquinas corrieron el depurador sobre ellos. La mayor diferencia entre máquinas en cualquier estadístico fue 4,4e-16 (D3), 2,2e-16 (D3p) y 7e-18 (G); D2, D2h, D2p, D4, E(u₀) y E(u₁) salieron bit-idénticos. numpy 1.26.4 en las tres; Python 3.9.6 (Mac), 3.12.10 (WAR, torch 2.7.0+cu128), 3.12.3 (GUERRA, torch 2.6.0+cu124).

Transferencias (`round2/logs/transfers.tsv`, 1.511 filas, SHA-256 verificado en ambos extremos):

| Dirección | Archivos | Bytes | Reintentos | Fallidos |
| --- | --- | --- | --- | --- |
| Mac → WAR | 451 | 3,58 GB | 0 | 0 |
| Mac → GUERRA | 649 | 4,95 GB | 0 | 0 |
| WAR → Mac | 401 | 3,03 GB | 0 | 0 |
| GUERRA → Mac | 10 | 10 MB | 0 | 0 |

`C:\ADN\pd-exp-r2\` se borró en WAR (912 archivos, 7,3 GB) y GUERRA (739 archivos, 5,7 GB) después de traer y verificar todo, junto con los dos `.ps1` temporales de `C:\Users\Public` (`round2/logs/{war,guerra}/cleanup.log`). Espacio libre en C:: WAR 55,9 GiB al empezar y 55,9 GiB después de limpiar; GUERRA 85,8 GiB al empezar y 85,75 GiB después. No se tocó nada más en esas máquinas: las GPU estaban ociosas al empezar y la fábrica de vídeo siguió en pausa.

## Lo que no salió como se diseñó, o no se hizo

- La hipótesis de trabajo sobre la causa del mal ranking (la divergencia) resultó falsa ya en el piloto, y se confirmó con datos nuevos. Se arregló otra cosa (el normalizador); la propuesta proyectada se reporta como comparación y falla.
- H8 se cumple, pero no discrimina: D3 de la ronda 1 también lo habría pasado.
- El piloto usó las mismas redes P2 (semillas 0 y 1) que se evalúan aquí; los criterios de H7 y H8 se escribieron después de ver ρ ≈ 0,93/0,98 en la prueba de la ronda 1. Solo las trayectorias son nuevas.
- `round2/test_checks2.py` no estaba en el `.cmd` remoto; se corrió aparte en WAR y GUERRA (logs en `round2/logs/*/test_checks2.log`).
- Sin rollout (E2) en esta ronda; no se usó Taylor–Green (ya visto).

## Límites (de DESIGN, sin cambios)

Misma caja 32³, misma viscosidad, horizonte corto, una sola arquitectura. H7/H8 miden ranking contra D4 en predicciones de un paso. D2p cambia sensibilidad por robustez. Esto no dice nada sobre el problema del milenio ni sobre turbulencia real.

## Archivos

`round2/DESIGN.md` · `round2/thresholds.json` · `round2/MANIFEST.sha256` · `round2/results/{mac,war,guerra}/` · `round2/results/comparison.json` · `round2/results/fp_diagnostic.json` · `round2/ledgers/` · `round2/logs/` · `round2/pilot/` · `round2/verify.py`. Datos, predicciones y checkpoints (~4,6 GB) fuera de git, con hash en el manifiesto.
