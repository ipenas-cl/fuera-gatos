# Techo: cámara, torretas y agua autónoma

El techo compartido es la autopista de los gatos. Una cámara arriba los ve
antes de que bajen, y dos torretas de hilo fino los interceptan en tu tramo.
Como subir una manguera desde la matriz no es práctico, el agua vive arriba en
un estanque con bomba y sensor de nivel.

## Qué va arriba

```
                 cumbrera
   ═══════════╦═══════════════════════════╦═══════════
   vecino izq ║  [torreta A]   [cámara 3]  [torreta B] ║ vecino der
              ║        ▲   estanque + bomba   ▲       ║
   medianera  ║        └─── caja estanca ─────┘       ║  medianera
```

| Pieza | Notas |
|---|---|
| Cámara NoIR + iluminador IR | En la cumbrera o en un mástil corto, mirando a lo largo del techo. Detector a 640 px (`imgsz`) porque el gato queda lejos |
| 2 torretas (servos MG996R + PCA9685) | Una por extremo del tramo. Límites de pan en las medianeras; tilt que obligue a apuntar hacia abajo, a tu vertiente |
| 2 bombas de diafragma 12 V (o una con válvula de 2 vías) | 3 L/min nominal; con boquilla de 1.5 mm rinden 1.5-2 L/min |
| Estanque 20-30 L opaco | Bidón de agua de 20 L o estanque plano de 25 L. Opaco para que no crezcan algas |
| Flotador (interruptor de nivel) | En el estanque, cableado a un GPIO. Vacío = torretas bloqueadas + aviso |
| Filtro de malla en la salida | Protege bomba y boquilla |
| Caja estanca IP65 | Pi, relés, PCA9685 y fuente. El estanque afuera, a la sombra |

## Cuánta agua se usa

Una activación de nivel 1 dura 4 s en ráfagas de 0.6 s con 0.3 s de pausa: unos
2.7 s de bomba, que a 2 L/min son **0.1 L**. Con las dos torretas en nivel 2
salen unos 0.2 L. Diez activaciones por día son entre 1 y 2 L.

| Estanque | Autonomía con 10 activaciones/día |
|---|---|
| 20 L | 2 a 3 semanas |
| 30 L | 3 a 5 semanas |
| 60 L (dos bidones) | 1 a 2 meses |

Cuando el flotador marca vacío, el sistema deja de usar agua (la bomba no
trabaja en seco), sigue con luz, y manda un aviso por Telegram una sola vez.

## Cómo rellenar sin subir manguera

1. **Lluvia desde la canaleta** (la mejor opción): un desvío de la bajada de
   agua con filtro de hojas y descarte de primeras aguas llena el estanque
   solo. En temporada de lluvias no hay que subir nunca. Poner un rebalse.
2. **Bidón de recambio**: cuando llega el aviso, subir un bidón de 20 L lleno
   y bajar el vacío. Con conexión rápida es un minuto de trabajo cada 2-4 semanas.
3. **Recarga automática desde abajo**: una segunda bomba en el suelo con una
   manguera fina de 6 mm fija por la pared, activada por otro flotador de
   "lleno". No está integrada en el software todavía; se puede resolver con un
   temporizador o un relé comandado por el flotador sin pasar por la Pi.

## Energía

Lo más simple y confiable es un **cable de 12 V desde abajo** (2 hilos de
1.5 mm²): la Pi consume unos 4 W continuos, la bomba 40 W pero solo segundos
al día. Con panel solar hace falta uno de 50 W y una batería de 12 V 20 Ah para
pasar el invierno; es más caro y más cosas que fallan.

Alternativa mixta: dejar la Pi abajo y subir solo una cámara IP por cable de
red (PoE) más el cable de 12 V para bombas y servos; los relés y el PCA9685
quedan arriba en la caja y se comandan por I2C largo (no recomendado, máximo
2-3 m) o por una segunda Pi Zero. En la práctica, una Pi por caja es lo que
menos problemas da.

## Seguridad y vecinos

* **Límites**: `limits.pan` en las medianeras y `limits.tilt` que impida un
  chorro casi horizontal. Un hilo a 100 psi recorre 6-8 m; apuntado hacia
  abajo cae en tu vertiente, apuntado al frente termina en el techo de al lado.
* **Zonas de vecinos con `deterrents: []`**: el sistema registra que un gato
  pasó por ahí (sirve para saber por dónde entran) pero no actúa.
* **Detección más exigente** arriba: confianza 0.55 y 4 detecciones antes de
  actuar. A esa distancia una paloma no debe disparar nada.
* **Peso**: 25 L son 25 kg. Apoyar el estanque sobre un muro medianero o
  junto a la cumbrera, nunca en el medio de una plancha.
* **Heladas**: en zonas con noches bajo cero, no llenar del todo y vaciar la
  bomba en invierno.
* **Mascotas ajenas**: un gato en el techo puede ser del vecino. Avisar qué
  hay instalado, y que solo es agua fría en tu tramo.

## Arranque

```bash
cp examples/config.techo.yaml config.techo.yaml
# calibrar cada torreta:
fuera-gatos aim -c config.techo.yaml --name torreta_a --pan 90 --tilt 45 --water 1
sudo systemctl enable --now fuera-gatos@techo
```
