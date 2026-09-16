# Instalación en un terreno con techo compartido

Este esquema corresponde a un lote alargado típico: antejardín hacia la calle, casa
al medio con techo continuo con las casas de la izquierda y la derecha, y jardín
trasero con un galpón y un árbol. Los gatos usan el techo como autopista: bajan al
antejardín o al jardín trasero, hacen sus necesidades en la tierra y revisan la
basura junto a la entrada.

```
            calle
   ┌───────────────────────┐
   │      antejardín       │  <- Cámara 1 (bajo el alero, mirando a la calle)
   │  [basura]             │     zonas: techo_frente, antejardin, basura
   ├───────────────────────┤
 ══╡        casa           ╞══   techo compartido con vecinos (izq. y der.)
   ├───────────────────────┤
   │    jardín trasero     │  <- Cámara 2 (pared trasera o galpón)
   │  [galpón]      árbol  │     zonas: techo_fondo, jardin_trasero, galpon
   └───────────────────────┘
```

## Qué cubrir y con qué

| Lugar | Por qué vienen | Disuasores | Zona en la configuración |
|---|---|---|---|
| Techo | Camino de paso entre casas | Cámara 3 en la cumbrera y dos torretas con agua autónoma (estanque + bomba), limitadas por las medianeras. Ver [techo.md](techo.md) | `techo_propio` con agua; `techo_vecino_*` solo registro |
| Borde del techo visto desde abajo | Lo que ven las cámaras 1 y 2 | Luz, ultrasonido, sonido; el agua la ponen las torretas de arriba | `techo_frente`, `techo_fondo` con `deterrents: [luz, ultrasonido, sonido]` |
| Antejardín | Tierra suelta para enterrar | Torreta desde la primera visita, luz; aspersor fijo de respaldo | `antejardin` |
| Basura junto a la entrada | Comida | Torreta, luz; además tapa con traba | `basura` |
| Jardín trasero | Tierra y refugio | Torreta, luz, aspersor fijo | `jardin_trasero` |
| Techo del galpón | Escalera hacia el techo principal | Luz, ultrasonido, sonido (sin mojar lo guardado) | `galpon` |

El objetivo principal no es el techo sino los **puntos de bajada**. Un gato que
pasa por el techo y no baja no molesta. Con gatos acostumbrados, la lección tiene
que ser el agua desde el primer contacto con el jardín; la luz y el sonido solos
ya demostraron no servir con este grupo.

Con cinco gatos conviene un `cooldown_s` corto (15 s) y `max_activations_per_hour`
alto (20): suelen bajar de a varios y el segundo no debe encontrar el sistema en
pausa.

## Tres cámaras, uno o más equipos

* **Opción A, una Raspberry Pi con dos cámaras**: la Pi 5 tiene dos conectores CSI.
  Se ejecutan dos instancias con configuraciones distintas (`config.frente.yaml`,
  `config.fondo.yaml`) y pines de relé distintos. Hace falta que el cable llegue a
  ambos extremos de la casa, o poner la Pi en el medio.
* **Opción B, una Pi por extremo** (más simple de cablear): cada una con su cámara,
  sus relés, su aspersor y su reflector. Es lo recomendado si la casa es larga.
* **Opción C, cámaras IP** con RTSP en ambos extremos y una sola Pi con `source: rtsp`.
  Los relés siguen necesitando cable hasta cada aspersor.

En cualquier caso, en el equipo:

```bash
cp examples/config.frente.yaml config.frente.yaml
cp examples/config.fondo.yaml config.fondo.yaml
cp examples/config.techo.yaml config.techo.yaml
# ajustar pines, zonas y fuente de cámara de cada uno
sudo systemctl enable --now fuera-gatos@frente fuera-gatos@fondo fuera-gatos@techo
journalctl -u 'fuera-gatos*' -f
```

## Ubicación de las cámaras

* **Cámara 1** bajo el alero delantero, a 2.5 m, inclinada hacia abajo para que el
  cuadro incluya una franja del borde del techo arriba, el antejardín en el medio y
  la basura abajo. Si la vereda entra en el cuadro, que quede fuera de todas las zonas.
* **Cámara 2** en la pared trasera a 2.5 m mirando al jardín y al galpón; si el
  galpón queda muy cerca, ponerla en el galpón mirando hacia la casa para ver el
  borde del techo trasero.
* Ambas **NoIR con iluminador infrarrojo**: los gatos vienen sobre todo de noche.
* Para dibujar las zonas: arrancar con `--simulate`, esperar una activación o bajar
  `confirm_frames` a 1 temporalmente, abrir la captura de `data/<cámara>/snapshots/`
  y anotar las esquinas de cada polígono en píxeles.

## Torreta y aspersores

* **Una torreta por jardín**, montada junto a la cámara, con la bomba y el bidón
  en la caja estanca. Sus `limits` de pan/tilt deben dejar fuera la vereda, la
  calle y los patios vecinos, aunque el detector se equivoque.
* **Un aspersor fijo de impacto por jardín** como respaldo (nivel 2), apuntando
  hacia el centro del propio terreno. Cubre el rincón que la torreta no alcanza.
* Probar con `fuera-gatos aim -c config.frente.yaml --pan 90 --tilt 50 --water 1`
  y con `fuera-gatos test-deterrents -c config.frente.yaml aspersor --seconds 2`,
  y mirar dónde cae el agua.
* En el antejardín, cuidado con la vereda: si un vecino pasa mientras un gato está
  en el cantero, el detector ve `person` y apaga todo, pero además los límites
  mecánicos impiden que la torreta apunte hacia afuera.

## Con los vecinos

Al compartir techo, lo más probable es que alguno de los gatos sea de al lado.
Conviene avisarles qué se instaló y mostrarles que solo son luz, sonido y un
chorrito de agua. El ultrasonido en el techo también lo oyen sus mascotas, por eso
está limitado a ráfagas de pocos segundos y solo cuando hay un gato en el cuadro.
Si un vecino tiene perro, dejar `dog` en `suppress_labels`.
