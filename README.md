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

## Verificación

Desde la raíz, `uv run --locked` usa el entorno fijado por el proyecto. La verificación rápida reevalúa las estadísticas guardadas y no necesita los datos grandes:

```sh
uv run --locked verify.py --saved mac
uv run --locked round2/verify.py --saved mac
uv run --locked round3/verify.py --saved mac
uv run --locked round4/verify.py --saved mac
```

Para recalcular desde las predicciones guardadas, los comandos son `uv run --locked verify.py`, `uv run --locked round2/verify.py`, `uv run --locked round3/verify.py --jobs 2` y `uv run --locked round4/verify.py --jobs 4`. Requieren los datos y predicciones correspondientes. Los datos no están en git; sus hashes están en los manifiestos. El workflow también corre las pruebas de comprobaciones y verifica las huellas guardadas para `mac`, `war` y `guerra`.

## Ronda 5: prueba a ciegas

Invito a quien quiera participar a preparar pares de estados correctos y saboteados siguiendo [round5/KIT.md](round5/KIT.md). El kit explica cómo comprometer las etiquetas antes de entregar los pares.

## Límites

El alcance es una caja periódica de 32³, campos iniciales suaves, un horizonte corto, una arquitectura y ningún forzamiento. Esto no dice nada sobre el problema de Clay, la prueba de OpenAI ni la turbulencia real. Los datos y predicciones ocupan alrededor de 5 GB y no están en git; el repositorio conserva sus hashes. Las tres máquinas son mías, así que esto no es una reproducción independiente. Escribí y ejecuté este trabajo con ayuda de asistentes de IA, bajo mi dirección.

Mi proyecto hermano está en [scientific-qa-evidence](https://criguex.github.io/scientific-qa-evidence/).

## In English

I am Cristian Guerra, a QA engineer in Medellín. This repository contains a physics debugger for 3D fluid predictions from a Fourier neural operator. I test it through preregistered rounds and report failures as well as successes. The results are limited to the setup described here; the data are not included in git, and the three machines are mine.
