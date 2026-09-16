# Ahuyentar sin dañar

Los gatos que usan un terreno como baño o rompen la basura no son "malos": buscan
tierra suelta para enterrar y comida fácil. La forma de que dejen de venir es que el
lugar les resulte **impredecible y desagradable**, nunca doloroso. Un susto corto y
repetido enseña; un daño solo genera sufrimiento y, además, es ilegal en la mayoría
de los países (leyes de bienestar animal). Muchos de esos gatos son mascotas del
vecindario.

## Métodos que usa este sistema (seguros)

| Método | Por qué funciona | Límites que aplica el software |
|---|---|---|
| **Chorro de agua dirigido** | Es el más eficaz, y el único que funciona con gatos ya acostumbrados a perros, púas y ultrasonido. Un hilo de agua que los persigue los sobresalta y no se habitúan. | Máx. 4-8 s en ráfagas, cooldown, tope por hora, límites mecánicos de puntería |
| **Luz repentina** | El cambio brusco los asusta y rompe la sensación de escondite. | Duración corta; de noche no molesta a los vecinos si apunta al suelo |
| **Sonido de bufido / aire comprimido** | Imita a otro gato o a un perro; sonidos grabados cortos. | Solo de día (horario silencioso configurable) |
| **Ultrasonido (20-25 kHz)** | Los gatos lo oyen, la mayoría de los adultos no. Es molesto, no doloroso. | Solo mientras hay gato, nunca continuo |

Combinados y en escalado, los gatos suelen dejar de venir en una o dos semanas.
Los dispositivos comerciales que hacen lo mismo (PIR + aspersor, tipo "ScareCrow" o
"Catwatch") tienen años de uso sin reportes de daño.

### ¿Qué tan fuerte puede ser el chorro?

Fuerte en velocidad y alcance, no en energía. La referencia es la pistola de riego
de jardín en modo chorro, o una bomba de diafragma de 12 V (hasta 100 psi / 7 bar)
con boquilla de 1.5-2 mm: moja, sorprende y llega lejos, pero no lastima ni a un
gatito. Los dispositivos comerciales de este tipo ("Yard Enforcer", "ScareCrow")
usan la presión de la red (3-4 bar) y llevan décadas en uso sin daños.

Lo que **no** se debe usar es una hidrolavadora (100-200 bar): a esa presión el
agua corta la piel. Tampoco agua caliente ni con aditivos.

## Lo que este sistema no hace y no conviene hacer

* **Repelentes químicos**: naftalina, amoníaco, lavandina, pimienta, cayena. Son
  tóxicos o irritan ojos y mucosas del gato (y de perros y niños).
* **Trampas, alambres, vidrios, tachuelas**: causan heridas.
* **Láseres a los ojos, ultrasonido continuo a alto volumen, agua a presión**:
  pueden lesionar o generar estrés crónico.
* **Alimentarlos "para que no revuelvan"**: refuerza la visita.

## Gatos que ya no se asustan con nada

Cuando son varios (cinco o más) y ya aprendieron a ignorar perros, ultrasonido o
púas, lo que falla no es el método sino la previsibilidad: un aparato fijo que
siempre hace lo mismo se aprende en dos días. Lo que sí funciona con ellos:

1. **Agua que persigue, desde la primera vez.** No dar "avisos" con luz o sonido:
   el primer contacto con el terreno tiene que ser un chorro dirigido. Por eso la
   torreta está en el nivel 1.
2. **Sin huecos.** Cubrir todos los puntos donde bajan del techo. Un solo rincón
   sin cobertura se convierte en el nuevo baño. Dos cámaras y un aspersor fijo de
   respaldo por jardín.
3. **Constancia.** Dos o tres semanas de respuesta inmediata cada vez. Los gatos
   memorizan el lugar como "malo" y lo sacan de su ruta; los nuevos que lleguen
   aprenden en pocos días.
4. **Quitar el motivo.** Basura con traba y malla bajo la tierra. Si no hay premio,
   no vale la pena arriesgarse al chorro.
5. **Revisar el registro.** Si después de dos semanas siguen las activaciones en
   el mismo punto, el chorro no está llegando ahí: recalibrar o mover la torreta.

## Medidas pasivas que multiplican el efecto

* **Basura**: tacho con tapa y traba o correa elástica; sacar las bolsas justo antes
  de la recolección; no dejar bolsas en el piso.
* **Cantero**: los gatos evitan superficies donde no pueden escarbar. Malla
  gallinera (tela de gallinero) bajo 2-3 cm de tierra o mantillo, piedras grandes,
  piñas, o ramas de poda sobre la tierra desnuda. Cubrir la tierra con cobertura
  vegetal densa.
* **Olores que rechazan y no dañan**: cáscaras de cítricos, borra de café, plantas como
  ruda, lavanda o *Coleus canina*. Hay que renovarlos seguido.
* **Limpiar bien** las zonas ya usadas como baño (agua con vinagre o limpiador
  enzimático): el olor los hace volver al mismo punto.
* **Hablar con los vecinos**: si los gatos tienen dueño, un arenero en casa y
  castración reducen mucho el marcado y el vagabundeo. Si son gatos comunitarios, los
  programas de castrar-y-devolver de la zona son la solución de fondo.

## Seguridad de las personas y otros animales

* Si el detector ve una **persona o un perro**, no se activa nada y, si algo estaba
  encendido, se apaga al instante.
* El aspersor apunta hacia adentro del terreno y a baja presión.
* Los niveles y duraciones tienen topes en la configuración (`duration_s` ≤ 30 s,
  `max_on_s` por disuasor) y en el hardware (el relé corta si la Pi se apaga).
* Revisar el registro de eventos las primeras semanas: si hay activaciones a horas
  raras o sin gato, subir `confidence` o ajustar las zonas.
