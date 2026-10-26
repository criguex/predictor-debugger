# predictor-debugger

Soy Cristian Guerra, ingeniero de QA en Medellín. Este repositorio contiene un depurador que comprueba si las predicciones de una red neuronal FNO para un fluido 3D respetan la incompresibilidad, el balance de energía y la ecuación de evolución. Lo evalúo con hipótesis y umbrales prerregistrados, y reporto también los controles que no pasan. Las rondas 1 a 4 documentan esas pruebas y sus resultados.

## Cómo trabajo

Antes de generar los datos de prueba, dejo las hipótesis y los umbrales en un commit. Incluyo comparadores que deberían fallar, para comprobar si las pruebas distinguen los casos previstos. Ejecuto la verificación en tres máquinas: Mac, WAR y GUERRA. Comparo los veredictos y la huella de cada ronda. Mantengo ledgers de discrepancias y de falsos positivos.

## Rondas

| Ronda | Qué probé | Resultado principal | Huella |
| --- | --- | --- | --- |
| 1 | Comprobaciones de incompresibilidad, energía y evolución en controles exactos, predicciones saboteadas y FNO. | Los controles se separaron y las tres máquinas coincidieron. D3 detectó la persistencia, pero no ordenó qué pasos de la FNO tenían más error. El balance de energía D2 dio falsos positivos fuera de distribución. | `EEC9-09E0-F77D` |
| 2 | Un medidor de error G, una comprobación de energía más sensible y predicciones con varios niveles de error. | G ordenó el error dentro de cada predictor y el nuevo balance evitó las marcas del control exacto. H8 pasó al juntar niveles de error, pero no distinguió G de D3: D3 también ordenó ese conjunto. | `D506-F58F-3838` |
| 3 | Pisos de detección, una alarma G′ y rollouts de 20 pasos. | H14 **FALLÓ**: la suma de G no ordenó suficientemente bien el error acumulado entre trayectorias, y el comparador ΣD3 cumplió el criterio en tres de cuatro redes. | `6319-537B-7167` |
| 4 | Transporte de los defectos de predicción a lo largo de rollouts de 20 pasos. | H17 pasó en las cuatro redes: transportar la dirección del defecto ordenó mejor el error de rollout que sumar normas locales. La huella se repitió en las tres máquinas. | `681D-143B-64A3` |

## Reproducir

Todo se corre desde la raíz del repositorio con [uv](https://docs.astral.sh/uv/); `uv run --locked` usa Python 3.9 y numpy 1.26.4, fijados en `uv.lock`. Hay tres niveles, del más barato al más caro. Además de mis tres máquinas (el Mac, y WAR y GUERRA con Windows), uso un cuarto sistema: Linux, en el CI de GitHub (`ubuntu-24.04`) y en WSL2 (Ubuntu 24.04) sobre GUERRA.

### (a) Veredictos guardados: minutos, sin datos

Reaplico los umbrales prerregistrados a las estadísticas guardadas de cada máquina y recalculo la huella. No hace falta descargar nada:

```sh
uv run --locked verify.py --saved mac
uv run --locked round2/verify.py --saved mac
uv run --locked round3/verify.py --saved mac
uv run --locked round4/verify.py --saved mac
```

Cambia `mac` por `war` o `guerra` para ver las otras máquinas, o por `linux` en la ronda 1. Cada comando debe imprimir `verdicts equal ...: True` y la huella de la tabla de arriba. En mi Mac, las cuatro rondas seguidas tardaron 242 s (unos 4 min) el 25 de octubre. El workflow `verify` hace esto en cada push para las tres máquinas y corre las pruebas de las comprobaciones.

### (b) Recalcular desde los datos y las predicciones publicadas

Los datos, las predicciones y los checkpoints no están en git. Los publiqué como un tarball por carpeta en el release [`data-v1`](https://github.com/criguex/predictor-debugger/releases/tag/data-v1), junto con un `SHA256SUMS`. `tools/fetch_data.py` (solo biblioteca estándar) descarga lo que pidas, comprueba cada tar contra `SHA256SUMS` antes de extraerlo, rechaza rutas absolutas, `..` y enlaces, borra el tar al terminar y compara lo extraído con el `MANIFEST.sha256` de la ronda. Si algo falla, imprime la lista y sale con un código distinto de 0.

```sh
uv run --locked tools/fetch_data.py --rounds r1 --what data preds
uv run --locked verify.py

uv run --locked tools/fetch_data.py --rounds r2 r3 r4 --what data preds
uv run --locked round2/verify.py
uv run --locked round3/verify.py --jobs 2
uv run --locked round4/verify.py --jobs 4
```

Las rondas 2 a 4 también leen la validación de la ronda 1 (`data/val`), así que necesitan los datos de la ronda 1. Cada ronda ocupa unos 5 GB y las cuatro, unos 20 GB. Sin argumentos, `fetch_data.py` baja todo, incluidos los checkpoints. Cada `verify.py` compara sus veredictos con los guardados del Mac e imprime la huella, que debe ser la misma.

Lo que tardó el recálculo del depurador en cada máquina:

| Ronda | Mac | WAR | GUERRA | Fuente |
| --- | --- | --- | --- | --- |
| 1 | 126 s | 257 s | 704 s | [RESULTS.md](RESULTS.md), *Reproducibility across machines* |
| 2 | 585 s | 1.154 s | 3.190 s | [round2/RESULTS.md](round2/RESULTS.md), *Reproducibilidad entre máquinas* |
| 3 | 1.956 s (2 procesos) | 3.436 s (6) | 9.457 s (6) | [round3/RESULTS.md](round3/RESULTS.md), *Reproducibilidad entre máquinas* |
| 4 | 3.966 s ≈ 1,1 h (5 procesos) | 15.734 s ≈ 4,4 h (6) | 31.223 s ≈ 8,7 h (8) | [round4/RESULTS.md](round4/RESULTS.md), *Reproducibilidad entre máquinas* |

En Linux (WSL2 en GUERRA), la ronda 1 completa tardó unos 7 min: 2 min 52 s de recálculo y 4 min 8 s de regenerar val, test y OOD ([logs/linux/run.log](logs/linux/run.log)). Dio los mismos veredictos y la huella `EEC9-09E0-F77D` ([logs/linux/verify_saved.log](logs/linux/verify_saved.log)). El workflow `reproduce` (manual o con un tag `v*`) hace este nivel en un runner de GitHub para las rondas 1 y 2. En su primera corrida ([run 40267731741](https://github.com/criguex/predictor-debugger/actions/runs/40267731741)), con la descarga incluida, el job de la ronda 1 tardó 6 min 33 s y el de la ronda 2, 17 min 47 s; los dos dieron los mismos veredictos y las huellas `EEC9-09E0-F77D` y `D506-F58F-3838`.

### (c) Regenerar los datos y reentrenar

Los datos se regeneran desde las semillas con el solver de `vendor/`, y cada `verify.py` compara el resultado con su manifiesto:

```sh
uv run --locked verify.py --regenerate /ruta/regen --splits train val test ood
uv run --locked round2/verify.py --regenerate /ruta/regen2
uv run --locked round3/verify.py --regenerate /ruta/regen3
uv run --locked round4/verify.py --regenerate /ruta/regen4
```

Este nivel no es bit-idéntico entre sistemas. Ningún archivo regenerado en WAR, GUERRA o Linux salió igual bit a bit al del Mac. La mayor diferencia absoluta fue 8,9e-16 (WAR, ronda 1, [RESULTS.md](RESULTS.md)); en las rondas 2 a 4 estuvo entre 6,7e-16 y 7,8e-16. Por eso los archivos del Mac son los canónicos. Los veredictos de las cuatro máquinas se calcularon sobre ellos y coinciden, con la misma huella. Entre máquinas, ningún estadístico difirió en más de 4,4e-16 en las rondas 1 a 3; en la 4, el máximo fue 5,7e-14, en un paso de P0f32. En la ronda 1, regenerar el split de entrenamiento tardó 311 s en el Mac y los otros tres, 160 s ([logs/mac/data_generation.log](logs/mac/data_generation.log)); en WAR, 732 s y 371 s ([logs/war/regeneration.log](logs/war/regeneration.log)).

Reentrenar la FNO requiere una GPU con CUDA y el grupo `train` (torch 2.7.0): `uv run --locked --group train python -m pd.train --seed 0 --log train_s0.json`, y lo mismo con `--seed 1`. Después, `python -m pd.predictors` construye P3a y P3b. Las redes de la ronda 2 salen de `python -m round2.predict checkpoints` y `python -m round2.predict graded`, y las predicciones de las rondas 3 y 4, de `round3/predict.py` y `round4/predict.py`. Entrené una sola vez, en WAR (RTX 5070); las dos semillas de la ronda 1 tardaron 102,6 s y 136,8 s ([RESULTS.md](RESULTS.md)). No busqué pesos bit-idénticos entre dispositivos, así que reentrenar da redes nuevas: es evidencia nueva, no una copia de mis bits.

## Ronda 5: prueba a ciegas

Invito a quien quiera participar a preparar pares de estados correctos y saboteados siguiendo [round5/KIT.md](round5/KIT.md). El kit explica cómo comprometer las etiquetas antes de entregar los pares.

## Límites

El alcance es una caja periódica de 32³, campos iniciales suaves, un horizonte corto, una arquitectura y ningún forzamiento. Esto no dice nada sobre el problema de Clay, la prueba de OpenAI ni la turbulencia real. Los datos y predicciones ocupan alrededor de 20 GB y no están en git; están en el release `data-v1` y el repositorio conserva sus hashes. Las tres máquinas son mías, así que esto no es una reproducción independiente. Escribí y ejecuté este trabajo con ayuda de asistentes de IA, bajo mi dirección.

Mi proyecto hermano está en [scientific-qa-evidence](https://criguex.github.io/scientific-qa-evidence/).

## In English

I am Cristian Guerra, a QA engineer in Medellín. This repository contains a physics debugger for 3D fluid predictions from a Fourier neural operator. I test it through preregistered rounds and report failures as well as successes. The results are limited to the setup described here, and the three machines are mine. To reproduce: `verify.py --saved` re-checks the saved verdicts in minutes without data; `tools/fetch_data.py` downloads the data and predictions (about 5 GB per round) from the `data-v1` release and checks them against the manifests, and then each round's `verify.py` recomputes everything; regenerating the data and retraining needs a GPU and is not bit-identical across systems (differences up to 8.9e-16), while the verdicts and fingerprints match.
