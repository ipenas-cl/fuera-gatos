# Hardware y cableado

## Lista de materiales

| Cant. | Pieza | Notas |
|---|---|---|
| 1 | Raspberry Pi 4 (2 GB o más) o Pi 5 | Pi Zero 2 W solo con `backend: motion` |
| 1 | Tarjeta microSD 32 GB + fuente oficial | |
| 1 | Cámara Pi Module 3 **NoIR** (sin filtro IR) | Ve de noche con iluminador IR |
| 1 | Iluminador IR 850 nm de 12 V (o el del kit de cámara) | Invisible para el ojo humano, no molesta a nadie |
| 1 | Módulo de 4 relés 5 V con optoacoplador | Disparo por GPIO a 3.3 V ("low level trigger" es lo habitual: poner `active_high: false`) |
| 1 | Electroválvula 12 V normalmente cerrada, rosca ½" o ¾" | Se conecta en línea con la manguera del aspersor |
| 1 | Aspersor pequeño o boquilla de riego | Apuntar a la zona, no a la calle ni al vecino |
| 1 | Fuente 12 V 2 A | Para válvula, reflector e iluminador |
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
GPIO27 ───> IN2 relé ───> electroválvula 12 V  (+ diodo 1N4007 en antiparalelo)
GPIO22 ───> IN3 relé ───> repelente ultrasónico (alimentación)
5 V / GND ─> VCC / GND del módulo de relés
Jack 3.5 mm / HAT audio ──> PAM8403 ──> parlante
```

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
