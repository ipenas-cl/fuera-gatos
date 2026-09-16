# Modo centralizado: una laptop del armario como cerebro

En vez de una Raspberry Pi por caja, todo el procesamiento corre en un solo
equipo dentro de la casa (una laptop o servidor viejo del armario). Afuera
quedan solo cámaras IP y un nodo pequeño por ubicación para relés y servos.
Además de espantar gatos, el mismo equipo graba las tres cámaras y avisa si
entra una persona: un sistema de seguridad privado.

```
   armario                          exterior
   ┌──────────────────────┐        ┌──────────────┐  PoE   ┌───────────────┐
   │ laptop               │◄───────┤ switch PoE   ├───────►│ cámara IP x3  │
   │  Frigate (NVR+IA)    │  red   └──────────────┘        └───────────────┘
   │  Mosquitto (MQTT)    │
   │  fuera-gatos x3      │  WiFi/MQTT                     ┌───────────────┐
   │  (Home Assistant)    │◄──────────────────────────────►│ nodo ESP32 x3 │
   └──────────────────────┘                                │ relés, servos │
                                                           │ flotador      │
                                                           └───────────────┘
```

## Qué hace cada pieza

| Pieza | Función |
|---|---|
| **Frigate** | Recibe el video RTSP de las cámaras, detecta gato / persona / perro, graba 24/7 y guarda clips de eventos. Publica cada objeto en MQTT (`frigate/events`) |
| **Mosquitto** | Servidor MQTT: por aquí hablan Frigate, fuera-gatos y los nodos |
| **fuera-gatos** | Una instancia por cámara. Lee los eventos de Frigate (`detector.backend: frigate`), aplica zonas, confirmación, escalado y límites, y manda órdenes a los nodos (`mqtt_switch`, `mqtt_turret`) |
| **Nodo ESP32 (ESPHome)** | Relés de bomba, luz, ultrasonido; servos de la torreta; flotador del estanque. Cada salida se apaga sola por firmware aunque se caiga la red |
| **Home Assistant** (opcional) | Panel, avisos al teléfono con clip, automatizaciones (por ejemplo "luz del patio si hay persona de noche") |

## Requisitos de la laptop

* **CPU Intel de 6.ª generación (2015) o más nueva**: Frigate usa la GPU
  integrada con OpenVINO para detectar y VAAPI para decodificar. Tres cámaras
  a 5 fps de detección cargan poco.
* **CPU más vieja o AMD**: agregar un Coral USB (acelerador, ~60 USD) o bajar a
  2 fps de detección. Solo con CPU es posible pero se calienta.
* **Disco**: 500 GB a 1 TB para grabaciones (3 días continuos + 30 días de clips
  con persona caben en 300 GB con tres cámaras).
* **Sistema**: cualquier Linux con Docker. Ubuntu Server o Debian.
* **Energía**: la laptop tiene batería, que hace de UPS. Cerrar la tapa sin
  suspender (`HandleLidSwitch=ignore` en `/etc/systemd/logind.conf`).
* **Red**: cable a un switch PoE de 4 puertos (alimenta las cámaras). Los nodos
  van por WiFi; si el WiFi no llega al techo, un cable de red al nodo también sirve.

## Instalación

```bash
# 1. Docker en la laptop
curl -fsSL https://get.docker.com | sh

# 2. Repositorio y configuración
git clone https://github.com/ipenas-cl/fuera-gatos.git
cd fuera-gatos/examples/central
mkdir mosquitto && cp mosquitto.conf mosquitto/
# editar frigate.yml: IP, usuario y clave RTSP de cada cámara; máscaras
# editar config.*.yaml: zonas y calibración (igual que en modo distribuido)

# 3. Arrancar
docker compose up -d
docker compose exec mosquitto mosquitto_passwd -c /mosquitto/config/passwd fueragatos
docker compose restart mosquitto
# Interfaz de Frigate: http://IP-laptop:5000

# 4. Nodos ESP32 (desde cualquier PC con Python)
pip install esphome
cd ../esphome && cp secrets.example.yaml secrets.yaml   # editar
esphome run nodo-frente.yaml      # conectar el ESP32 por USB la primera vez
```

## Calibración y pruebas

Igual que en modo distribuido, pero las órdenes viajan por MQTT:

```bash
fuera-gatos test-deterrents -c config.frente.yaml luz aspersor --seconds 1
fuera-gatos aim -c config.frente.yaml --name torreta --pan 90 --tilt 50 --water 1
fuera-gatos run -c config.frente.yaml --simulate   # lee Frigate real, no manda órdenes
```

Para dibujar las zonas se usa la captura de `http://IP:5000/api/frente/latest.jpg`
o directamente la vista de la cámara en Frigate, que muestra las coordenadas.

## Seguridad y privacidad

* Las cámaras IP no deben salir a internet: sin puerto abierto en el router,
  sin "nube" del fabricante. Se ven desde afuera con una VPN (WireGuard o
  Tailscale en la laptop).
* Las máscaras de movimiento de Frigate dejan fuera la vereda y todo lo que sea
  del vecino. Grabar la vía pública desde tu terreno suele ser legal; los
  patios ajenos no.
* Contraseña propia en cada cámara y en Mosquitto. Los ESP32 solo aceptan
  órdenes del broker.
* Si la laptop se apaga, los nodos no reciben órdenes y todo queda apagado:
  falla segura. Los topes de tiempo viven en el firmware del nodo.

## Nodos ESP32: pines de referencia

| Nodo | Relés (activo en bajo) | Servos (PWM) | Otros |
|---|---|---|---|
| nodo-frente | GPIO25 bomba torreta, 26 aspersor, 27 luz, 14 ultrasonido, 12 sonido | 18 pan, 19 tilt | DFPlayer en UART 17/16 |
| nodo-fondo | igual que frente | 18 pan, 19 tilt | DFPlayer |
| nodo-techo | GPIO25 bomba A, 26 bomba B, 27 luz | 18/19 torreta A, 21/22 torreta B | flotador en GPIO34 |

Alimentación de cada nodo: fuente 12 V 5 A para bombas, válvula, luz e IR; un
regulador 12→5 V (buck) de 3 A para el ESP32 y los servos. GND común.
