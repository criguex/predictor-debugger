# Resultados · Ronda 4 · Transporte del error a lo largo del rollout

Corrida el 2026-10-25 (UTC) bajo `round4/DESIGN.md`, sin enmiendas. Las rondas 1–3 no se tocaron y siguen verificando en las tres máquinas: **EEC9-09E0-F77D**, **D506-F58F-3838** y **6319-537B-7167**.

## Orden y tiempos

| Paso | Commit | Hora (UTC) |
| --- | --- | --- |
| Piloto sobre datos ya vistos (`r3roll` de la ronda 3, 5.600 pasos) | incluido en el prerregistro | 13:10–14:20 |
| **Prerregistro** `round4/DESIGN.md` + código | `5d1925b` (GitHub privado, rama `ronda-4`) | **14:20:58** |
| Umbrales desde validación | `4cc1d06` | 14:26:04 |
| **Primer dato de evaluación** (generación de `r4test`, `r4ood5`, `r4ood6`, `r4roll`) | — | **14:26:06**, terminó 14:31:23 |
| Inferencia y rollouts de P2 en WAR | `f416411` | 14:35–14:52 |
| Corrida del depurador en el Mac (`--jobs 5`) | `6d69535` | 14:53–16:02 |
| Recomputación completa en el Mac (`verify.py --jobs 5`) | | RECOMP |
| Corridas en WAR y GUERRA | `REMOTE_COMMIT` | REMOTE_TIMES |
| Ledgers, verificación de las rondas 1–3 en remoto, limpieza | | CLEAN_TIME |

Los criterios H17–H20 los fijó el autor antes del piloto; el piloto solo eligió la reconstrucción primaria (`fp3`, ya elegida en una prueba de cinco pasos sobre `r3roll` antes del piloto completo). Tiempos de cada etapa en `round4/logs/mac/timeline.log` y `round4/logs/mac/orchestration.log`.

## Hipótesis prerregistradas (datos nuevos)

`r4test` = semillas 4000–4039 (k₀ = 3, 400 pasos por predictor); `r4ood5` = 4100–4119 (k₀ = 5) y `r4ood6` = 4200–4219 (k₀ = 6), 200 pasos cada uno; `r4roll` = 4300–4339 (k₀ = 3), rollouts de 20 pasos. MACHINES_SENTENCE

### H17–H20 (lo nuevo)

| Id | Criterio | Resultado | Veredicto |
| --- | --- | --- | --- |
| **H17** | Media sobre k = 1…20 del ρ entre trayectorias de Ê_k contra D4_k ≥ 0,8, IC inf. ≥ 0,6 y ρ₂₀ ≥ 0,7, en las cuatro redes | P2s0 0,992 [0,981; 0,995], ρ₂₀ 0,984 · P2s1 0,989 [0,973; 0,992], 0,977 · P2ge4 0,987 [0,968; 0,992], 0,974 · P2gbest 0,997 [0,991; 0,997], 0,996 | cumple |
| **H17-D** | Δρ = ρ(Ê) − ρ(X) ≥ 0,1 con IC pareado inf. > 0, contra X = ΣG y X = ΣD3, cada red | ver tabla siguiente: 8/8 celdas cumplen | **H17 PASA** (discrimina) |
| **H18** | Mediana de Ê_k/D4_k en [1/1,5; 1,5] en cada paso y red | P2s0 1,001–1,003 · P2s1 0,983–1,002 · P2ge4 0,999–1,003 · P2gbest 1,004–1,016 | **pasa** |
| **H19** | 0 alarmas Ê en los 80 rollouts de P0/P0f32; 0 falsos positivos nuevos de cualquier chequeo; P1 a tiempo ≥ 95 % | 0/80 alarmas; 0 nuevos (316 marcas viejas, todas con su explicación de la ronda 3, abajo); P1 40/40 | **pasa** |
| **H20** | Alarma Ê ≥ 5 % a tiempo ≥ 0,9 con IC inf. ≥ 0,8 y prematuras ≤ 0,1, sobre los 160 rollouts | 158/160 = 0,9875 [0,969; 1,00]; prematuras 0/160 [0; 0]. Referencia A (ronda 3): 160/160, 0 prematuras | **pasa** |

**Δρ por red (IC95 pareado, mismas trayectorias remuestreadas para las tres series):**

| Red | ρ medio Ê | ρ medio ΣG (A) | Δρ Ê − ΣG | ρ medio ΣD3 (C) | Δρ Ê − ΣD3 |
| --- | --- | --- | --- | --- | --- |
| P2s0 | 0,992 | 0,833 [0,696; 0,905] | **+0,160 [+0,086; +0,292]** | 0,708 [0,513; 0,830] | **+0,284 [+0,162; +0,475]** |
| P2s1 | 0,989 | 0,868 [0,764; 0,921] | **+0,121 [+0,067; +0,218]** | 0,829 [0,703; 0,892] | **+0,160 [+0,097; +0,276]** |
| P2ge4 | 0,987 | 0,840 [0,728; 0,902] | **+0,147 [+0,082; +0,254]** | 0,538 [0,278; 0,727] | **+0,448 [+0,258; +0,701]** |
| P2gbest | 0,997 | 0,805 [0,669; 0,884] | **+0,191 [+0,110; +0,325]** | 0,798 [0,663; 0,873] | **+0,198 [+0,123; +0,330]** |

La celda más justa es P2s1 contra ΣG: +0,121 con extremo inferior 0,067 (el criterio pedía ≥ 0,1 en el punto y > 0 en el extremo inferior).

**Curva ρ_k (k = 1 / 5 / 10 / 20):**

| Red | Ê (`fp3`) | ΣG (A) | S (ΣG ponderada por Lyapunov) | ΣD3 (C) | oráculo Ê* |
| --- | --- | --- | --- | --- | --- |
| P2s0 | 1,000 / 0,995 / 0,993 / 0,984 | 0,996 / 0,880 / 0,807 / 0,754 | 0,996 / 0,872 / 0,775 / 0,662 | 0,729 / 0,737 / 0,655 / 0,693 | 1,000 / 0,996 / 0,993 / 0,984 |
| P2s1 | 0,998 / 0,998 / 0,992 / 0,977 | 0,996 / 0,923 / 0,808 / 0,826 | 0,996 / 0,883 / 0,703 / 0,680 | 0,794 / 0,847 / 0,845 / 0,810 | 0,998 / 0,998 / 0,991 / 0,977 |
| P2ge4 | 1,000 / 0,995 / 0,990 / 0,974 | 0,993 / 0,915 / 0,833 / 0,747 | 0,993 / 0,895 / 0,805 / 0,645 | 0,658 / 0,537 / 0,509 / 0,532 | 0,999 / 0,995 / 0,990 / 0,974 |
| P2gbest | 1,000 / 0,999 / 0,999 / 0,996 | 0,992 / 0,934 / 0,792 / 0,676 | 0,992 / 0,919 / 0,764 / 0,635 | 0,797 / 0,840 / 0,780 / 0,786 | 0,999 / 0,999 / 0,999 / 0,996 |

ρ medio de S: 0,800 · 0,773 · 0,798 · 0,786 (peor que ΣG en tres de cuatro redes).

### Bloque de cordura (ronda 3 replicada con semillas nuevas)

| Id | Resultado | Veredicto |
| --- | --- | --- |
| H1 / H1b | P0 0/400 · P0f32 0/400 | pasa |
| H2 / H3 / H4 | 400/400 · 400/400 · 400/400 | pasa |
| H5 | D2′ 0/1.600 pasos de control | pasa |
| H6 | 400/400 | pasa |
| H7 | G: 0,936 [0,926; 0,945] · 0,975 [0,970; 0,978]; comparador D3: −0,167 [−0,248; −0,098] · +0,062 [−0,016; 0,130] (falla) | **pasa** |
| H9 | D2″ 0/1.600 | pasa |
| H10 | 6/6 celdas: D2″ 3,2e-6 / 1e-4 / 3,2e-4 contra D2′ 3,2e-4 / 1e-2 / 1e-2 (`r4test` / `r4ood5` / `r4ood6`, ambos signos) | pasa |
| H10b | 400/400 | pasa |
| H11 | G′ 0/1.600 | pasa |
| H12 | 2.400/2.400 | pasa |
| H13 | G′: 0,934 [0,924; 0,943] · 0,974 [0,969; 0,977]; D3 falla | **pasa** |

Pisos de momento (D3 / G / G6 / G′): `r4test` 1e-2 / 1e-4 / 1e-6 / 1e-5; `r4ood5` ninguno / 1e-4 / 1e-6 / 1e-4; `r4ood6` ninguno / 1e-4 / 1e-6 / 3,2e-4: los mismos de la ronda 3.

FINGERPRINT_PARAGRAPH

## Qué dice y qué no

- **El fallo de H14 era la suma de normas, no la estimación local.** Llevar cada defecto con su dirección por el mapa tangente (Ê) ordena las trayectorias con ρ ≥ 0,97 en el paso 20, donde ΣG cae a 0,68–0,83. Hasta el residuo sin invertir (`r6`, 14–17 % de error en el defecto) transportado ordena 0,987–0,995; el oráculo con el defecto exacto no mejora a Ê en nada medible (Δρ entre −0,001 y +0,001).
- **No es amplificación caótica.** La mediana del factor de crecimiento de la dirección más inestable (λ_k, por iteración de potencia hacia adelante) va de 0,949 en el paso 1 a 0,973 en el paso 20, igual en las cuatro redes: el mapa tangente contrae en este régimen viscoso (exponente de tiempo finito −0,53 a −0,35). Por eso ponderar ΣG por Lyapunov (S) no ayuda: sabe cuánto decae la dirección más lenta, no cuánto cancela o rota cada error. Lo que el transporte capta es la geometría (direcciones que se compensan y decaen distinto), no un crecimiento.
- **Ê está calibrado al 2 %** (H18), así que como alarma al mismo nivel L = 5 % suena en el mismo paso del cruce en 145 de 160 rollouts, un paso antes en 13 y un paso tarde en 2 (P2s1). A, que sobrestima 1,1–1,8 veces, avisa 0–10 pasos antes (mediana 1 en P2ge4, 3 en P2s1, 5–6 en P2s0, 8 en P2gbest). H20 pasa por margen pequeño: una alarma calibrada no tiene colchón; si se quisiera anticipación habría que poner el umbral por debajo de L, y eso no se cambió.
- **Lo que cuesta.** Ê usa el tangente de un paso del solver por cada paso del rollout (≈ 3 veces el costo del paso por cada vector transportado) y el propio estado de la red. No usa la trayectoria de referencia, pero un depurador que puede correr DΦ también puede correr Φ y obtener el defecto exacto: el resultado dice que el residuo de la ronda 3 basta para reconstruir el error (defecto con 1 % de error tras tres iteraciones de punto fijo), no que exista un chequeo barato que lo haga.
- **Lo que sigue sin probarse.** Horizonte 20, solo k₀ = 3, régimen contractivo, redes entrenadas para un paso. En un régimen caótico (ν más pequeño) la linealización alrededor del estado de la red (error de linealización ‖ê* − e‖/‖e‖ = 1,3–3,3 % en el paso 20 aquí) puede dejar de bastar.

## Diagnóstico del defecto d̂ (exploratorio)

Mediana de ‖d̂_k − d_k‖/‖d_k‖ en k = 1 / 5 / 10 / 20, d_k = û_k − Φ(û_{k−1}) exacto:

| Red | `fp3` (primaria) | `r6` (sin invertir) | `r6u` (inicio sin proyectar) | linealización ‖ê* − e‖/‖e‖ |
| --- | --- | --- | --- | --- |
| P2s0 | 1,4 / 1,4 / 1,1 / 0,5 % | 16 / 17 / 15 / 7,7 % | 16 / 57 / 54 / 45 % | 0 / 0,44 / 0,97 / 1,6 % |
| P2s1 | 1,3 / 1,3 / 1,0 / 0,3 % | 15 / 16 / 13 / 5,7 % | 15 / 49 / 45 / 36 % | 0 / 0,38 / 0,91 / 2,0 % |
| P2ge4 | 1,2 / 1,0 / 0,8 / 0,4 % | 14 / 14 / 12 / 6,5 % | 14 / 53 / 51 / 50 % | 0 / 0,74 / 1,8 / 3,3 % |
| P2gbest | 1,4 / 1,4 / 1,1 / 0,4 % | 16 / 17 / 15 / 7,1 % | 16 / 61 / 60 / 45 % | 0 / 0,31 / 0,69 / 1,3 % |

Proyectar el inicio importa para el defecto (la parte no solenoidal de la salida anterior de la red entra dos veces al residuo literal), casi nada para el orden. La mediana de Ê/D4 de las variantes sin invertir va de 0,997 a 1,095: la inversión del jacobiano del trapecio es lo que deja a Ê en 1 %.

## Ledgers

LEDGER_SECTION

## Reproducibilidad entre máquinas

REPRO_SECTION

## Lo que no salió como se diseñó, o no se hizo

NOTDONE_SECTION

## Límites (de DESIGN, sin cambios)

Misma caja 32³, viscosidad, Δ, arquitectura y redes. Horizonte de 20 pasos, solo k₀ = 3. Transporte linealizado en el estado de la red; defecto con el jacobiano del trapecio, sin los términos O(Δ²). Ê no es barato: usa el tangente del solver. Nada de esto dice algo sobre el problema del milenio ni sobre turbulencia real.

## Archivos

`round4/DESIGN.md` · `round4/thresholds.json` · `round4/MANIFEST.sha256` · `round4/results/{mac,war,guerra}/` (`onestep.json`, `rollout.json`, `sweep.json`, `verdicts.json`, `environment.json`) · `round4/results/comparison.json` · `round4/ledgers/` · `round4/logs/` · `round4/pilot/` · `round4/verify.py`. Datos y predicciones (~4,9 GB) fuera de git, con hash en el manifiesto.
