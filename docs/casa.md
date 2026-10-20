# Panel de casa: timbre y cámaras sin la nube de Ozom / Tuya

El problema de las apps de Ozom, Tuya o Smart Life es que la grabación y la detección
viven en la nube del fabricante: casi no guardan nada (o cobran por guardarlo) y su
"detección de humano o animal" es un filtro de movimiento barato. Aquí cada pieza
queda en tu equipo:

```
 timbre / cámaras ──> Frigate (graba, detecta persona/gato/perro/paquete)
                          │ MQTT + HTTP
                          ▼
              fuera-gatos casa  ──>  panel web (celular o PC)  +  Telegram con foto
                          │
                          └──> interruptores por MQTT (luces, puerta, nodos ESP32)
```

* **Historial real**: cada evento con miniatura y clip, guardado en tu disco
  (`record` y `snapshots` de `frigate.yml`).
* **Aviso de timbre**: banner, sonido y foto a Telegram al pulsarlo, y también cuando
  *alguien se para frente al timbre* sin pulsar.
* **Cámaras en vivo** y botones de interruptores (luz del patio, etc.).
* **Botón "Abrir puerta"** opcional, con confirmación.

## Lo primero: ¿tu cámara o timbre entrega video local?

Es lo único que decide qué tan fácil es esto. Revisa la ficha del modelo o prueba
`rtsp://usuario:clave@IP:554/` con VLC.

| Caso | Qué hacer |
|---|---|
| Tiene **RTSP u ONVIF** (se activa en la app) | Directo: poner la URL en `frigate.yml`. Es el mejor caso |
| Solo funciona por la app (típico Tuya/Ozom) | Probar el origen `tuya://` de [go2rtc](https://go2rtc.org/internal/tuya/) (viene dentro de Frigate). Exige una cuenta de la app **Tuya Smart** (no Smart Life; hay que volver a agregar el dispositivo) y activar *IoT Video Live Stream* en la plataforma de desarrolladores de Tuya. Los timbres a batería suelen dormir y tardar en responder |
| Ninguna de las dos | Cambiar el equipo: una cámara PoE con RTSP (Reolink, Dahua, Hikvision, TP-Link Tapo con RTSP) y un timbre con RTSP (Reolink Video Doorbell PoE, Dahua VTO). Es lo que de verdad resuelve el problema |

Un timbre pulsado necesita además una señal: los timbres con RTSP/ONVIF suelen
publicarla por ONVIF o por Home Assistant; con eso se envía a MQTT en el tópico
`doorbell.ring_topic`. Sin esa señal el panel igual avisa cuando Frigate ve a una
persona en la cámara del timbre.

## Puesta en marcha

```bash
cd examples/central
cp casa.yaml casa.yaml.local   # o editar casa.yaml directamente
# editar: clave (server.token), cámaras (mismos nombres que en frigate.yml), tópicos
docker compose up -d           # levanta Frigate, MQTT, fuera-gatos y el panel
# Panel: http://IP-laptop:8080
```

Sin Docker: `pip install -e ".[mqtt]"` y `fuera-gatos casa -c casa.yaml`.
Para probar sin MQTT real: `fuera-gatos casa -c casa.yaml --simulate`.
En el celular, "Agregar a pantalla de inicio" lo deja como app.

## Acceso desde fuera de casa

No abras el puerto 8080 en el router. Instala Tailscale o WireGuard en la laptop y
entra al panel por la VPN. Con `server.token` el panel pide clave; la clave viaja en
claro por HTTP, así que fuera de casa úsalo solo por la VPN.

## Qué expone el panel

Del Frigate solo se sirven capturas, miniaturas y clips de las cámaras que listas en
`casa.yaml`. Su configuración, borrado y demás API quedan inaccesibles desde el panel.
