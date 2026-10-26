# Ronda 5 · Kit para la prueba a ciegas

Este kit es para quien prepara las predicciones saboteadas. Nosotros no sabremos cuáles son buenas y cuáles son trampas hasta después de publicar los veredictos del depurador.

## Qué se prueba

En las rondas 1 a 4 inventamos nosotros mismos las trampas y el detective. La pregunta de esta ronda: ¿el depurador atrapa trampas que no diseñamos nosotros, sin marcar como malas las predicciones correctas?

## Las reglas del juego

El depurador revisa pares (u₀, u₁): un estado del fluido y la predicción del estado siguiente.

- Caja periódica 32³, viscosidad ν = 0.05, un paso Δ = 0.1 (10 subpasos de 0.01).
- Solver: `vendor/fluid_solver.py` (sha256 `87d3372e…`), vía `pd.data.advance`.
- Cada estado es un arreglo float64 de forma `(3, 32, 32, 32)`, como cada fila de `data/*/NNN.npy`.

**Correcto** significa que u₁ es la salida exacta del solver a partir de u₀, en float64 o redondeada a float32. **Trampa** es cualquier otra cosa, de cualquier tipo y tamaño: energía de más o de menos, fluido que se comprime, fase corrida, viscosidad o paso de tiempo equivocados, ruido, suavizado, una red entrenada, algo pensado para engañar al depurador… Se vale leer el código del depurador y apuntar justo debajo de sus umbrales.

## Paso a paso

1. **Elegir condiciones iniciales.** Semillas propias y secretas, mayores que 10000 (las rondas 1–4 usaron rangos menores), y la escala k₀ que se quiera, de 2 a 6. Por ejemplo:

   ```python
   from pd import flow
   from pd.initial import random_field
   from pd.data import advance
   s = flow()
   u0 = random_field(s, seed, k0)
   for _ in range(pasos_previos):
       u0 = advance(s, u0)
   exacto = advance(s, u0)
   ```

2. **Armar al menos 100 pares** y guardar cada uno como `pares/<id>.npz` con `np.savez(ruta, u0=u0, u1=u1)`. Los `<id>` deben ser aleatorios (por ejemplo `secrets.token_hex(4)`), sin relación con la etiqueta ni con el orden. La proporción de correctos y trampas es libre y secreta.

3. **Escribir `etiquetas.json`**, que se queda en tu máquina:

   ```json
   {"sal": "<32 caracteres hex aleatorios>",
    "pares": {"<id>": {"etiqueta": "correcto" | "trampa", "tipo": "texto libre", "magnitud": 0.0}}}
   ```

   `magnitud` = ‖u₁ − exacto‖ / ‖exacto‖, que es 0 para los correctos.

4. **Compromiso.** Calcular `shasum -a 256 etiquetas.json` y mandarme **solo ese hash** por correo o WhatsApp, antes de entregar nada más. Al recibirlo lo subo a este repositorio en `round5/compromiso.txt`, y GitHub le pone la hora antes de que lleguen los pares. Tu mensaje original sirve de respaldo. Así no se pueden cambiar las etiquetas después.

5. **Entrega.** Mandar la carpeta `pares/` junto con su lista de hashes (`shasum -a 256 pares/*.npz > pares.sha256`).

6. **Nosotros:** prerregistramos y subimos a GitHub, con hora, la regla de decisión y los umbrales congelados antes de abrir los pares. Luego corremos el depurador y subimos los veredictos.

7. **Revelación.** Una vez publicados los veredictos, nos mandas `etiquetas.json`. Comprobamos que su hash coincide con el del paso 4 y publicamos la tabla de aciertos, falsas alarmas y trampas no detectadas, por tipo y por magnitud.

## Lo que se va a reportar

- Falsas alarmas sobre los pares correctos (lo esperado es 0).
- Trampas detectadas, por tipo y por tamaño, incluidas las que no vio: el depurador tiene un piso de detección medido en la ronda 3, y lo que quede por debajo se reporta como no detectado, no se esconde.
- Todo con el mismo formato y la misma trazabilidad de las rondas 1–4: hashes, logs sin editar y las tres máquinas.
