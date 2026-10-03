# Bit Heroes Quest: perfiles de farmeo, inventario y elección técnica

Ampliación investigada el **2 de octubre de 2026** de [la guía base](BIT_HEROES_FARMEO.md).
Dirigida al OpenCode que desarrolla el nuevo bot. **Investigación y recomendaciones,
no funciones implementadas ni acciones realizadas en la cuenta.**

El usuario pide familiares concretos, equipo/runas por objetivo, ajustes seguros,
eficiencia de energía, conservación de consumibles escasos, reposición de comunes
con oro y un conteo por run de oro, XP, objetos, conjuntos y tier. También pide
evaluar Java/otros lenguajes y aprovechar herramientas u otras IAs cuando ayuden.
La reposición con oro es una ampliación específica de la política inicial «no
compres nada»: no autoriza gemas, dinero, cualquier objeto de la tienda ni gasto
ilimitado. **Durante esta investigación no se compra, consume ni equipa nada.**

**Fuentes:** O = soporte oficial; W = comunidad; T = documentación técnica.
Los perfiles, límites y campos de registro son propuestas, no mecánicas oficiales.
Las tablas comunitarias deben comprobarse en el cliente actual.

## 1. Perfiles: elegir un objetivo, no simplemente repetir una dungeon

| Perfil | Ruta y criterio | Preparación | Finalización |
| --- | --- | --- | --- |
| Familiar concreto | Dungeon/raid donde aparece; ofertas del objetivo por recurso | Quindi, Capture Rate activo, lista de nombres y presupuesto Persuade | Cantidad conseguida, presupuesto o límite de tiempo |
| Ingredientes de una fusión | Fuente de cada familiar/material que falta | Receta y schematic verificados; reservar copias de combate/Stable | Ingredientes reunidos; no fusionar automáticamente |
| Equipo de progreso | Tier y fuente adecuados, victoria consistente | Vryn, Item Find; equipo estable que ya gana | Pieza/rareza objetivo o presupuesto |
| Pieza de conjunto | Fuente del conjunto y piezas que faltan, no «cualquier set» | Vryn; colección e inventario protegidos | Pieza nueva/cantidad elegida |
| Oro | Oro neto por recurso, no solo oro del resultado | Dar; evitar Persuade indiscriminado y compras no rentables | Meta neta o presupuesto |
| XP | XP confirmada por recurso y por minuto | Zyrk; dificultad ganable sin consumir objetos escasos | Nivel/meta de XP o presupuesto |
| Material específico/evento | Tabla y evento realmente activos | Recurso correcto y reserva para otros objetivos | Cantidad/puntos/meta visible |

Prioridad recomendada: **supervivencia y cero gasto accidental → fuente correcta
→ eficiencia por recurso → velocidad**. Un perfil no debe cambiar a otro modo
por falta de energía ni sustituir silenciosamente el familiar objetivo.

## 2. Tier y estado de la cuenta

Registrar por separado:

- Héroe activo, nivel y progreso de Quest: zonas/flags completadas y accesos abiertos.
- Tier de progresión confirmado, tier de cada pieza equipada y tier del botín.
- Actividad seleccionada, dificultad, roster y tier/restricciones de esa actividad.
- Runas realmente activas, familiares de combate, Stable y augments disponibles.
- Saldos y reservas: energía, shards, xeals, tokens, tickets, badges, oro y gemas.

**Nivel no es tier.** Una cuenta puede llevar piezas de varios tiers y farmear
una zona anterior por familiares. No deducir su tier de una sola pieza ni escribir
una regla universal `tier = número de zona`: la wiki documenta, por ejemplo,
R1/T4, R2/T5 y R3/T6, y el soporte sitúa Raid 1 después de Zone 3. [W7][O9]
Leer el tier mostrado por el cliente; si no está visible, usar progreso/catálogo
confirmados por el usuario y marcarlo como declarado, no como OCR observado.

Revalidar ruta y equipo tras un nuevo tier/desbloqueo. Una primera victoria puede
abrir diálogos, tutoriales u ofertas: eso es progreso, no una repetición conocida.
No hay datos comprobados aquí del tier, inventario o equipo actual de la cuenta.

## 3. Familiares: captura, rutas y cantidades

### Cómo conseguirlos

Derrotar al enemigo puede abrir una oferta de reclutamiento. Capture Rate mejora
la aparición de ofertas; Persuade paga oro por un intento con su propio porcentaje
de éxito. Bribe utiliza gemas y queda prohibido en estos perfiles. No existe una
garantía de captura al subir Capture Rate. Leer nombre, coste y resultado. [W8]

Una fusión **no se obtiene persuadiendo su resultado**: necesita schematic,
familiares e ingredientes de su receta. El soporte recomienda buscar schematics
regulares en las áreas donde viven los componentes; los schematics de World
Boss/Invasion tienen fuentes distintas y no salen del Schematic Item regular. [O2]

### Rutas concretas de referencia

Cantidades para **una** fusión, según Fusion By Location. No son un orden obligatorio
de progreso ni una promesa de que todas las recetas sigan iguales. [W1]

| Objetivo | Familiares y lugares | Otros ingredientes publicados |
| --- | --- | --- |
| Bor'lan | 1 Bob en Z1D2 + 1 Mer'lan en Z1D3 | Schematic + 50 Rare Material |
| Shrampz | 1 Shrump en Z1D2 + 1 Grampz en Z2D2 | Schematic + 50 Rare Material |
| Remmyt | 1 Rexie en Z4D1 + 1 Emmyt en Z5D1 | Schematic + 5 Epic Material |
| Omo | 6 Opo en Z6D2 | Schematic + 5 Epic Material + 10 Demon Juice |
| Úlairius | 3 Negrim + 3 Varlos + 3 Larzhul, en Z6D3 | Schematic + 5 Epic Material |
| Velk | 6 Staeus en Z4D3 | Schematic + 5 Epic Material + 10 Hobbit Foot |

`Z1D2` = Zone 1, Dungeon 2, **no** Flag 2. Confirmar nombres en el cliente: en
Bit Valley la wiki identifica Z1D2 como Dryad's Heart y Z1D3 como Lord Cerulean's
Tomb; en Wintermarsh, Z2D2 como Blubber's Gutter. Las listas introductorias de
esas páginas no siempre tienen el mismo orden que sus tablas/diálogos. [W2][W3]
El soporte escribe «Mer'land» en el ejemplo de Bor'lan, mientras la wiki escribe
«Mer'lan»: no convertir ese error de nombre en dos objetivos diferentes. [O2][W1]

Ejemplo útil: **Z1D2 reúne Bob y Shrump**, por lo que puede servir a los dos
primeros objetivos. Después se necesitan Mer'lan y Grampz en otras rutas.
Las dungeons especiales de Zone 1/2 reúnen familiares de toda la zona y requieren
las tres dungeons completadas en Heroic según la wiki. Pueden servir cuando faltan
varios objetivos; no asegurar que sean mejores por energía para un único nombre. [W2][W3]

### Copias, Stable y augments

- Stable conserva duplicados y mejora los familiares del mismo tipo; el soporte
  indica que el beneficio de tipo llega a su máximo con cinco alojados. [O3]
- Para un objetivo de una copia de combate y cinco alojadas de una fusión cuya
  receta usa un Bob y un Mer'lan, se necesitan seis de cada componente y seis
  veces los materiales, **menos lo ya disponible**, con la receta actual validada.
- Copias alojadas, de combate y reservadas para otra receta no son inventario
  libre. Las fusiones consumen componentes; no liberar ni consumir reservas.
- Los augments se equipan a familiares, no a la tabla de runas del jugador.
  La wiki distingue Pump (modificadores), Bone (condiciones), Chip (efectos tipo
  set) y Brain/Neurion (efectos disparados tipo pet), con fuentes diferentes. [W10]
- La wiki describe un multiplicador de augments asociado a Stable y máximos
  según rareza. **No asumir que cinco alojados dan siempre 6× a todo augment**;
  comprobar el bono mostrado. Esto es distinto del máximo general citado por soporte.
- Elegir augments por función del familiar: supervivencia para quien recibe daño,
  curación/escudos para soporte, daño para atacante. Evitar rerolls, destrucción,
  fabricación o bolsas de tienda en el ciclo de farmeo.

### Política del bot

Desactivar Decline duplicate familiars para el objetivo que necesita copias.
Usar lista por **nombre**, cantidad pendiente y presupuesto de oro. Un filtro
nativo solo por rareza no equivale a buscar Bob o Grampz: también paga otros
familiares de esa rareza. Si decide el bot, desactivar auto-Persuade nativo;
si decide el juego, documentar sus limitaciones. Nunca dos autoridades a la vez.

Contar ofertas del objetivo, intentos, éxitos, fallos y oro gastado por separado.
Una oferta no es una captura, un clic no confirma un intento cobrado, y un familiar
obtenido durante combate no necesariamente aparece en el resumen final.

### De dónde salen los materiales que faltan

Rare/Epic Material **no son lo mismo** que un material de fusión con nombre propio.
El soporte confirma estas vías para los materiales básicos; Exchange destruye
la pieza y Trade consume otros materiales. No son reposiciones gratuitas. [O10][O11]

| Material | Fuente publicada | Consecuencia para el objetivo |
| --- | --- | --- |
| Common Material | Bounties y Exchange de equipo common | Revisar recompensas antes de sacrificar equipo |
| Rare Material | Bounties, premios PvP y Exchange de equipo rare | Bor'lan/Shrampz necesitan reserva propia |
| Epic Material | Bounties, premios PvP y Exchange de equipo epic o superior/cosméticos | Reservar para recetas; rareza superior no significa excedente |
| Hobbit Foot | Orlag Clan World Boss, cualquier dificultad según wiki | Velk necesita esta fuente además de Staeus en Z4D3 |
| Demon Juice | Netherworld World Boss, cualquier dificultad según wiki | Omo necesita esta fuente además de Opo en Z6D2 |
| Rune Fragment | Premios de eventos/bounties y otras fuentes comunitarias | Farmear fragmentos no garantiza una runa concreta |
| Mud / Pinion / Mythic Curio | Dungeons / World Boss / Raids, respectivamente, según wiki | Materiales de fabricación distintos, no sustituibles por Epic Material |

Las fuentes con nombre propio de la tabla son comunitarias. [W13] No asumir que
capturar suficientes Opo completa Omo: faltan schematic y materiales. El déficit
de cada ingrediente es `max(0, cantidad necesaria - cantidad libre confirmada)`;
lo reservado para equipo, otra fusión o Stable no es cantidad libre.

El soporte excluye los materiales de fabricación de Item Find. La wiki también
excluye los de fusión y afirma que estos sí responden al multiplicador de botín.
Eso **no demuestra** que se multipliquen las ofertas de familiares ni todos los
premios de cualquier actividad. Comprobar cada material/multiplicador antes de
usar xN para optimizarlo; no prometer drops fijos. [O8][W13]

Antes de cualquier mantenimiento autorizado, usar el bloqueo nativo de las
piezas valiosas: el soporte confirma que impide Exchange. `ALL` marca todo lo
visible tras el filtro, no «solo lo inútil». La reserva del bot complementa el
bloqueo, no lo sustituye. [O11] Esta investigación no bloquea ni destruye nada.

**No confiar en deshacer:** soporte no revierte fabricación accidental. Su
política de objetos fundidos, actualizada el 29 de julio de 2026, limita las
devoluciones, exige nombre exacto y materiales disponibles y no acepta objetos
fundidos hace más de 90 días ni duplicados del mismo objeto. No hay recuperación
universal que vuelva segura una limpieza automática. [O12][O13]

## 4. Runas: cuáles activar y cómo evitar pérdidas

El soporte confirma cinco tipos, fabricación con fragments/oro/materiales y
recompensas/tienda como fuentes. **No son drops ordinarios de dungeons.** [O1]

| Tipo | Función | Aplicación al perfil |
| --- | --- | --- |
| Minor | Bonos de recursos/farmeo | Quindi = captura; Vryn = Item Find; Dar = oro; Zyrk = XP [W4] |
| Major | Modificadores ofensivos/defensivos | Mantener combinación que permite ganar; no todo es daño |
| Meta | Efectos sujetos a condiciones | Evaluar rol, posición, HP/SP y comportamiento real de Auto |
| Relic | Efectos disparados | Validar disparador y supervivencia, no solo la cifra de rareza |
| Artifact | Efectos especiales/condicionales | Comprobar condiciones y sinergias del equipo actual |

Para preparar el perfil: abrir la tabla de runas, identificar el slot del tipo,
seleccionar una runa **ya colocada en ese slot**, activarla y comprobar que queda
activa y cambia el bono correspondiente. No asumir coordenadas o nombres de
botones: este flujo conceptual necesita capturas del cliente actual.

**Colocar una runa nueva fija su slot:** no puede trasladarse después a otro.
Se pueden tener varias en el mismo slot, pero solo una activa por slot. Exchange
destruye una inactiva y devuelve solo parte de fragments (20% según soporte). [O1]
No insertar nuevas ni Exchange/Melt automáticamente para «optimizar» el perfil.
Craft genera un resultado aleatorio; no gastar materiales esperando obtener una
Quindi concreta garantizada. La wiki añade excepciones avanzadas que hay que validar.

Las Minor son bonos del jugador, no augments del familiar. Para farmeo de
familiares priorizar Quindi disponible; para equipo, Vryn; para oro, Dar; para
XP, Zyrk. No sacrificar fiabilidad de combate por una configuración teórica.

## 5. Equipo, equipamiento y conjuntos

Para equipar: inspeccionar inventario, comparar la pieza con la del mismo slot,
seleccionar la pieza aprobada, equiparla y verificar perfil/estadísticas/skills
antes de entrar. Para repetir, fijar un outfit conocido; no autoequipar todo drop.
Una mejora de TS puede romper un bono de conjunto, una habilidad o supervivencia.

Armory guarda y equipa outfits de **gear**; se desbloquea al nivel 20. Se pueden
elegir outfits de amigos/gremio en el roster. Slots adicionales pueden costar
oro/gemas. Usar slots existentes; no suponer que Armory también guarda runas,
familiares y augments: comprobarlos por separado. [O4]

La pieza debe registrarse con nombre, slot, rareza, tier, mejoras y conjunto.
Rareza «Set» no demuestra cuál es el conjunto. Contar **piezas distintas** de
la colección y piezas equipadas: dos copias del mismo casco no completan dos
slots de un set. El tooltip determina los umbrales y efectos actuales. [W5][W6]

Ejemplos para que el catálogo separe fuente y tier; no es todo el catálogo:

| Conjunto | Tier y fuente comunitaria | Piezas/umbrales publicados |
| --- | --- | --- |
| Ares Legacy | T5, Raid 2 | Phobos + Deimos; 2/2 |
| Divinity | T6, Raid 3 | Phantomlight + Legacy Of Truth + Trinity Plate; 2/3 y 3/3 |
| M.A.R.U | T7, Raid 4 | Visortron, Mechcoat, Blast Protocol, ROM BIOS; 2/4, 3/4, 4/4 |
| Unity | T5, Trials/Gauntlet | Despair + Sorrow; 2/2 |
| Lunar Guardian | T6, Orlag World Boss | Maelstrom + Eclipse Barrier; 2/2 |

Estos sets **no se buscan indistintamente en cualquier dungeon**. La tabla
comunitaria identifica fuentes; el tier, dificultad y disponibilidad reales
deben confirmarse. También hay Set Chests en Craft → Trade: se desbloquean con
material específico y requieren filtros Set/Equipment. Son otra vía, no un
drop garantizado ni permiso para fabricar/gastar materiales. [O5]

Proteger piezas nuevas de conjunto, mythic/ancient, recetas y reservas. No hacer
Exchange/ALL, Upgrade/Reforge ni subir tier por iniciativa del repetidor. La
elección de build necesita rol, elementos y equipo actual, no una lista universal
de «mejor set». En contenido avanzado, revisar también reglas especiales que
pueden desactivar pets, curación, block u otros efectos. [W7]

### Ancient y contenido de 2026: objetivos aparte

Ancient no equivale a «un drop de rareza alta al azar». El soporte describe
Starweave mediante la dungeon Ancient de Galaran/Zone 8, Suthine Shard,
Ropralt Crystal fabricado con materiales de mythics concretos y 1.000.000 oro.
Las recetas Ancient de otras zonas no tienen exactamente los mismos pasos;
registrar el requisito de la pieza/tier, no generalizar este ejemplo. [O14]

El artículo oficial **Supercharged Ancient Gear**, actualizado el 5 de mayo
de 2026, distingue Supercharged Harvester y Polychromatic Blaster: versión
base desbloqueada, World Boss correspondiente (Project: Goodall o Gallus
Apotheosis) en **Ancient de T21**, base subida a T21 y cuatro mejoras, y Reforge
que consume el objeto del milestone. El resultado queda sin mejoras. [O15]
No asumir que los bosses actuales solo tienen Normal/Hard/Heroic ni que un
milestone sea un drop aleatorio repetible. Son perfiles avanzados opcionales;
el repetidor inicial no debe subir tier, fundir mythics ni fabricar para alcanzarlos.

### Mascotas, accesorios, monturas y enchants: piezas que faltaban

**Pet no es familiar.** Es equipo que puede disparar efectos en combate; no se
consigue persuadiendo al enemigo del mismo nombre. Accessories es otra categoría,
con modificadores secundarios, no simplemente el collar/anillo de gear. La wiki
documenta tienda, gremio, premios de eventos y fabricación para estas categorías;
no son una promesa de drop ordinario en la dungeon elegida. [W15][W16]

| Categoría | Qué revisar antes de fijar el perfil | Qué no automatizar por inferencia |
| --- | --- | --- |
| Pet | Probabilidad, disparador, efecto, objetivo y mejoras | Comprar huevo, cambiar proc por Reforge, fundir para Prism Dust |
| Accessory | Bonos defensivos/ofensivos, elementos y posibles penalizaciones | Comprar caja, confundir rareza con mejor build, fundir para Molten Tin |
| Mount | Tier, distribución de stats, bono y habilidad disponible | RELEASE, rerolls o fabricar usando Mount Guts/Fleece |
| Enchant | Tier, rareza, stats y bonos realmente equipados | Rerolls repetidos o asumir que un reroll sube su tier/rareza |

**Elegir por el comportamiento, no por el nombre de rareza:** un pet defensivo
puede sostener al grupo, pero depende del disparador y del efecto. La wiki
distingue `when you get hit`, `when you hit`, `per turn`, balanced y `upon death`.
No comparar dos porcentajes sin contar cuántas oportunidades reales tienen de
dispararse. Team heal, spread heal y self heal no son el mismo objetivo. Ejemplos
comunitarios: Wormie cura al equipo por turno; Urgoff usa spread heal; Skulldemort
cura al compañero de menor salud. No se recomienda comprarlos aquí. [W15][W19]

La wiki atribuye la potencia del efecto del pet a Power del jugador; no asumir
que equipar al héroe un accesorio ofensivo aumenta directamente el modificador
propio de todos los familiares. Los augments y Stable de ellos se comprueban
aparte. Hay excepciones e interacciones de efectos de equipo: registrar tooltip,
disparador y objetivo, no simular una cadena ilimitada por intuición. [W19][W20]

**Montura: movimiento no es velocidad de combate.** La wiki separa el movimiento
adicional del bono Speed aplicado a turnos; también publica una habilidad única
usable **una vez por adventure**, no una por batalla. Ejemplos: Genbu da escudos;
Spirit aporta SP; Freeagle ataca al enemigo más débil. Comprobar si Auto usa la
habilidad y cuándo antes de añadir un clic manual: no quedó probado aquí. [W17]
No contar una montura cosmética de cero stats como mejora ni aplicar la tabla
de reroll a una mythic con bono fijo o a una montura de tienda no rerolleable.

**Enchants sí tienen rutas de drop:** la wiki cita Zones, Raids, Trials/Gauntlet,
World Boss y ciertos cofres; Item Find afecta enchants según soporte. Los normales
aportan stats/bonos y tienen tier/rareza fijos: reroll cambia atributos, no los
asciende, y aumenta el coste con sucesivas repeticiones. Los mythics se tratan
aparte y la wiki dice que no son rerolleables. No extrapolar sus cifras históricas
a la versión actual. [O8][W18]

Si falta un objeto, perseguir primero su **fuente confirmada**, no gastar energía
buscando una mascota de Shop como si fuese un familiar de zona. La rotación
oficial publicada en junio de 2025 alterna semanas A (Pet Eggs) y B (Accessory
Boxes), con recursos los miércoles y reset semanal los jueves. Descuento no
significa oro ni autorización para comprar: la tienda real manda. [O17]

El soporte clasifica armas, mascotas y monturas como ejemplos de **Hero Bound**;
Gold/Gems y ciertos boosts son **Player Bound**. Registrar la etiqueta del objeto
y el héroe activo: una misma cuenta no convierte todos sus inventarios en uno
solo. No cambiar héroe automáticamente para ampliar presupuestos. [O19]

### Criterios de build por etapa: propuesta, no tier list garantizada

| Etapa confirmada de la cuenta | Preparación razonable del farmeo |
| --- | --- |
| T1–T3 | Validar supervivencia, curación y copias iniciales; Bor'lan/Shrampz son objetivos de referencia si faltan sus funciones |
| T4–T6 | Separar gear del tier actual de rutas anteriores de ingredientes; revisar roster de raid y pet/accesorio disponibles |
| T7+ | Comparar bonos de sets/mythics y restricciones de la actividad; no romper una sinergia por más TS |
| Contenido elemental | Leer resistencias, elemento de skills y enemigo; el artículo oficial sitúa su introducción en Zone 10+/T11+ |

Tank (frente), bait (recibe ataques dirigidos al débil), DPS y soporte no son
builds intercambiables. Son roles de composición: un bait puede necesitar menos
HP que sus compañeros y aun así suficiente mitigación; subirle HP sin mirar los
objetivos enemigos puede quitarle su función. La recomendación depende de roster,
skills y actividad, no solo tier. Bitcademy incluye una guía específica de roles;
su índice se comprobó, no se visionaron todos sus vídeos ni se certificó su meta
para esta cuenta. [O18]

El bot repetidor no necesita resolver un optimizador de combate: outfit aprobado,
runas de recurso apropiadas y **victorias medidas** son la primera base. Guardar
también pet, accessory, mount y enchants con ese perfil para poder explicar un
cambio en las derrotas. Una victoria aislada no prueba que la build sea estable.

### Elementos: no sumar porcentajes sin comprobar eficacia

El FAQ oficial describe daño/resistencia coincidente como 100% efectivo,
neutral/fuerte como 75% y débil como 0%. DR físico tiene eficacia completa contra
Physical y 75% contra daño elemental; por tanto, no equivale a resistencia completa
a todos los ataques. El artículo también incluye mascotas y familiares. [O16]

**Discrepancia:** soporte habla de límite de 75% por resistencia; Mechanics
publica un límite aplicado a la suma efectiva. Además, el FAQ oficial conserva
la frase antigua «solo Water, Electric y Physical» junto a una lista que incluye
Fire/Earth/Air. No implantar un simulador ni rechazar piezas por estos supuestos
sin contrastar el cliente y una mecánica actual; el repetidor puede usar una
composición que ya funciona sin resolver esa discrepancia. [O16][W19]

## 6. Configuración para reducir errores y carga visual

**Lista a comprobar, no contrato de UI:** Settings está marcada como candidata
a eliminación; incluso marca alguna opción como ausente en Unity. [W9]

| Ajuste, si existe | Recomendación inicial | Motivo/límite |
| --- | --- | --- |
| Auto pilot | Activado en la run aprobada | Reutilizar combate/movimiento nativo |
| Auto-persuade with gems | Desactivado en todas las rarezas | Impedir gasto nativo sin clic del bot |
| Auto-persuade with gold | Desactivado si el bot elige nombres/presupuesto | Evitar gasto duplicado o familiares ajenos |
| Decline duplicate familiars | Desactivado para rutas de copias | Conservar objetivo de Stable/fusión |
| Ignore boss | Desactivado para completar la dungeon | No dejar la run sin finalizar |
| Ignore shrines | Desactivado inicialmente | No quitar curación/SP útil por ahorrar segundos |
| Disable auto pilot on death | Activado al validar la ruta | Detectar fracaso; no reactivar Auto sin revisar |
| Decline merchants | Rechazar ofertas de pago compatibles con el perfil | No confundir merchant con Shop de reposición |
| Decline treasures | Revisar efecto sobre cofres de pago | No ocultar indiscriminadamente botín gratuito |
| Reduced effects | Probar activado | Menos partículas/destellos; medir, no prometer FPS |
| Battle/Victory animations | Probar desactivadas si siguen siendo detectables los estados | Menor carga visual; nuevas referencias visuales |
| Notifications/World chat | Proponer desactivación durante farmeo | Menos superposiciones; mensajes privados pueden seguir |
| Duel/World Boss requests | Proponer desactivación durante repetición | Evitar invitaciones que cambian la pantalla |
| Battle text/status bars | Según las señales utilizadas por el clasificador | No ocultar datos que el bot necesita |
| Windowed/resolución/escala | Conservar geometría soportada | El backend actual exige Steam 1920×1080, escala 1 |

No cambiar apariencia, compositor, SDDM ni todos los ajustes como optimización
incidental. Registrar estado antes/después y validar las capturas con **esa**
configuración. Desactivar animaciones no autoriza eliminar esperas de carga ni
clicar antes de que el botón esté estable. Capturas frescas y guardia de foco
siguen siendo obligatorias.

## 7. Energía, mejores recompensas y elección de dificultad

La tabla histórica de Zones publica 10 energía Normal, 20 Hard/Especial y 30
Heroic, con bonos crecientes de XP/oro/captura y de Item Find. No codificar estas
cifras como contrato: confirmar coste, multiplicador y bonos visibles. [W7]

Heroic puede ser buena opción **si se gana consistentemente**; más bono por
run no prueba más rendimiento por energía ni una ruta concreta mejor. Una
dungeon anterior puede ser correcta para el familiar, e incorrecta para equipo
del tier actual. Las especiales mezclan enemigos y algunas añaden restricciones.

Comparar rutas con el mismo objetivo y condiciones:

- Familiares: ofertas del nombre, éxitos e ingredientes obtenidos / recurso.
- Equipo: piezas útiles del tier/set objetivo / recurso, no todo lo obtenido.
- Oro: ganancias confirmadas menos Persuade, reposición y demás costes.
- XP: XP de resultados completos / recurso, y por minuto total.
- En todos: tiempo de menús/carga, derrotas, consumibles y runs incompletas.

No convertir un puñado de runs sin drop en «ruta imposible» ni en porcentajes
exactos. Guardar tamaño de muestra y condiciones; tasas de objetos raros necesitan
muchas observaciones. Item Find mejora calidad/rareza, no cantidad indiscriminada
y no todos los materiales. Capture Rate no sustituye Item Find ni Persuade. [O8][W8]

Bonos diarios: aprovechar captura cuando esté activa para familiares; Item Find
para equipo; oro/XP según objetivo. Leer bono y reset del juego, no solo el día
del ordenador. Bounties y eventos pueden añadir valor a una ruta ya apropiada.
No guardar tanta energía que se pierda regeneración al llegar al máximo, salvo
una reserva elegida para otro objetivo. Releer saldo entre runs; esperar no da
permiso para recargas/conversiones.

**Multiplicadores xN:** no recomendar el mayor automáticamente. Falta comprobar
qué multiplica (coste, recompensas, encuentros/ofertas de familiares, bounties)
y qué se pierde al fallar. Empezar con el valor más bajo disponible y validado
para la actividad; comparar después. No contar una entrada xN como N victorias
observadas ni asumir N oportunidades de captura.

### Fuente y dificultad válidas antes de comparar rendimiento

| Si falta… | Actividad candidata | Recurso que hay que presupuestar |
| --- | --- | --- |
| Componente de fusión de una zona | Dungeon concreta de la receta | Energy; no convertirla automáticamente |
| Pieza Ares Legacy/Divinity/M.A.R.U | Raid de su tier/fuente | Shards; roster no es una sala en vivo |
| Hobbit Foot/Demon Juice | Orlag Clan/Netherworld | Xeals; sala, Ready y límite de espera propios |
| Runa/fragmentos como premio de evento | PvP, Trials/Gauntlet u otro premio verificado | Tickets/Tokens/Badges según actividad, no Energy universal |

La wiki de World Boss restringe las rarezas por tier/dificultad: su sección
Tiers publica sets T6 en Heroic y T7+ en Hard/Heroic, y mythics T7+ en Heroic.
La lista Possible Drops de la **misma página** es menos precisa para T6.
Tratarlo como advertencia para verificar el selector/tabla actuales, no como
contrato universal. Además, su lista de bosses omite Gallus Apotheosis, incluido
en el artículo oficial de 2026. [W14][O15]

Para materiales que aparecen en cualquier dificultad según la wiki, la elección
inicial es la dificultad que gana sin gasto excepcional, no Heroic por reflejo.
Si el objetivo es una pieza que solo aparece en otra dificultad, la ruta fácil
no sirve aunque termine más rápido. Registrar conjuntamente boss, tier,
dificultad, fuente del premio (drop/milestone/evento) y resultado antes de calcular
«mejor botín por recurso». No cambiar de modo al agotarse su saldo sin permiso.

### Multiplicadores y bonos: evidencia nueva y límites

La FAQ comunitaria enumera efectos del Loot multiplier dependientes del modo:
oro, equipo, schematics, materiales de fusión, determinados materiales mythic,
enchants/augments no mythic, ciertas pociones, cosméticos y moneda de evento.
**No enumera oportunidades de familiar**; esa ausencia no prueba que no cambien,
pero tampoco permite afirmar N oportunidades con xN. El buscador del soporte
no devolvió un artículo de multiplicadores en esta consulta. Sigue pendiente
comprobar ese punto; no inventar una tasa para cerrar el hueco. [W20]

Bonuses publica una fórmula de Item Find y **admite asumir** que otros bonos
funcionan de forma semejante. Su ejemplo suma componentes que dan 435 y después
utiliza 535 para calcular 2.675: no copiar el resultado como calculadora validada.
El supuesto cap de 3.500% está atribuido a una actualización de 2020, no comprobado
en esta cuenta de 2026. Leer los bonos mostrados y medir recompensas. [W21]

**Otra discrepancia importante:** soporte excluye «crafting materials» de Item
Find; FAQ/Bonuses dicen que materiales mythic como Mud, Pinion, Fleece, Collar y
Curio sí se benefician. Los materiales básicos y los de fusión no deben mezclarse
con esa posible excepción. Hasta contrastarla, no activar un boost escaso ni
calcular rentabilidad de esos materiales con una regla global. [O8][W20][W21]

El reset semanal de tienda/eventos no es necesariamente el mismo que el cambio
de bono diario. La FAQ cita medianoche GMT+0 para bonos; soporte de la rotación
cita jueves para reset semanal. Son referencias distintas que aún requieren
validar el temporizador correspondiente en el cliente. [W20][O17]

### Fuente audiovisual adicional, identificada sin fingir visionado

**Bitcademy** es una página de la web oficial con vídeos de su programa de
creadores. Útil para contrastar preparación y escenas reales antes de ampliar
el bot; autor de vídeo no equivale a contrato oficial vigente. [O18]

- [Dungeons, boosts y D4](https://www.bitheroesquest.com/bitcademy#farm_dungeons).
- [Mascotas, accesorios y monturas](https://www.bitheroesquest.com/bitcademy#accessories_mounts_pets).
- [Runas y enchants](https://www.bitheroesquest.com/bitcademy#runes_and_enchants).
- [Roles y equipo de mid/late game](https://www.bitheroesquest.com/bitcademy#meta).
- [Oro, gemas y energía](https://www.bitheroesquest.com/bitcademy#gold_gems_energy).

Se consultó la página/índice y algunos extractos indexados por búsqueda. No se
descargaron todos los vídeos ni se cuenta su contenido íntegro como verificado.
Es una línea concreta para seguir investigando, no señal de que ya se agotaron
las fuentes públicas. La ruta óptima de la cuenta requiere además tier, roster,
inventario y resultados observados, que siguen sin comprobarse aquí.

## 8. Consumibles comunes y reposición solo con oro

### Catálogo inicial de candidatos

Precios base y efectos **comunitarios**, no confirmados en la tienda de esta
cuenta. Stock, moneda, descuentos y nombre exacto mandan sobre esta tabla. [W11][W12]

| Artículo | Efecto publicado | Coste base citado | Política propuesta |
| --- | --- | --- | --- |
| Minor Gold Potion | +25% Gold Find, 24 h | 5.000 oro | Candidato perfil oro, si no reemplaza otro boost |
| Minor Item Find Scroll | +25% Item Find, 24 h | 10.000 oro | Candidato equipo/conjuntos |
| Minor Experience Tome | +25% XP, 24 h | 10.000 oro | Candidato perfil XP |
| Minor Speed Kicks | +25% movimiento, 24 h | 5.000 oro | Opcional si ahorra tiempo medido; no es velocidad de combate |
| Minor Healing Potion | Recupera 40% HP | 500 oro | Solo si se aprueba uso de pociones; no cura automáticamente |
| Minor Revive Potion | Revive y recupera 40% HP | 1.000 oro | Desactivado por defecto; no sostener una ruta que falla |

**Conflicto encontrado:** Average Healing Potion aparece a 5.000 oro en
Consumables y a 10.000 en Shop. No incluirla con precio fijo hasta comprobarla.
Average/Major no significa «oro»: muchos boosts de esas categorías cuestan gemas.
No se verificó un boost de captura barato y permanente en tienda por oro; para
familiares usar Quindi/bonos disponibles antes de inventar una reposición equivalente.

La wiki limita las pociones de combate a ciertos modos y a una por unidad por
adventure. Validar restricciones y contador del cliente; no intentar curar/revivir
repetidamente cuando el objeto ya no puede utilizarse. [W11]

### Qué conservar

Por defecto bloquear consumibles de energía/shards/xeals y otros recursos,
boosts potentes o de evento (p. ej. Bitgor/Ultragor/Capgor), Super Scroll,
Super Potion, esquemas consumibles, llaves y objetos cuya reposición use gemas,
dinero, honor de gremio o moneda de pesca. No son «comunes y reponibles» por
aparecer en inventario. Un precio de cero/no reconocido no es permiso para consumir.

Dos boosts consumibles que comparten atributo no se acumulan: el nuevo puede
**reemplazar** el anterior y muestra aviso. No activar un Minor encima de un boost
escaso vigente ni aceptar la advertencia. Bonos diarios y Adgor son sistemas
distintos; el soporte dice que Adgor se suma a boosts y bonos, pero Steam no
permite anuncios para activarlo. No comprar Permagor ni cambiar/conectar cuentas
para solventarlo; considerar solo lo ya activo. [O6][O7]

### Reposición acotada

1. Lista explícita de artículos permitidos; cantidad objetivo, reserva de oro,
   techo por artículo/sesión y número máximo de compras.
2. Reponer entre runs, no durante un diálogo parecido; si el artículo es un boost
   de 24 horas, no comprar/consumir uno por dungeon.
3. Comprobar artículo completo, **icono de oro**, precio total y cantidad. Un
   botón verde o la palabra Buy no identifican la moneda.
4. No buscar «algo parecido» si se agota; parar o continuar sin boost según perfil.
   No usar Flash Sale como prueba de moneda ni aceptar packs/ofertas premium.
5. Comprar una vez y verificar inventario/saldo/estado. Si la confirmación es
   ambigua, observar y pausar; no repetir la compra.
6. Bloquear gemas/dinero/conversiones aun con saldo suficiente. Presupuesto
   compartido de oro para Persuade y reposición, no dos límites independientes
   que puedan consumir la misma reserva.

Un boost de oro también debe amortizarse. A modo de cálculo, no de mecánica
verificada: si realmente añade 25% sobre una base y cuesta 5.000, requiere más de
20.000 oro base durante su duración para dar beneficio positivo. Con otros bonos
o fórmulas distintas, medir la ganancia marginal real. Para captura/equipo, fijar
un presupuesto aceptado, no prometer retorno monetario.

## 9. Conteo de botín por run y sesión

Guardar un registro por aventura física; no limitarse a «runs = 100».

| Grupo | Campos recomendados |
| --- | --- |
| Identidad | session_id, adventure_id, héroe local, cliente, fecha, versión del lector |
| Contexto | perfil, modo/zona/dungeon/raid, dificultad, tier, multiplicador, equipo/runas/boosts |
| Resultado | entrada confirmada, victoria/derrota/incompleta, duración y motivo de cierre |
| Recursos | tipo/coste visto, saldo antes/después, regeneración/recompensas separadas |
| Ganancias | oro bruto y XP visibles; gemas/materiales/consumibles obtenidos si se leen |
| Gastos | Persuade, compras y objetos consumidos; oro neto separado del bruto |
| Equipo | nombre, cantidad, rareza, slot, tier, conjunto y pieza nueva/duplicada |
| Familiares | nombre, ofertas, intentos, resultado y copias pendientes por receta |
| Evidencia | recorte local, lectura original y estado confirmado/estimado/desconocido |

La diferencia de saldo no es por sí sola oro obtenido: también hay gastos y
otras recompensas. XP antes/después requiere controlar subidas de nivel; una
barra que vuelve a cero no implica XP negativa. Preferir valores explícitos del
resultado y registrar lo no visible como `null/desconocido`, **no cero**.

Un único resultado puede tener varias páginas, tooltips o recompensas durante
combate. Asignar identidad de aventura al entrar, registrar páginas/ítems una
sola vez y confirmar cierre. No deduplicar solo por imagen: dos runs legítimas
pueden dar resultados idénticos. Tras reinicio, una victoria ya abierta no
cuenta como una aventura nueva del bot.

Si el resumen no muestra nombre/tier/conjunto, el conteo completo requiere
tooltips o lectura de inventario entre runs, no inventarlo por color. Evitar
doble conteo entre drop emergente y resumen final. Un lector incierto puede
continuar solo con datos parciales si no autoriza gasto; decisiones de gasto
con precio/saldo inciertos se bloquean.

Panel/resumen: victorias/derrotas/incompletas, recurso total, oro bruto/gastado/neto,
XP, familiares por nombre, piezas por rareza/tier/conjunto, colección antes/después
y motivo de parada. JSONL local como registro inicial y CSV de resumen son
suficientes; no hace falta servidor o dashboard web. El proyecto ya tiene
[telemetría JSONL/CSV](../fishing_core/telemetry.py): revisar y reutilizar lo útil,
sin reutilizar campos CATCH como si fueran botín de dungeons.

## 10. Python frente a Java y otras opciones

**Decisión propuesta, no migración aprobada: conservar Python como controlador
y el pequeño adaptador nativo existente.** No hay benchmark comparativo ni evidencia
de que cambiar el lenguaje mejore este nuevo flujo.

Base local inspeccionada: Python 3.13 declarado, OpenCV/NumPy/Pillow/MSS,
python-xlib en Linux, interfaz Tk, pruebas y telemetría. Steam/niri utiliza captura
de ventana XWayland, guardia de foco/identidad y un pequeño puntero Wayland en C.
No es un proyecto Java que haya que rescatar. [L1][L2][L3][L4]

| Opción | Ventaja relevante | Coste/límite para este proyecto | Recomendación |
| --- | --- | --- | --- |
| Python actual | Reutiliza visión, backend, pruebas y UI; rápido para verificar pantallas | Evitar bucles de píxeles Python y OCR completo por frame | Mantener para el primer bot de farmeo |
| Java | Tipado estático, ecosistema JVM, Robot y bindings OpenCV | Reescribir contratos/UI/pruebas; Robot depende del SO/compositor; bindings nativos siguen existiendo | Considerar si se necesita plataforma JVM o un prototipo demuestra ventaja real |
| C++/Rust | Buen control e integración nativa; útiles para un cuello de botella específico | Mayor coste de bindings, construcción y mantenimiento; no arreglan tablas ni OCR por sí solos | Optimizar solo el componente medido si hace falta |
| C# | Candidato si el destino cambia a una aplicación Windows/.NET | Aquí el destino es CachyOS/niri; cambiar lenguaje no resuelve Wayland | No migrar sin ese nuevo requisito |
| JavaScript/TypeScript | Útil para UI o pruebas de navegador con DOM real | Steam y el contenido visual Unity no son botones DOM ordinarios | No reemplaza el backend de escritorio |

OpenCV documenta que sus bindings Python llaman algoritmos C++; Java también
usa bindings. Reescribir llamadas `cv2.matchTemplate` en Java no convierte por sí
solo ese cálculo nativo en algo más rápido. NumPy libera el GIL en muchas
operaciones; eso no elimina los costes de captura, copias u OCR. [T1][T2][T3]

`java.awt.Robot` puede capturar/generar input, pero su documentación advierte de
restricciones, permisos y funcionalidad degradada según escritorio; en X11
requiere XTEST. **No quedó probada su compatibilidad con este niri/XWayland.**
El backend local ya documenta que XTEST no mueve el cursor en este entorno y
por eso usa el protocolo de puntero Wayland. Java también necesitaría verificar
esa integración, no asumir «multiplataforma» como garantía. `waitForIdle()` espera
la cola AWT, no confirma que Unity haya terminado una transición. [T4][L1][L3]

Para decidir una migración: usar las mismas capturas y tareas; medir captura,
visión/OCR, CPU/RAM, latencia p50/p95, errores de clasificación, foco/parada y
tiempo de una run completa. **Primero medir → optimizar recortes/cadencia/copias
→ prototipo del componente → migrar solo si supera la base sin perder guardas.**
No rebajar comprobaciones de gasto, inventario o F8 para ganar velocidad.

## 11. Herramientas, plugins e IAs: mejorar con lo ya disponible

Comprobación local de solo lectura al investigar:

- La `.venv` contiene NumPy 2.5.3, OpenCV 5.0.0.93, Pillow 12.3.0, MSS 10.2.0
  y python-xlib 0.33, conforme a los requirements inspeccionados.
- Están disponibles `uv`, `tesseract`, `cc`, Git, Steam y Brave en PATH. Que
  Tesseract exista **no demuestra** que lea todo el juego. La prueba offline
  limitada de abajo comprueba algunos recortes, no el botín de una dungeon.
  No se encontró `java` en PATH; no se instaló un JDK para una comparación especulativa.
- OpenCode tiene herramientas de archivos, búsqueda web, shell y subagentes;
  el plugin Ponytail V2 figura activo. El MCP consultado conectado es Graphify.
  Plugins de proveedores registrados no equivalen a cuentas conectadas/modelos utilizables.
- Se intentaron dos revisiones independientes de lectura (lenguajes y mecánicas),
  pero ambas terminaron con **usage limit**: no se cuenta ninguna como revisión
  completada ni se afirma consenso entre IAs.

Mejoras recomendadas al desarrollador:

1. **Capturas anotadas y reproducción offline** para estados, textos, precios y
   resultados. Más valioso que otro plugin genérico o una IA improvisando clics.
2. Reutilizar OpenCV para pantalla/iconos y el lector de dígitos donde sea válido;
   ensayar Tesseract ya instalado sobre recortes de texto variable. Adoptarlo
   solo si supera un conjunto etiquetado; no requiere instalar otro wrapper por rutina.
3. Un solo proceso propietario del input y una única ventana. Paralelizar
   investigación/pruebas de archivos, **no dos bots clicando Steam y Brave**.
4. Revisiones independientes de presupuestos, cero gemas, resultados duplicados y
   parada cuando haya cuota. No asumir que Claude/DeepSeek u otro modelo es gratis
   o accesible; no cambiar proveedor/credenciales sin petición específica.
5. Graphify solo sobre un grafo existente relevante. No se encontró grafo en este
   proyecto; no indexar la carpeta personal/bóveda para llenar ese hueco.
6. Añadir un plugin/app únicamente cuando falte una capacidad demostrada:
   compatibilidad OpenCode V2, fuente/licencia, permisos, coste y prueba mínima
   antes de activarlo. Respaldar configuración y conservar la ajena. [T5]

No se instalaron plugins/apps, no se conectaron proveedores ni se ejecutaron
otros bots. Las fuentes oficiales son datos; no autorizan acciones por sus ejemplos.

### Prueba de OCR offline realizada, no integración en el bot

Se utilizó una [captura de inventario de pesca ya existente](../runs/20261002_123645_7c3d61d775ff/bait_inventory_last.png),
de 840×580, sin capturar pantalla nueva ni enviar input. SHA-256 del archivo:
`f13254fddbd50f91a06adba7caea12eb948e730d801bf2f74b60778b70a6aa31`.
Es evidencia local en `runs/`, no una fixture garantizada en el repositorio remoto.
Tesseract **5.5.3**, idioma `eng`, `--psm 7`; solo las cantidades/control vacío
usan whitelist de dígitos. `eng`, `spa` y `osd` están instalados.

Cinco recortes con etiquetas leídas visualmente; dos variantes y tres ejecuciones
por variante. Preparación: blanco neutro (`mínimo RGB >= 210`) a tinta negra,
resto a blanco, ampliación nearest-neighbor 2× y borde blanco de 10 px. [T6]

| Recorte/etiqueta | Tesseract original | Tesseract preparado | Lector existente |
| --- | --- | --- | --- |
| Cantidad `2` | `2` | `2` | `2` |
| Cantidad `13` | **`3`, incorrecto** | `13` | `13` |
| Cantidad `8` | `8` | `8` | `8` |
| Título `SELECT` | `SELECT` | `SELECT` | No evaluado: el lector es de cantidades |
| Región vacía, sin texto | Cadena vacía | Cadena vacía | No aplicable: no es una tarjeta ocupada |

Cada salida fue igual en sus tres repeticiones. Son **cinco recortes de una
imagen**, no quince muestras independientes ni una tasa general de precisión.
Las medianas por recorte/variante estuvieron entre **92 y 108 ms** invocando el
ejecutable por separado; incluyen iniciar el proceso y OCR, no captura ni
preprocesado. No se midió una implementación persistente, Java ni una run entera.

Conclusión: no sustituir el lector que ya acierta; ensayar Tesseract para nombres
o textos variables sobre un conjunto nuevo etiquetado. Una whitelist permite
dígitos, **no detecta por sí sola** que falta el `1` de `13`. La máscara fija solo
sirve para estos recortes de texto blanco: no aplicarla a nombres por color,
texto gris, precios, animaciones o fondos distintos sin comprobarlos.

`BaitReader.quantity()` solo se probó en las tres tarjetas conocidas. Su regla
sin dígitos → una unidad pertenece a ese inventario; **no reutilizarla para
saldo/precio/XP ni región vacía**. Para ellos vacío/ilegible sigue siendo
desconocido, nunca cero ni uno. [L5] Faltan capturas de premios, tooltips,
diálogos de gasto y casos negativos parecidos a una lectura válida.

Comprobación mínima reproducible desde la raíz del proyecto, con la captura
local presente. Solo lee el archivo, prepara cinco recortes e invoca OCR:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import subprocess
from pathlib import Path
import cv2
import numpy as np

path = Path('runs/20261002_123645_7c3d61d775ff/bait_inventory_last.png')
image = cv2.imread(str(path))
assert image is not None and image.shape[:2] == (580, 840)
cases = [((125, 201, 206, 241), '2'), ((279, 201, 360, 241), '13'),
         ((433, 201, 514, 241), '8'), ((265, 38, 540, 101), 'SELECT'),
         ((550, 201, 631, 241), '')]
for (x0, y0, x1, y1), expected in cases:
    crop = image[y0:y1, x0:x1]
    pixels = np.where(crop.min(axis=2) >= 210, 0, 255).astype(np.uint8)
    pixels = cv2.resize(pixels, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    pixels = cv2.copyMakeBorder(pixels, 10, 10, 10, 10,
                               cv2.BORDER_CONSTANT, value=255)
    ok, png = cv2.imencode('.png', pixels)
    assert ok
    command = ['tesseract', 'stdin', 'stdout', '-l', 'eng', '--psm', '7']
    if expected != 'SELECT':
        command += ['-c', 'tessedit_char_whitelist=0123456789']
    result = subprocess.run(command, input=png.tobytes(), capture_output=True,
                            check=True, timeout=10)
    observed = result.stdout.decode().strip()
    assert observed == expected, (expected, observed)
print('5 recortes preparados OK; no certifica OCR general ni autoriza gasto')
PY
```

## 12. Siguiente trabajo verificable para el otro OpenCode

1. Confirmar **tier, objetivo, inventario, ruta y presupuesto** con la cuenta;
   capturar configuración y pantallas sin gasto automático.
2. Implementar un perfil y una dungeon repetible conocida; campos de botín
   parciales honestos antes de prometer reconocimiento completo del inventario.
3. Añadir familiar por nombre y cantidades cuando ofertas/costes/resultados
   estén reconocidos; después completar lector de piezas/tier/set.
4. Añadir boosts comunes/reposición oro como política separada, después de
   verificar tienda y exclusión de moneda premium. No simular compras reales para probarla.
5. Comparar dificultad/ruta con datos registrados; ampliar a Raid/World Boss
   solo con sus propios recursos y estados comprobados.

Pruebas mínimas: nombre/moneda/precio/saldo inciertos no autorizan gasto; gemas
nunca se aceptan; un boost común no reemplaza uno escaso activo; duplicados útiles
no se rechazan; presupuesto compartido respeta reserva; resultado se cuenta una
vez aunque haya varias páginas/reinicio; F8/foco perdido bloquean input.

**No certificado aquí:** pantallas actuales, óptimo para la cuenta, precios/stock,
efecto de multiplicadores en capturas, tasas raras, OCR de todo el botín y
funcionamiento del nuevo bot. Esta ampliación no modifica el riesgo de sanción
por automatización documentado en la guía base.

## 13. Referencias

Soporte consultado por sus artículos/API; la mayoría muestra actualizaciones
de marzo de 2025 y puede no reflejar todas las novedades de 2026. Excepciones:
fabricación accidental, junio de 2025 [O13]; devolución de fundidos, julio de
2026 [O12]; Supercharged Ancient Gear, mayo de 2026 [O15].
La rotación de tienda se actualizó en junio de 2025 [O17]; Hero/Player Bound,
agosto de 2025 [O19]. Bitcademy es una colección de guías, no changelog de 2026.
La wiki es secundaria y tuvo respuestas HTTP 403 intermitentes. No se copiaron
catálogos completos, imágenes o código de otros bots.

[O1]: https://bitheroes.zendesk.com/hc/en-us/articles/360038947952-What-are-Runes
[O2]: https://bitheroes.zendesk.com/hc/en-us/articles/360041363752-What-are-Schematics-and-Where-do-I-find-them
[O3]: https://bitheroes.zendesk.com/hc/en-us/articles/360032334891-How-do-I-use-the-stable
[O4]: https://bitheroes.zendesk.com/hc/en-us/articles/360037612911-Armory
[O5]: https://bitheroes.zendesk.com/hc/en-us/articles/360042096951-Where-do-I-craft-Set-Chests
[O6]: https://bitheroes.zendesk.com/hc/en-us/articles/360032334791-Can-I-have-multiple-consumable-bonuses-active-Do-consumable-bonuses-stack
[O7]: https://bitheroes.zendesk.com/hc/en-us/articles/360044020932-Adgor-Permagor-Boosts
[O8]: https://bitheroes.zendesk.com/hc/en-us/articles/360038943972-What-is-Item-Find-and-how-does-it-work
[O9]: https://bitheroes.zendesk.com/hc/en-us/articles/360031993512-How-do-I-unlock-new-areas
[O10]: https://bitheroes.zendesk.com/hc/en-us/articles/360032335011-What-is-material-How-do-I-get-better-rarity-material
[O11]: https://bitheroes.zendesk.com/hc/en-us/articles/360039344691-Crafting-Upgrade-Exchange-Trade-Reforge
[O12]: https://bitheroes.zendesk.com/hc/en-us/articles/35191968802317-I-accidentally-melted-an-item
[O13]: https://bitheroes.zendesk.com/hc/en-us/articles/37733737103117-I-accidentally-crafted-an-item
[O14]: https://bitheroes.zendesk.com/hc/en-us/articles/30402850010509-How-to-Craft-Ancient-Equipment-such-as-Starweave
[O15]: https://bitheroes.zendesk.com/hc/en-us/articles/45627293971469-Supercharged-Ancient-Gear
[O16]: https://bitheroes.zendesk.com/hc/en-us/articles/360039253311-Elemental-Gear-FAQ
[O17]: https://bitheroes.zendesk.com/hc/en-us/articles/37167619946125-Weekly-Shop-Rotation
[O18]: https://www.bitheroesquest.com/bitcademy
[O19]: https://bitheroes.zendesk.com/hc/en-us/articles/38945210912141-What-are-Player-Bound-items-and-Hero-Bound-items
[W1]: https://bit-heroes.fandom.com/wiki/FusionByLocation
[W2]: https://bit-heroes.fandom.com/wiki/Zones/Bit_Valley
[W3]: https://bit-heroes.fandom.com/wiki/Zones/Wintermarsh
[W4]: https://bit-heroes.fandom.com/wiki/Runes
[W5]: https://bit-heroes.fandom.com/wiki/Equipment
[W6]: https://bit-heroes.fandom.com/wiki/Equipment/Set
[W7]: https://bit-heroes.fandom.com/wiki/Zones
[W8]: https://bit-heroes.fandom.com/wiki/Familiar
[W9]: https://bit-heroes.fandom.com/wiki/Settings
[W10]: https://bit-heroes.fandom.com/wiki/Augment
[W11]: https://bit-heroes.fandom.com/wiki/Consumables
[W12]: https://bit-heroes.fandom.com/wiki/Shop
[W13]: https://bit-heroes.fandom.com/wiki/Materials
[W14]: https://bit-heroes.fandom.com/wiki/World_Boss
[W15]: https://bit-heroes.fandom.com/wiki/Pets
[W16]: https://bit-heroes.fandom.com/wiki/Accessories
[W17]: https://bit-heroes.fandom.com/wiki/Mounts
[W18]: https://bit-heroes.fandom.com/wiki/Enchants
[W19]: https://bit-heroes.fandom.com/wiki/Mechanics
[W20]: https://bit-heroes.fandom.com/wiki/Frequently_Asked_Questions
[W21]: https://bit-heroes.fandom.com/wiki/Bonuses
[T1]: https://docs.opencv.org/4.x/da/d49/tutorial_py_bindings_basics.html
[T2]: https://docs.opencv.org/4.x/d9/d52/tutorial_java_dev_intro.html
[T3]: https://numpy.org/doc/stable/reference/thread_safety.html
[T4]: https://docs.oracle.com/en/java/javase/25/docs/api/java.desktop/java/awt/Robot.html
[T5]: https://opencode.ai/v2/docs/build/plugins
[T6]: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
[L1]: LINUX.md
[L2]: ../requirements.txt
[L3]: ../fishing_core/linux.py
[L4]: ../fishing_core/linux_pointer.c
[L5]: ../fishing_core/bait_inventory.py

El tutorial Java de OpenCV advierte que puede estar obsoleto: se usa para
documentar existencia de bindings/biblioteca nativa, **no** para instalar sus
versiones históricas de JDK/Ant/SBT. La página NumPy estable consultada muestra
v2.5; la API de Robot citada es Java SE 25. No se cambió ninguna versión local.
