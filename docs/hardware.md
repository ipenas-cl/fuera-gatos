# Hardware y cableado

## Lista de materiales

| Cant. | Pieza | Notas |
|---|---|---|
| 1 | Raspberry Pi 4 (2 GB o más) o Pi 5 | Pi Zero 2 W solo con `backend: motion` |
| 1 | Tarjeta microSD 32 GB + fuente oficial | |
| 1 | Cámara Pi Module 3 **NoIR** (sin filtro IR) | Ve de noche con iluminador IR |
| 1 | Iluminador IR 850 nm de 12 V (o el del kit de cámara) | Invisible para el ojo humano, no molesta a nadie |
| 1 | Módulo de 4 relés 5 V con optoacoplador | Disparo por GPIO a 3.3 V ("low level trigger" es lo habitual: poner `active_high: false`) |
| 1 | **Torreta**: soporte pan/tilt para 2 servos (impreso en 3D o kit de cámara) | Sostiene la boquilla; ver sección Torreta |
| 2 | Servo MG996R o DS3218 (metálico, 15-20 kg·cm) | Los SG90 de plástico no aguantan el tirón de la manguera |
| 1 | Módulo PCA9685 (I2C, 16 canales PWM) | PWM por hardware, sin temblor; los servos van con fuente aparte de 5-6 V 3 A |
| 1 | Bomba de diafragma 12 V, 3-5 L/min, 60-100 psi (tipo casa rodante) | Chorro fino y largo con poco caudal; toma de un bidón de 20 L o de la red |
| 1 | Boquilla de chorro recto de 1.5-2 mm (o pistola de riego en modo "jet") | Alcance 5-8 m con la bomba |
| 1 | Electroválvula 12 V NC ½" (opcional) | Solo si en vez de bomba se usa la presión de la red |
| 1 | Aspersor de impacto pequeño (respaldo fijo) | Cubre la zona que la torreta no alcanza |
| 1 | Fuente 12 V 5 A | Bomba, válvula, reflector e iluminador |
| 1 | Reflector LED 12 V 10 W | Luz repentina |
| 1 | Parlante 3 W 4 Ω + amplificador PAM8403 | Conectar a la salida de audio de la Pi (jack o HAT I2S/USB) |
| 1 | Repelente ultrasónico comercial para gatos (a pilas o 12 V) | Se abre y se alimenta a través de un relé: así lo dispara la Pi y no queda encendido todo el día |
| 1 | Caja estanca IP65 con prensacables | La Pi y los relés adentro; la cámara con su domo |
| - | Cable, terminales, diodo 1N4007 para la válvula | El diodo en antiparalelo protege el relé |

Opcional:
* Sensor PIR HC-SR501 para despertar la detección y ahorrar CPU (no está integrado
  en el código todavía; el detector corre continuo a pocos fps y consume poco).
* Google Coral USB para YOLO a 30 fps; no hace falta para este uso.

## Cableado (numeración BCM)

```
GPIO17 ───> IN1 relé ───> reflector LED 12 V
GPIO27 ───> IN2 relé ───> bomba 12 V de la torreta  (+ diodo 1N4007 en antiparalelo)
GPIO5  ───> IN3 relé ───> electroválvula del aspersor fijo (+ diodo)
GPIO22 ───> IN4 relé ───> repelente ultrasónico (alimentación)
SDA/SCL (GPIO2/3) ──> PCA9685 ──> canal 0 servo pan, canal 1 servo tilt
                      PCA9685 V+ <── fuente 5-6 V 3 A (NO los 5 V de la Pi)
5 V / GND ─> VCC / GND del módulo de relés
Jack 3.5 mm / HAT audio ──> PAM8403 ──> parlante
```

Activar I2C con `sudo raspi-config` (Interface Options) e instalar `pip install smbus2`.

## Torreta: chorro fino que sigue al gato

La idea es poco caudal y mucha velocidad: una bomba de diafragma de 12 V con una
boquilla de 1.5-2 mm lanza un hilo de agua a 5-8 m gastando menos de un vaso por
ráfaga. Es lo que mejor funciona con gatos ya acostumbrados: no es el volumen lo
que los espanta sino el impacto sorpresivo que los persigue.

* **Montaje**: la boquilla va sobre el soporte pan/tilt, a 1.5-2 m de altura, con
  un tramo de manguera flexible de 6 mm para que los servos no carguen peso.
* **Ubicación**: idealmente junto a la cámara. Si la torreta y la cámara están en
  el mismo punto, la calibración píxel-grado es casi lineal y muy precisa.
* **Calibración** (dos puntos por eje):
  1. `fuera-gatos aim -c config.yaml --pan 60 --tilt 50 --water 1` y mirar en la
     captura (`data/snapshots`, o `--simulate` off con la cámara en vivo) en qué
     píxel cae el chorro.
  2. Repetir con `--pan 120` y con `--tilt 70`.
  3. Anotar los pares `[píxel, grado]` en `calibration.pan` y `calibration.tilt`.
* **Límites** (`limits.pan`, `limits.tilt`): ángulos fuera de los cuales la torreta
  no gira nunca. Ponerlos de modo que el chorro no pueda salir del terreno ni
  llegar a la vereda, la calle o el patio del vecino, aunque el detector se
  equivoque.
* **Ráfagas** (`pulse_on_s` / `pulse_off_s`): 0.6 s de agua y 0.3 s de pausa
  sorprenden más que un chorro continuo y usan la mitad de agua.
* **Anticipación** (`lead_s`): apunta unos 0.3 s por delante del gato según su
  velocidad; subir si el chorro llega tarde, bajar si se pasa.
* **Servos**: los de 5 V de plástico (SG90) no sirven. Usar MG996R o DS3218 con
  fuente propia. Con `driver: gpiozero` se conectan directo a pines PWM
  (`pan_pin`, `tilt_pin`) pero tiemblan; el PCA9685 es la opción recomendada.
* **Agua**: la bomba puede tomar de un bidón de 20 L (dura semanas con ráfagas
  de 4 s) o de la red con un regulador. En invierno vaciar el circuito.

* La fuente de 12 V comparte **GND** con la Pi.
* Los relés conmutan el positivo de 12 V de cada carga.
* Si el módulo de relés es "active low", poner `active_high: false` en cada
  disuasor de tipo `relay`; de lo contrario las cargas quedarían encendidas al arrancar.
* Alimentar la válvula solo a través del relé: si el sistema se cae, el relé se
  abre y el agua se corta. Además el software tiene `max_on_s` como segundo seguro.

## Instalación física

* Cámara a 1.5-2.5 m de altura mirando hacia abajo en diagonal, cubriendo la basura
  y el cantero en el mismo cuadro. Evitar que entre la vereda o la calle en las zonas
  configuradas.
* Aspersor apuntando hacia adentro del terreno y a baja presión. El objetivo es
  mojarle las patas y hacer ruido, no un chorro fuerte.
* Parlante bajo un alero, mirando al suelo.
* Probar cada salida con `fuera-gatos test-deterrents -c config.yaml --seconds 1`.

## Alternativas

* **ESP32-CAM + servidor**: la ESP32-CAM publica un stream RTSP/MJPEG y una PC o Pi
  corre `fuera-gatos` con `camera.source: rtsp`. Los relés pueden ir en la Pi o en
  otra ESP32 con un pequeño firmware que reciba comandos (no incluido).
* **Cámara IP existente**: cualquier cámara con RTSP funciona con `source: rtsp`.
* **Sin agua**: si no hay manguera cerca, luz + ultrasonido + bufido funcionan bien
  la mayoría de las veces. Basta con quitar `aspersor` de los niveles.
