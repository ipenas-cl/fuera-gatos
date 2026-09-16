# Lista de materiales por ubicación (modo centralizado)

Una laptop del armario como cerebro (Frigate + Mosquitto + fuera-gatos), tres puntos exteriores con cámara IP y nodo ESP32, más material común.
La variante con una Raspberry Pi por caja está descrita en hardware.md y terreno.md.
Precios en USD como referencia aproximada de tiendas en línea; varían según proveedor.

## Armario (ya lo tienes casi todo)

**Dónde:** La laptop o servidor viejo corre Frigate, Mosquitto y fuera-gatos. Solo hay que sumar el switch PoE y disco para grabar.

| Cant. | Pieza | Especificación | Dónde va exactamente | Ref. USD |
|---|---|---|---|---|
| 1 | Laptop o servidor existente | Intel 6.ª gen o más nuevo para usar la GPU integrada; Linux con Docker | En el armario, tapa cerrada sin suspender; la batería hace de UPS | 0–0 |
| 1 | Disco de 500 GB a 1 TB | SSD o HDD, para grabaciones (si la laptop no lo tiene) | En la laptop o por USB | 0–60 |
| 1 | Switch PoE de 4 u 8 puertos | 802.3af/at, alimenta las tres cámaras | En el armario, junto al router | 40–70 |
| 1 | Coral USB (solo si el CPU es viejo o AMD) | acelerador de detección; con Intel moderno no hace falta | USB de la laptop | 0–70 |
| 60 | Cable de red exterior Cat5e/6 | metros, con conectores; un tendido por cámara | Del armario a cada cámara por la pared | 30–60 |

Subtotal: USD 70–260

## Frente

**Dónde:** Cámara bajo el alero delantero a 2.5 m mirando a la calle en diagonal. Nodo en caja pequeña al lado, con los relés y las fuentes.

| Cant. | Pieza | Especificación | Dónde va exactamente | Ref. USD |
|---|---|---|---|---|
| 1 | Cámara IP PoE exterior | RTSP, IR integrado, 4 MP, lente 2.8 mm; con subflujo 640x480 | Bajo el alero, inclinada 30° hacia abajo | 50–100 |
| 1 | ESP32 DevKit + módulo 4 relés 5 V | nodo ESPHome; relés activo en bajo | Dentro de la caja del nodo | 8–15 |
| 1 | Torreta pan/tilt | soporte + 2 servos MG996R + boquilla 1.5-2 mm | Junto a la cámara, manguera de 6 mm hasta la bomba | 30–60 |
| 1 | Bomba de diafragma 12 V | 3-5 L/min, 60-100 psi | Al pie de la pared, junto al estanque | 15–30 |
| 1 | Estanque 20 L con válvula flotante | bidón + flotador mecánico conectado a la manguera de la casa | Al pie de la pared; siempre lleno sin intervención | 20–40 |
| 1 | Electroválvula 12 V NC ½" + aspersor de impacto | respaldo fijo del nivel 2 | Válvula junto a la llave; aspersor en la esquina opuesta del antejardín | 13–30 |
| 1 | Reflector LED 12 V 10 W |  | Bajo el alero, apuntando al antejardín | 8–15 |
| 1 | Repelente ultrasónico comercial | alimentado por relé | Pared delantera, a 1 m del suelo, hacia el cantero | 15–30 |
| 1 | DFPlayer Mini + parlante 3 W | opcional: bufido en microSD, lo dispara el nodo | Bajo el alero, mirando al suelo | 5–10 |
| 1 | Fuente 12 V 5 A + regulador buck 12→5 V 3 A | 12 V para bombas y luz; 5 V para ESP32 y servos | Dentro de la caja del nodo | 15–30 |
| 1 | Caja estanca IP65 20×15×10 cm | con prensacables | Bajo el alero, junto a la cámara | 10–25 |

Subtotal: USD 189–385

## Fondo

**Dónde:** Cámara en la pared trasera a 2.5 m mirando al jardín, el galpón y el borde trasero del techo. Nodo al lado.

| Cant. | Pieza | Especificación | Dónde va exactamente | Ref. USD |
|---|---|---|---|---|
| 1 | Cámara IP PoE exterior | misma que el frente | Pared trasera, inclinada hacia el jardín | 50–100 |
| 1 | ESP32 DevKit + módulo 4 relés 5 V |  | Dentro de la caja del nodo | 8–15 |
| 1 | Torreta pan/tilt | soporte + 2 servos + boquilla | Junto a la cámara | 30–60 |
| 1 | Bomba de diafragma 12 V |  | Al pie de la pared trasera | 15–30 |
| 1 | Estanque 20 L con válvula flotante | conectado a la llave del jardín trasero | Al pie de la pared | 20–40 |
| 1 | Electroválvula 12 V NC ½" + aspersor de impacto |  | Aspersor cerca del árbol, apuntando al centro (no al galpón) | 13–30 |
| 1 | Reflector LED 12 V 10 W |  | Pared trasera, hacia el jardín | 8–15 |
| 1 | Repelente ultrasónico comercial | alimentado por relé | Pared del galpón, hacia su techo (ahí no va agua) | 15–30 |
| 1 | DFPlayer Mini + parlante 3 W | opcional | Pared trasera, mirando al suelo | 5–10 |
| 1 | Fuente 12 V 5 A + regulador buck 12→5 V 3 A |  | Dentro de la caja del nodo | 15–30 |
| 1 | Caja estanca IP65 20×15×10 cm |  | Pared trasera | 10–25 |

Subtotal: USD 189–385

## Techo

**Dónde:** Cámara en la cumbrera mirando a lo largo del techo. Nodo, bombas y estanque sobre un muro medianero o junto a la cumbrera, nunca al medio de una plancha. Un cable de red PoE (cámara) y un cable de 12 V (nodo) suben por la pared.

| Cant. | Pieza | Especificación | Dónde va exactamente | Ref. USD |
|---|---|---|---|---|
| 1 | Cámara IP PoE exterior | con IR de 20 m o más; bullet, no domo | En mástil corto o sobre la caja, mirando a lo largo del techo | 50–100 |
| 1 | ESP32 DevKit + módulo 4 relés 5 V | bomba A, bomba B, luz; entrada del flotador | Dentro de la caja del nodo, en la cumbrera | 8–15 |
| 2 | Torreta pan/tilt A y B | soporte + 2 servos + boquilla cada una | Una en cada extremo del tramo propio, a 30-50 cm de la medianera, tilt hacia abajo | 60–120 |
| 2 | Bomba de diafragma 12 V | una por torreta | Junto al estanque | 30–60 |
| 1 | Estanque opaco 20-30 L | con tapa, rebalse y filtro de malla en la salida | A la sombra, sobre el muro medianero (25 kg lleno) | 15–30 |
| 1 | Interruptor de flotador | al GPIO34 del nodo | Dentro del estanque, a 3-4 cm del fondo | 3–8 |
| 1 | Desvío de canaleta con filtro de hojas | kit de captación de lluvia | En la bajada de agua más cercana, manguera al estanque | 15–40 |
| 1 | Bidón 20 L de recambio con conexión rápida | para rellenar en seco | Se guarda abajo lleno; sube cuando llega el aviso | 8–15 |
| 1 | Reflector LED 12 V 10 W |  | Sobre la caja, apuntando al tramo propio | 8–15 |
| 1 | Fuente 12 V 5 A + regulador buck 12→5 V 3 A | la fuente puede quedar abajo y subir solo 12 V | Caja del nodo (o abajo) | 15–30 |
| 15 | Cable 2 × 1.5 mm² para 12 V | metros, por la pared hasta la cumbrera, en canaleta plástica | Pared lateral hasta el techo | 15–30 |
| 1 | Caja estanca IP65 20×15×10 cm | fijada a la cumbrera o a un soporte | Cumbrera | 10–25 |

Subtotal: USD 237–488

## Material común y consumibles

**Dónde:** Para las tres ubicaciones.

| Cant. | Pieza | Especificación | Dónde va exactamente | Ref. USD |
|---|---|---|---|---|
| 10 | Manguera flexible 6 mm (PU o silicona) | metros, de bomba a boquilla | Cada torreta | 10–20 |
| 1 | Conectores rápidos 6 mm y abrazaderas | kit | Bombas, estanques y bidón | 5–10 |
| 1 | Manguera de jardín ½" + conectores | aspersores fijos y válvulas flotantes | Frente y fondo | 10–25 |
| 30 | Cable 2 × 1 mm² para 12 V | metros, reflectores y ultrasonido | Todas las cajas | 15–30 |
| 4 | Cable de servo con extensión | 50 cm a 1 m | Torretas | 4–12 |
| 1 | Cinta teflón, silicona neutra, prensacables extra | kit | Sellado de cajas y roscas | 5–15 |
| 10 | Diodos 1N4007 | en antiparalelo en bombas y válvulas | Módulos de relés | 10–30 |
| 1 | Tornillería, tarugos, abrazaderas de mástil | kit | Fijación de cajas, torretas y cámaras | 5–15 |
| 1 | Canaleta plástica y cinta UV | para los cables que suben al techo | Pared lateral | 5–15 |

Subtotal: USD 69–172

## Lista de compra consolidada

| Cant. | Pieza | Para | Ref. USD |
|---|---|---|---|
| 1 | Laptop o servidor existente | armario | 0–0 |
| 1 | Disco de 500 GB a 1 TB | armario | 0–60 |
| 1 | Switch PoE de 4 u 8 puertos | armario | 40–70 |
| 1 | Coral USB (solo si el CPU es viejo o AMD) | armario | 0–70 |
| 60 | Cable de red exterior Cat5e/6 | armario ×60 | 30–60 |
| 3 | Cámara IP PoE exterior | frente, fondo, techo | 150–300 |
| 3 | ESP32 DevKit + módulo 4 relés 5 V | frente, fondo, techo | 24–45 |
| 2 | Torreta pan/tilt | frente, fondo | 60–120 |
| 4 | Bomba de diafragma 12 V | frente, fondo, techo ×2 | 60–120 |
| 2 | Estanque 20 L con válvula flotante | frente, fondo | 40–80 |
| 2 | Electroválvula 12 V NC ½" + aspersor de impacto | frente, fondo | 26–60 |
| 3 | Reflector LED 12 V 10 W | frente, fondo, techo | 24–45 |
| 2 | Repelente ultrasónico comercial | frente, fondo | 30–60 |
| 2 | DFPlayer Mini + parlante 3 W | frente, fondo | 10–20 |
| 3 | Fuente 12 V 5 A + regulador buck 12→5 V 3 A | frente, fondo, techo | 45–90 |
| 3 | Caja estanca IP65 20×15×10 cm | frente, fondo, techo | 30–75 |
| 2 | Torreta pan/tilt y | techo ×2 | 60–120 |
| 1 | Estanque opaco 20-30 L | techo | 15–30 |
| 1 | Interruptor de flotador | techo | 3–8 |
| 1 | Desvío de canaleta con filtro de hojas | techo | 15–40 |
| 1 | Bidón 20 L de recambio con conexión rápida | techo | 8–15 |
| 15 | Cable 2 × 1.5 mm² para 12 V | techo ×15 | 15–30 |
| 10 | Manguera flexible 6 mm (PU o silicona) | comun ×10 | 10–20 |
| 1 | Conectores rápidos 6 mm y abrazaderas | comun | 5–10 |
| 1 | Manguera de jardín ½" + conectores | comun | 10–25 |
| 30 | Cable 2 × 1 mm² para 12 V | comun ×30 | 15–30 |
| 4 | Cable de servo con extensión | comun ×4 | 4–12 |
| 1 | Cinta teflón, silicona neutra, prensacables extra | comun | 5–15 |
| 10 | Diodos 1N4007 | comun ×10 | 10–30 |
| 1 | Tornillería, tarugos, abrazaderas de mástil | comun | 5–15 |
| 1 | Canaleta plástica y cinta UV | comun | 5–15 |

**Total estimado: USD 754–1,690**

## Orden sugerido

1. Primero el armario: Docker, Frigate y Mosquitto en la laptop, con una cámara IP. Ya hay grabación y se ven los gatos antes de comprar más.
2. Después el jardín donde más daño hacen (fondo o frente): nodo, torreta y estanque. Sirve para afinar zonas y calibración.
3. Al final el techo, la instalación más trabajosa (cables que suben, estanque, dos torretas).
