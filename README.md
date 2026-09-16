# fuera-gatos

Sistema de detección de gatos con cámara que los **asusta sin lastimarlos** para que
dejen de usar el terreno como baño y de romper las bolsas de basura.

La idea es simple: una cámara vigila las zonas problemáticas (la basura, el cantero),
una red neuronal reconoce al gato, y el sistema responde con un susto corto y
proporcional: primero luz y un bufido grabado; si el gato insiste, un chorrito de agua
de pocos segundos. Los gatos aprenden rápido que ese lugar "es raro" y buscan otro.

```
 cámara ──> detector (YOLO o movimiento) ──> zonas ──> controlador ──> disuasores
                                                          │              ├─ luz (relé)
                                                          │              ├─ sonido (parlante)
                                                          │              ├─ ultrasonido (relé)
                                                          │              └─ aspersor (electroválvula)
                                                          └──> registro JSONL + captura + Telegram
```

## Principios: asustar, nunca dañar

* **Susto corto y proporcional.** Cada activación dura 3-4 s y tiene un tope duro por
  disuasor (`max_on_s`). La electroválvula del agua nunca puede quedar abierta.
* **Escalado.** Primera visita: luz + bufido. Si vuelve en menos de 5 minutos: luz +
  ultrasonido + agua. Si pasa mucho tiempo sin verlo, se vuelve al nivel suave.
* **Confirmación.** Hacen falta varias detecciones seguidas antes de actuar: una
  sombra o un pájaro no disparan nada.
* **Pausa y tope por hora.** Cooldown de 30 s entre activaciones y máximo 12 por hora.
* **Personas y perros.** Si aparece una persona o un perro en el cuadro, se apaga todo
  al instante y no se actúa. Nadie recibe un chorro de agua por error.
* **Horario silencioso.** De noche solo se usan disuasores que no molestan a los
  vecinos (luz, ultrasonido, agua).

* **Límites por zona.** Cada zona puede restringir qué disuasores se usan. En un
  techo compartido con los vecinos: luz y ultrasonido sí, agua nunca.

En [docs/humanitario.md](docs/humanitario.md) se explica qué métodos son seguros,
cuáles no, y qué medidas pasivas ayudan (tapa de basura, malla bajo la tierra, etc.).

## Hardware

Lista completa, cableado y alternativas en [docs/hardware.md](docs/hardware.md).
Lo mínimo:

| Pieza | Para qué |
|---|---|
| Raspberry Pi 4 o 5 (2 GB alcanza) | Corre la detección |
| Cámara Pi Module 3 **NoIR** + iluminador IR | Ver de noche, cuando más vienen |
| Módulo de 4 relés 5 V optoacoplados | Encender luz, válvula y ultrasonido |
| Electroválvula 12 V para manguera + fuente 12 V | Chorro de agua breve |
| Reflector LED 12 V | Luz repentina |
| Parlante 3 W + amplificador PAM8403 | Bufido / chorro de aire |
| Repelente ultrasónico comercial (disparado por relé) | Sonido que solo molesta al gato |
| Caja estanca IP65 | Proteger todo del agua y la lluvia |

Con una Pi Zero 2 W también funciona usando el detector por movimiento
(`backend: motion`), menos preciso pero suficiente en zonas acotadas.

## Instalación (Raspberry Pi OS)

```bash
git clone https://github.com/ipenas-cl/fuera-gatos.git
cd fuera-gatos
./scripts/install.sh          # paquetes, venv, sonidos, config.yaml y servicio systemd
nano config.yaml              # pines, zonas, horarios
.venv/bin/fuera-gatos check -c config.yaml
.venv/bin/fuera-gatos test-deterrents -c config.yaml --seconds 1   # probar cableado
.venv/bin/fuera-gatos run -c config.yaml
sudo systemctl enable --now fuera-gatos                            # arrancar solo
```

Sin hardware (para probar la lógica en cualquier PC):

```bash
pip install -e ".[dev]"
python scripts/make_sounds.py
fuera-gatos simulate                  # guion de visitas con reloj acelerado
fuera-gatos simulate --hour 23        # lo mismo, en horario silencioso
fuera-gatos run -c config.example.yaml --simulate   # cámara real, GPIO simulado
pytest
```

## Terreno con antejardín, techo compartido y jardín trasero

Si los gatos circulan por el techo y bajan a ambos jardines, hacen falta dos cámaras
(frente y fondo), cada una con sus zonas y sus relés. Hay configuraciones de ejemplo
en `examples/` y una guía con la ubicación de cámaras, aspersores y zonas en
[docs/terreno.md](docs/terreno.md). Cada cámara corre como un servicio aparte:

```bash
cp examples/config.frente.yaml config.frente.yaml
cp examples/config.fondo.yaml config.fondo.yaml
sudo systemctl enable --now fuera-gatos@frente fuera-gatos@fondo
```

## Configuración

Todo está en `config.yaml` (ver `config.example.yaml`, comentado). Lo más importante:

* **`zones.include`**: polígonos en píxeles donde sí se actúa. Dibuja uno sobre la
  basura y otro sobre el cantero; el resto del cuadro se ignora. Un gato cuenta como
  "dentro" si sus patas (base del cuadro) caen en el polígono. Para sacar las
  coordenadas, guarda una captura y mírala en cualquier editor de imágenes.
  Con `deterrents: [luz, ultrasonido]` una zona limita qué se puede usar en ella.
* **`controller.escalation`**: niveles, qué disuasores usa cada uno y cuántos segundos.
* **`controller.quiet_hours`**: horario nocturno y qué disuasores se permiten.
* **`deterrents`**: un relé por disuasor (pin BCM) o un sonido con archivos WAV.
* **`detector.suppress_labels`**: etiquetas que bloquean todo (`person`, `dog`).

### Detector

* `yolo` (recomendado): YOLOv8n reconoce la clase `cat` de COCO con buena precisión.
  En la Pi conviene exportar a NCNN una vez (`yolo export model=yolov8n.pt format=ncnn imgsz=320`)
  y poner `model: yolov8n_ncnn_model`; da unos 5-10 fps en Pi 4 y más en Pi 5.
* `motion`: diferencia de cuadros con filtro por tamaño del bulto. No sabe qué es un
  gato, así que úsalo solo con zonas bien acotadas y `min_area`/`max_area` ajustados.

## Registro y avisos

Cada activación queda en `data/events.jsonl` con la captura en `data/snapshots/`.
Sirve para ver a qué horas viene el gato y ajustar zonas o niveles. Con
`notify.telegram` activado, llega la foto al teléfono en cada activación.

## Estructura

```
fuera_gatos/
  cli.py          comandos: run, simulate, test-deterrents, check
  pipeline.py     bucle cámara -> detector -> zonas -> controlador
  controller.py   máquina de estados (confirmación, escalado, cooldown, supresión)
  zones.py        polígonos de actuación
  camera.py       picamera2, OpenCV (USB/RTSP) o sintética
  detection/      yolo.py, motion.py, scripted.py
  deterrents/     relay.py (GPIO), sound.py, simulated.py
  events.py       JSONL + capturas
  notify.py       Telegram
docs/             hardware.md, humanitario.md, terreno.md
examples/         config.frente.yaml, config.fondo.yaml
scripts/          install.sh, make_sounds.py
systemd/          fuera-gatos.service (una cámara), fuera-gatos@.service (varias)
tests/            pytest (lógica pura, sin hardware)
```

## Licencia

MIT.
