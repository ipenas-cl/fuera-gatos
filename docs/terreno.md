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
| Techo (frente y fondo) | Camino de paso entre casas | Luz, ultrasonido, sonido. **Nunca agua**: es techo del vecino, hay canaletas y puede haber mascotas ajenas | `techo_frente`, `techo_fondo` con `deterrents: [luz, ultrasonido, sonido]` |
| Antejardín | Tierra suelta para enterrar | Todo, incluido un chorro breve | `antejardin` |
| Basura junto a la entrada | Comida | Todo; además tapa con traba | `basura` |
| Jardín trasero | Tierra y refugio | Todo | `jardin_trasero` |
| Techo del galpón | Escalera hacia el techo principal | Luz, ultrasonido, sonido (sin mojar lo guardado) | `galpon` |

El objetivo principal no es el techo sino los **puntos de bajada**. Un gato que
pasa por el techo y no baja no molesta. Por eso la luz y el ultrasonido en el techo
son un aviso, y el agua en el jardín es la lección.

## Dos cámaras, uno o dos equipos

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
# ajustar pines, zonas y fuente de cámara de cada uno
sudo systemctl enable --now fuera-gatos@frente fuera-gatos@fondo
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

## Aspersores

* Uno por jardín, apuntando **hacia el centro del propio terreno**, nunca hacia la
  calle, la vereda ni la propiedad vecina. Presión baja: mojar patas, no empapar.
* Electroválvula en línea con la manguera, dentro de una caja estanca, cable hasta
  el relé de la Pi correspondiente.
* Probar con `fuera-gatos test-deterrents -c config.frente.yaml aspersor --seconds 2`
  y mirar dónde cae el agua.

## Con los vecinos

Al compartir techo, lo más probable es que alguno de los gatos sea de al lado.
Conviene avisarles qué se instaló y mostrarles que solo son luz, sonido y un
chorrito de agua. El ultrasonido en el techo también lo oyen sus mascotas, por eso
está limitado a ráfagas de pocos segundos y solo cuando hay un gato en el cuadro.
Si un vecino tiene perro, dejar `dog` en `suppress_labels`.
