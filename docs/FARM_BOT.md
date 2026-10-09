# Bit Heroes Farm Bot — primera entrega local

`./ABRIR_BOT.sh` abre **Dungeons** primero y **Fishing** segundo. Abrir no inicia
una aventura. Se conserva el acceso de pesca `FISHING_BOT_APP.py`, sus motores,
preferencias y Windows; el runner de dungeon es por ahora **Steam/niri**.

## Disponible

- Catálogo local: 77 dungeons de 20 zonas y 220 familiares con rutas de captura
  de la wiki, consultada el 2026-10-02. No garantiza contenido posterior.
- Selección directa o búsqueda exacta del familiar: Bob/Shrump → Z1D2.
  Fusiones y nombres desconocidos no se sustituyen por otra ruta.
- Primera ruta calibrada: **Z5D2 · Zorul's Gauntlet · Normal · 10 energía**.
  Segunda: **Z5D3 · Tealk's Palace · Heroic · 30 energía**, solo **1 run/sesión**
  hasta validar repetición. Una prueba supervisada no certifica autonomía completa.
  Selecciona Aramore mediante **Zones** si Quest muestra otra zona; confirma
  el título antes de buscar el nodo. Navegación de mapas Z1–20 comprobada.
  Otras dungeons/dificultades se rechazan antes de iniciar, sin sustituir la ruta.
- Límites finitos de runs/energía y 15 minutos/sesión; máximo 3 min/dungeon.
  Intención duradera antes de ACCEPT; nunca repetir un clic incierto ni contar
  una recompensa antes de confirmar Town → mapa → Home.
- Comprobación de auto-Persuade GOLD y auto-Bribe GEMS desactivados antes de
  entrar; no se cambian esos ajustes ni equipo. Si se busca un familiar y está
  activo Decline duplicate familiars, se bloquea antes de gastar energía.
- No usa motores de pesca para dungeons ni permite modos simultáneos. Captura
  Wayland, foco, cursor, F8 y exclusividad existentes se reutilizan sin relajarlos.

**F8 detiene el controlador y restaura el panel; el Auto nativo puede terminar
la dungeon ya iniciada.** No abre otra. No mover ratón/teclado ni compartir input
durante una prueba. Con objetivo seleccionado, otro familiar identificado se
rechaza mediante Decline → confirmación específica → cierre observado. Objetivo
o nombre desconocido: pausa sin Persuade/Bribe. Por ahora los nombres con referencia
exacta son **Mummih, Brute y Sitra**; no se usa OCR dudoso para decidir. Sin objetivo,
toda oferta pausa. Cada rechazo tiene intención duradera y no se repite si quedó
incierto. Un cierre incierto no se reanuda automáticamente.

## Oro autorizado, automatización pendiente

crzf autorizó gastar oro durante esta sesión. Se ejecutó únicamente Persuade de
Melvguin, con confirmación explícita **2.000 GOLD**. La oferta se cerró; el saldo
visible `9.94M` no permite certificar saldo exacto/delta y el resultado de
reclutamiento quedó **desconocido**, no se declara una captura exitosa.

El runner mantiene `max_gold=0`: autorización humana de oro no equivale a
activar gasto nativo, gemas, compras, recargas o consumibles. Pendiente lector
de moneda/precio/saldo, cuota compartida y selección de objetivos antes de
automatizar Persuade. El gasto supervisado está registrado aparte, no se suma
falsamente a `gold_reserved=0` del presupuesto automático.

## Evidencia real

- Exploración supervisada: primera Z5D2 Normal terminó **CLEARED**, con
  referencias de menús, equipo, Auto, historia y resultado. No modificó equipo.
- `20261002_140403_de6f4f3b6d2a`: parada segura desde mapa, sin inputs/entrada.
  Se corrigió el supuesto de que Town siempre vuelve directamente a Home.
- `20261002_140535_2e9cb0b5c5ab`: ajustes comprobados y llegada al equipo;
  parada antes de ACCEPT por lectura de energía. La barra TEAM tiene sombreado
  nativo al 50 %; se añadió un caso real sin reducir filtros de pantallas.
- `20261002_140836_70c52d4b0fe5`: una única entrada automática, saldo previo
  leído **337**, coste reservado **10**. Parada en carga inicialmente no
  etiquetada; después apareció Melvguin y se hizo el gasto supervisado autorizado.
  La misma dungeon terminó **CLEARED** y se cerró con cero entradas nuevas.
  `dungeon_resume_events.jsonl` registra la continuación supervisada; no es una
  función de reanudación automática ni otra sesión de farmeo.
- `20261002_141807_df80cbf262f4`: F8 real, **0 inputs y 0 entradas**; panel
  restaurado y duplicado LAUNCHER rechazado.
- `20261002_154802_ca83930eecdc`: **Z5D3 Heroic**, una entrada desde el panel,
  energía previa **354**, coste reservado **30**, objetivo Tealk. GOLD/GEMS y
  rechazo de duplicados comprobados apagados. Se desactivó este último ajuste
  manualmente antes, con autorización; el runner no cambia los ajustes.
  Mummih rechazado supervisadamente; **dos ofertas de Brute rechazadas por el
  runtime**, sin oro/gemas. No apareció una oferta de Tealk. Resultado **CLEARED**,
  Town → Aramore → Home confirmado; un solo `entry-1.intent.json`/ACCEPT.
  Hubo pausa inicial por oferta y continuaciones supervisadas en
  `dungeon_resume*_events.jsonl`, no nuevas entradas ni reanudación automática.
  Se diferenciaron Auto de combate y Auto del mapa sin quitar la parada ante
  desactivación inesperada de este último. La repetición y una run autónoma con
  la versión final todavía no están verificadas.
- `20261002_224527_1f1744bd9d71`: inicio solicitado por el usuario desde el
  panel, una entrada Z5D3 Heroic desde energía **368**, coste reservado **30**.
  Primera parada por UNKNOWN después de Auto: el cursor permanecía sobre el
  botón y el hover no coincidía con la referencia. Continuación autorizada,
  con una única activación supervisada de Auto confirmada; cero ACCEPT nuevos.
  El mapa mostró OFF al pasar a combate, causando una segunda parada prematura;
  después apareció Sitra. La primera corrección aparcaba el cursor antes de
  procesarse la suelta del botón y canceló Decline; se corrigió el orden.
  Reintento del rechazo **autorizado expresamente**, registrado por separado;
  original pendiente preservado en `decline-1-1.original-pending.json` y su
  resolución enlazada, sin atribuir efecto confirmado al primer clic.
  Sitra y dos Brute rechazados; **VICTORY y Home confirmados**, sin oro/gemas,
  otra entrada ni otra activación de Auto. `dungeon_resume*_events.jsonl` conserva
  las pausas y continuaciones; no acredita una run autónoma completa.
- `20261002_232527_0da5a00a6ddc`: parada antes de seleccionar Heroic, sin
  ACCEPT ni intención de entrada. El menú y coste 30 eran correctos, pero
  el botón sin hover dio correlación `.9598` y diferencia `25.77`; la única
  referencia era el botón resaltado. Se añadió `HEROIC_IDLE`, conservando la
  anterior y los umbrales `.97`/`12`; gris, oscuro o nombre dañado se rechazan.
  `20261002_233349_34dbeffd4963` comprobó el arranque real hasta enviar Heroic
  con entrada/gasto prohibidos; después recibió F8 y se detuvo, sin ACCEPT ni
  intención de entrada. La lectura final de equipo y vuelta a Home quedaron
  interrumpidas: no se declara esa comprobación completa ni se reanudó tras F8.

Quest/Settings comparan los píxeles invariantes de dos referencias conservadas,
no su fondo transparente: el pueblo cambia al mover al personaje. Correlación
`.97` y diferencia de brillo máxima `12` intactas; icono ausente, pantalla
oscurecida o puntuación no finita no acreditan Home. Checkbox vacío resaltado
tiene referencia propia, no se rebajó la guarda anti-gasto.

Corrección de arranque: `20261002_223631_6b4c6983564d` comprobó el panel real →
ocultar → foco Steam → captura/Home → restaurar, con hijo limitado a lectura:
**cero inputs/entradas**. `20261002_223745_preentry_home_check` verificó ajustes,
Z5D3 Heroic/coste 30 y equipo, y regresó a Home con ACCEPT prohibido; ninguna
entrada. La comprobación terminó con un error en una aserción del helper
(`entries_reserved` no es atributo; se consulta con `payload()`), tras regresar;
imagen final y registro de clics conservados, sin alterar ese registro.
No es otra validación de dungeon. Los intentos anteriores también incluyen
paradas por cambiar a otra ventana: mantener Steam en primer plano; no se
reactiva automáticamente tras perder foco.

Los clics esperan 250 ms tras la suelta antes de mover el cursor a `(960,1070)`;
así no cancelan la acción de Unity ni dejan el botón resaltado en la lectura.
Auto distingue mapa/combate mediante el HUD de exploración, no el brillo del
verde; su referencia de SHOP es **solo lectura**, jamás autoriza una compra.
Auto ON debe confirmarse antes de acreditarlo. Tras haberlo visto ON, un OFF
transitorio espera hasta 8 s **sin enviar input**; si persiste, detiene y nunca
lo reactiva. Auto OFF de combate tampoco autoriza un clic de activación.
`observe(..., auto_started=True)` se utilizó solo en continuación supervisada,
restaurando ese hecho desde una intención confirmada del mismo intento; no hay
reanudación automática ni liberación de entradas/rechazos inciertos.

Los costes reservados no son saldo posterior medido. Botín/XP/oro ilegibles se
guardan como `null`, no cero. Los recortes de resultados están en el run; el
bot no certifica todavía inventario nuevo, tier o ganancias netas.

## Verificación sin gastar

```sh
.venv/bin/python -B -m unittest discover -s tests
.venv/bin/python -B scripts/comprobar_panel_farm.py
```

La suite no toca el juego; la segunda comprobación abre y cierra solo el panel.
Fixtures y recortes son locales/sanitizados. Fuentes del catálogo y hashes de
capturas en `assets/dungeons.json` y `assets/dungeon_templates.json`.

Verificación actual: **247 tests, 244 pasan y 3 skips Windows ya existentes**;
panel real comprobado sin motores, incluida la disponibilidad de Tealk Heroic.
Mutación en memoria de la comparación objetivo/otro familiar detectada por dos
pruebas; archivo original intacto. Importación de las nuevas fixtures reproducida
en directorio temporal y referencias anteriores conservadas exactamente.
La fixture mínima `home_town_moved` reproduce UNKNOWN antes de la corrección
y Home después; los iconos ausentes/oscurecidos siguen devolviendo UNKNOWN.
Una mutación en memoria de la selección de píxeles también provoca dos fallos;
archivos intactos. No se modificaron las guardas de foco/F8 ni el presupuesto.
Regresiones adicionales: procesar suelta antes de apartar cursor, confirmar
Auto una sola vez, diferenciar mapa/combate por contexto, permitir transición
OFF sin reactivar y detener un OFF persistente. Referencia Sitra exacta; una
alteración del nombre sigue provocando lectura desconocida.
Heroic se prueba en ambos estados de hover y sin aceptar versiones grises,
oscurecidas o con texto alterado. Los datos anteriores siguen intactos.

## Zones y Escape — comprobado 2026-10-03

`select_zone()` abre el botón azul Zones, busca el nombre visible con scroll
acotado y verifica el título del mapa resultante. La lista se recoloca alrededor
de la zona elegida al reabrirse: una fila fija no identifica una zona. Texto
blanco y títulos conservan los umbrales `.97`/`12`; referencias desconocidas,
oscurecidas o ausentes no autorizan seleccionar otra zona.

`close_menu()` usa una sola pulsación **Escape** por nivel y confirma el padre.
Comprobado en Zones, mapas, Settings, dificultad Tealk y equipo; sin clic en X.
Ofertas de familiar, confirmaciones, combate, resultado y UNKNOWN no autorizan
Escape. Town sigue usando su botón: cerrar un resultado no equivale a cobrarlo.

Evidencia: `20261003_003057_zones_escape_check`, código real del runner recorriendo
las **20 zonas**, incluidos scroll y cambios entre extremos. Desde Big Claw
seleccionó Aramore → Tealk Heroic → equipo, sin ACCEPT, y cerró con Escape hasta
Home. Se restauró Bit Valley, la zona inicial. Ajustes solo leídos; **0 entradas,
0 energía reservada y 0 oro**, sin Auto, gemas, equipo ni consumibles. Registro
`dungeon_navigation_events.jsonl` y `navigation-verification.json`; no es una
prueba de farmeo ni acredita dungeons desbloqueadas en los mapas abiertos.
Importación reproducible: `scripts/preparar_dungeon_fixtures.py <fuentes> --append-zones`.

## Scroll de ajustes — 2026-10-03

Comparación local con el mismo runner, captura, perfilado y dos repeticiones:
avance de **2 pasos: 20,420 s** de mediana; **6 pasos: 11,269 s** en prueba y
**11,291 s** al repetir con el método de producción, aproximadamente **45 %
menos tiempo**. Capturas por comprobación: 98 → 46; permanecen las dos lecturas
estables y todas las guardas de foco/F8/cursor, gasto nativo y duplicados.
El avance de 8 pasos se descartó: no confirmó los tres ajustes y acabó en parada
segura. No se bajaron umbrales ni se aumentó la velocidad del input compartido.
Solo cambió el avance de lectura de Settings de 2 a 6, manteniendo solape.
Zones y los motores de pesca conservan su scroll/input anterior.

Medidas: `20261003_005313_scroll_settings_benchmark/scroll_measurements.json`;
verificación final: `20261003_010043_scroll_settings_benchmark`, dos lecturas de
GOLD/GEMS/duplicates apagados y vuelta a Home, sin modificar ajustes, sin ACCEPT,
Auto, gasto ni entradas. La regresión acota el número de avances y conserva
parada ante ajustes activados o ilegibles.

## Parada al leer energía TEAM — 2026-10-03

`20261003_010714_7307fdd5f468` y `20261003_010757_a7bb9714091b` se detuvieron
en la lectura estable de energía, antes de reservar o pulsar ACCEPT. El panel
siguió abierto. La barra con **317/368** usa un slash de **23×22**, distinto del
**21×20** anterior: comparar reescalado daba `.9005`, por debajo del filtro `.95`.
Se añadió `SLASH_LARGE`, conservando la referencia anterior y el mismo filtro;
el lector de dígitos, el rechazo de temporizadores y el presupuesto no cambiaron.
Fixtures sanitizadas de saldo y reloj; negativos para slash/capacidad ausentes
y pantalla oscurecida. Importación aditiva reproducible con
`scripts/preparar_dungeon_fixtures.py <fuentes> --append-energy`.

`20261003_011700_energy_preentry_check` comprobó el método real `enter()` hasta
su llamada de reserva, bloqueada por la prueba antes de modificar presupuesto:
saldo estable **319**, coste **30**, vuelta a Home, **0 ACCEPT y 0 reservas**.
No es otra entrada ni certifica una run autónoma; los registros previos siguen
intactos. Las referencias/fixtures anteriores se conservaron píxel a píxel.

## Ofertas encadenadas y cancelación supervisada — 2026-10-03

`20261003_011900_ec18431e7a39`, iniciada desde el panel, registró una entrada
Z5D3 Heroic desde **319**, reserva **30**, rechazos Sitra → Mummih → Sitra y
**VICTORY/Town/Home**, cierre confirmado por el propio runner y límite de una run.
No hay registros de continuación en esa sesión; botín/reclutamientos no se
infieren. No habilita repetición automática ni acredita la última corrección.

La siguiente sesión independiente, `20261003_012120_5e8291fba450`, tuvo un ACCEPT,
reserva **30** desde lectura **369**, y rechazos confirmados de Sitra y Brute.
El tercer rechazo de Brute se detuvo tras enviar YES: su intención permanece
**sin efecto confirmado**. No existe captura del instante de la parada; no se
atribuye retrospectivamente éxito ni se repite el clic. La inspección posterior
mostró una confirmación de Persuade de **Sitra por 2.000 GOLD**, no su origen.

Con autorización expresa «Cancelar y revisar»,
`20261003_012817_cancel_sitra_gold_check` envió solo **NO**, confirmó tres lecturas
de la oferta Sitra, sin gasto, ACCEPT, Decline ni reanudación. La dungeon queda
pausada y la intención incierta original se conserva exactamente.

Se reprodujo con las fixtures reales el caso Brute → confirmación → Sitra:
el cierre esperaba únicamente mapa/combate/resultado, por lo que otra oferta
inmediata causaba parada. Ahora dos lecturas de **otra oferta conocida** acreditan
el cierre; la misma especie, un nombre ilegible o una confirmación no lo hacen.
Los rechazos existentes/inciertos siguen bloqueados. La regresión y una mutación
en memoria que aceptaba indebidamente la misma oferta detectan ese límite.
Corrección verificada por reproducción; no se inició otra run para probarla.

## Exploración actual y diagnóstico de pausas — 2026-10-03

`20261003_034131_menu_exploration` recorrió los menús reales, con exclusividad,
capturas Wayland y guardas de foco/F8 intactas; terminó en **Home**, sin ACCEPT,
Play, Summon, compras, reservas de entrada/oro, cambios de equipo ni de ajustes.
Es navegación supervisada, no certificación de nuevos modos automáticos.

| Menú observado | Hallazgo, sin entrar a la actividad |
| --- | --- |
| Quest | Aramore, 10/10 estrellas visibles; no apareció una opción de reanudación. |
| Settings | Auto-persuade GOLD **activo**, Bribe GEMS apagado y rechazo de duplicados **activo**. No son los ajustes apagados de las pruebas anteriores. |
| Raid | Pantalla Storm con **0 shards** y Summon; no se pulsó Summon ni recarga. Un clic en el primer indicador no cambió la página: no se acredita navegación a otra raid. |
| World Boss | Lista de salas, Filter y Summon; no se creó sala ni se entró a ninguna. Datos de jugadores omitidos. |
| Trials | Diálogo inicial Nyxn avanzado una vez; después Nyxn's Trials, 15 tokens y coste seleccionado 1. Play no pulsado. |
| PvP | PvP Arena con coste seleccionado **5 tickets**; no Play ni cambio de formación. |
| Expedition | Coste seleccionado **1 badge** y saldo visible 15; no Play, Rewards ni cambio de equipo. |

`anti-spend-verification.json` comprobó el método real `verify_settings()`:
detectó GOLD activo y detuvo con `safety_checked=false` antes de cualquier entrada.
Los ajustes siguen intactos; no habilitar farmeo mientras el gasto nativo esté activo.
No se atribuye este estado actual a las pausas históricas, que sí comprobaron GOLD apagado.

Escape no cerró Quest una vez, sin pérdida de foco registrada; se cerró con X
supervisadamente. Escape sí cerró Settings después. Causa intermitente sin resolver:
no se añadieron reintentos, fallback automático ni otro backend de teclado.

`wait()` ahora registra `DUNGEON_WAIT_TIMEOUT` con pantalla/familiar observados,
espera solicitada y un `wait-timeout-*.png` de regiones de interfaz, no chat/roster.
Reutiliza el último frame ya validado, sin captura extra tras perder foco/F8.
Si falta frame o no se puede escribir la imagen, sigue deteniendo; no confirma
intenciones ni repite acciones. Comprobado offline con Sitra y en Steam con una
espera imposible de TEAM desde Home, **sin input**. Mutación de la selección de
recortes detectada por la regresión. Sintaxis y suite completa verificadas.

`20261003_013919_af16c5b71763` sigue sin resultado confirmado; su rechazo Sitra
pendiente permanece intacto. Home/Quest actuales no demuestran victoria de esa
entrada. Evidencia de la exploración en `exploration-verification.json` y JSONL.
Las fuentes oficiales de zonas/desbloqueos se releían mediante Agent Browser
aislado, sin cuentas; no sustituyen las observaciones del cliente.

## Pendiente, sin presentar como probado

Recorrido continuo completo con la última corrección sin intervención, repetición real de varias runs,
otras dungeons/dificultades (navegación de zonas ya comprobada), ampliar rutas por familiar y nombres reconocidos, reconocimiento de
derrota, Persuade con cuota de oro y botín estructurado. No se hicieron compras,
consumibles, cambios de equipo, commits o publicación.

## Repetición autónoma Z5D2 — 2026-10-03

`20261003_131256_f3ef71365838`: **6/6 runs** Z5D2 Normal sin intervención,
energía 62→~4, parada por límite de runs. Correcciones previas, cada una con
prueba y causa observada en vivo:

- Foco: `activate()` exige 1 s de foco continuo confirmado; un Escape enviado
  ~0,6 s tras pedir foco se perdía (`20261003_114038_dde3ac5617e7`).
- Energía: la barra alterna saldo y reloj cada 2–6 s. El lector de cebos
  confundía 0/6 con 8 en esta fuente; se añadió `DIGIT_0..9_ENERGY` real y la
  espera de saldo en TEAM es de 30 s. Saldo > capacidad se descarta.
- Ofertas: con Decline duplicates desactivado y sin objetivo, se rechaza toda
  oferta legible (identidad por glifo del nombre). Nunca Persuade ni Bribe.
- Ajustes del usuario (autorizados): auto-Persuade GOLD y Decline duplicates
  desactivados en el juego; gemas seguían apagadas.

## World Boss Netherworld T9 — 2026-10-03

`python -m fishing_core.boss_runtime <runs>` (Linux/niri, sin panel todavía) gasta
xeals en **Netherworld Tier 9 Normal, sala privada en solitario**. Comprueba y nunca
cambia la configuración del diálogo Summon; reserva 1 xeal antes de START; cierra con
TOWN y la X de la lista. Sin xeals cierra la lista sin invocar.

- Heroic T9 en solitario: derrota en segundos (`c4`, 2026-10-03). Normal: victoria ~8 s.
- Sala pública: se une otro jugador y START queda desactivado → pantalla desconocida,
  parada sin expulsar a nadie.
- Diálogos y ventanas entran/salen animados: cada clic espera pantalla **y** botón estables.
- En vivo: `20261003_133642_00491fa11b43` y `20261003_133747_c0b5fc0a0427`, 2 victorias
  y parada por saldo 0.

Pendiente: Trials (coste 5 tokens; con 3 el juego ofrece comprar con gemas → siempre
NO), integración en el panel y un orquestador que repita cada modo al regenerarse.

## Exploración de modos — 2026-10-04

Una run de cada modo, supervisada y sin compras. Coordenadas a 1920×1080.

| Modo | Recurso | Entrada | Combate | Cierre |
|---|---|---|---|---|
| Trials (Nyxn's) | Tokens, coste 1–5 (desplegable), dificultad 499 | HOME TRIALS (1830,710) → PLAY (1280,580) → TEAM ACCEPT | Mapa tipo dungeon: AUTO del mapa (1880,530) y combates | CLEARED → TOWN (994,998) vuelve a la ventana |
| Raid Storm (T13) | Shards, 1 por dificultad | HOME RAID (90,580) → abre en Storm → SUMMON (1260,786) → Normal/Hard/Heroic → TEAM ACCEPT | Mapa con AUTO activo, varios combates | CLEARED → RERUN o TOWN (1154,996) |
| PvP Arena | Tickets, coste 5 (desplegable) | HOME PVP (90,280) → PLAY (1280,568) → SELECT OPPONENT (4 rivales, FIGHT) → TEAM ACCEPT | Un combate (~4 s) | VICTORY → STATS / TOWN |
| Expedition (Idol Dimension) | Badges, coste 5 | HOME EXPEDITION (1830,560) → PLAY → 4 portales → ENTER (958,966) → TEAM ACCEPT | Mapa con AUTO y combates | CLEARED → TOWN; la dificultad sube sola (10.330→10.335) |

- Con tokens < coste, PLAY de Trials ofrece comprar con gemas: siempre NO (1100,750).
- Cambiar el coste: el selector de Trials muestra filas 1–5; pulsar la fila ya marcada no lo
  cierra, se cierra con su X.
- El clic en AUTO del mapa justo al empezar un combate apaga el AUTO del combate: esperar a
  que el combate esté estable antes de tocarlo.
- Preferencias de crzf: Trials coste 5 bajando hasta 1; Raid del tier del jugador (T13 =
  Storm); PvP 5 tickets eligiendo rival; Netherworld T9 Heroic con REGROUP.

## Retoques del panel y evaluación de Brave — 2026-10-07

- Iconos de modos recuperados completos de referencias locales, con transparencia;
  cofre sin fondo. Se conserva el centrado por masa visible de `pixel_ui.visual_center`.
- Marcos Settings/Raid: esquinas y placa separadas del fondo/cuerpo, limpieza de
  controles originales y margen de recorte para mantener la zona X dentro del PNG.
  Corregido el generador `scripts/build_ui_frames.py`, con regresiones offline.
- Ocho pantallas renderizadas con PIL, sin abrir Tk ni el juego; zonas clicables
  dentro del panel y los seis iconos centrados con error máximo de 0,5 px.
- **Brave multicuenta simultáneo: objetivo solicitado, todavía no implementado ni
  probado.** Brave y gamescope están instalados. La ruta candidata reutiliza gamescope
  con un perfil y servidor gráfico por cuenta; antes hay que separar display/nodo
  PipeWire, memoria compartida, locks, configuración, progreso y botín por sesión.
  También identificar Brave, adaptar la geometría web y evitar el relanzamiento
  global de Steam. Conservar F8 y guardas; no basta abrir varios perfiles.

## Multicuenta: aislamiento offline — 2026-10-07

**Primera entrega, no farmeo Brave operativo.** Alcance confirmado: tres cuentas
distintas a la vez (Personal, Perfil 1, Steam). El usuario autorizó dos perfiles
Brave nuevos exclusivos del bot; los originales no se inspeccionaron ni copiaron.
Asignación aclarada: **Personal = fmani**, **Perfil 1 = Kortzz**,
**Steam = brandonr2600**. Los nombres del personaje y de Kongregate pueden diferir.

- `fishing_core/accounts.py`: identidad allowlist `FARM_ACCOUNT=personal|perfil-1|steam`.
  Un proceso por cuenta, con entorno fijo y heredado por sus hijos; nunca cambiar
  la cuenta dentro de un mismo panel/proceso. Sin esa variable, rutas antiguas.
- Preferencias, progreso, botín/álbum/tipos, IPC y registros propios bajo
  `runs/accounts/<id>/`. Manifiestos/eventos identifican la cuenta lógica, no sus
  credenciales. Las cuentas nuevas empiezan con cuota de oro cero; valores ya
  guardados y configuración antigua intactos.
- Locks por cuenta para todos los motores y para la cadena `FARM_ALL`. Steam
  conserva los nombres antiguos de locks para impedir dos motores sobre esa
  cuenta desde lanzadores diferentes. Lock exclusivo adicional de `FRAME_SERVER`.
- Sesión identificada: `FARM_BACKEND=gamescope`, display X local explícito en
  `FARM_GAMESCOPE_DISPLAY` y serial de vídeo en `FARM_GAMESCOPE_SERIAL`. No se elige
  el primer nodo/pantalla ni se cambia al escritorio si faltan o desaparecen.
  SHM propia por usuario/cuenta/display/serial; nunca reciclar la imagen de otro
  endpoint. No hay fallback a otro flujo sin su servidor de imagen.
- Geometría exacta 1920×1080, ventana única y misma identidad X durante la sesión.
  Un servidor muerto no entrega fotogramas almacenados. F8 se conserva en el
  escritorio; relanzamiento global de Steam deshabilitado para cuentas identificadas.
- Directorios privados preparados (modo 0700, excluidos por `runs/`):
  `runs/accounts/personal/brave-data` y `runs/accounts/perfil-1/brave-data`.
  Al prepararlos estaban vacíos, antes de los logins manuales posteriores. Se
  rechazan enlaces simbólicos y directorios de perfil públicos; no se sobrescribe
  contenido ya existente. Fuente del aislamiento de datos:
  [Chromium: User Data Directory](https://chromium.googlesource.com/chromium/src/+/main/docs/user_data_dir.md).

Pruebas: tres workers Python reales coexistieron offline y rechazaron duplicados
(también Steam frente al modo antiguo). IPC/logs con el mismo run-id no se mezclan.
Ventanas, nodos y frames restantes son sintéticos; regresiones comprobadas rojas
antes del arreglo y mutación de la guarda de identidad detectada sin editar disco.
Durante la primera prueba roja del relanzamiento heredado se intentó enumerar X;
el test quedó corregido para aislar esa llamada. No se inició navegador/juego,
no se capturaron imágenes ni se enviaron inputs.
La primera suite completa heredó `DISPLAY` y sus seis tests Tk crearon y retiraron
un panel sin `mainloop`, con clics simulados y configuración temporal. Para evitar
incluso esa creación de ventanas, la verificación de esta entrega se repite sin
`DISPLAY`, `WAYLAND_DISPLAY` ni `NIRI_SOCKET`; los tests Tk conservan su skip
existente cuando no hay pantalla. No se lanzaron motores ni farmeo.

**Pendiente en la primera entrega:** login manual y validación gráfica; resultados
posteriores más abajo. Todavía falta integrar las guardas web en el runtime y
integrar el supervisor/lanzamiento de las tres sesiones, parada conjunta y
demostrar farmeo simultáneo real. `backend()` y `GamescopeGuard` rechazan Personal
y Perfil 1 antes de conectar al servidor X: no eliminar ese bloqueo sin validar
Brave. No hay launcher multicuenta listo ni promesa de funcionamiento basada en mocks.

Evidencias y logs de esta entrega: `/tmp/opencode/bitheroes-multi-account/`.
Suite offline:
`env -u DISPLAY -u WAYLAND_DISPLAY -u NIRI_SOCKET .venv/bin/python -B -m unittest discover -s tests`.
Regresión enfocada final: 33 tests de cuentas/gamescope/orquestador pasan; sintaxis
de 13 archivos y `git diff --check` correctos. Primera suite: 371 tests, 368 pasan
y 3 Windows omitidos (222,013 s). Suite headless terminada: **371 tests, 362 pasan
y 9 omitidos** (6 Tk sin pantalla, 3 Windows), 212,813 s; log `tests-headless.log`
en el directorio de evidencias. No hay commits ni publicación.

### Primera prueba gráfica: perfil entonces etiquetado Personal

**Corrección posterior:** este perfil autenticado contenía Kortzz y corresponde a
Perfil 1, no a fmani. Las rutas y nombres de evidencias de esta prueba conservan
su etiqueta histórica; no prueban la identidad de Personal/fmani.

El usuario autorizó explícitamente continuar con Brave y el juego después de
explicar la restricción offline. La excepción no elimina F8, aislamiento,
límites de gasto ni la prohibición de leer/copiar los perfiles originales.

- Brave 154.1.96.60 abierto con el directorio nuevo
  `runs/accounts/personal/brave-data`, sin importar cuentas ni datos originales.
  Inicio visible sobre Wayland para permitir login manual; todavía no gamescope.
- Página del juego localizada en la portada oficial de Kongregate:
  `https://www.kongregate.com/en/games/Juppiomenz/bit-heroes`.
  Identidad Brave comprobada en el runtime (`navigator.brave`), no inferida del
  nombre del proceso. La página exige iniciar sesión para jugar; no hay canvas
  del juego antes del login.
- Formulario de login abierto. El usuario escribe sus credenciales directamente
  en Brave; no se leen campos, cookies, storage ni archivos de credenciales y no
  se exporta estado de autenticación. No hay motores activos ni gasto de recursos.
- Control CDP solo local y con un directorio de datos ajeno al navegador personal,
  siguiendo [Chrome: remote debugging](https://developer.chrome.com/blog/remote-debugging-port).
  La sesión de Agent Browser se liga a la pestaña del juego; para adjuntarse a una
  instancia se usa `connect` explícito, evitando abrir un Chromium distinto por
  omitir parámetros de conexión en llamadas posteriores.

### Kortzz, entonces etiquetado Personal: captura y clic — 2026-10-07

Login manual terminado y excepción gráfica reconfirmada. Solo se probaron el
perfil nuevo, Settings y controles de ventana; ningún motor ni gasto de recursos.

- Instancia inicial cerrada limpiamente antes de trasladar el mismo directorio
  de datos a gamescope headless. El modo app dejó una barra de 56 px; se probó
  kiosco y el botón Fullscreen de Kongregate, sin importar datos de otros perfiles.
  Brave restauró una pestaña anterior además de la nueva: se cerró la restaurada
  antes de pulsar Play en la restante. El launcher futuro debe rechazar duplicados
  y fijar el target CDP, no elegir silenciosamente la primera pestaña.
- Endpoints de la prueba final: display `:3`, serial PipeWire `3634`. Nodo ligado
  al cliente PipeWire cuyo `application.process.id` coincide con el gamescope
  lanzado; display escrito por su proceso hijo. Son datos efímeros, **no valores
  para reutilizar en el lanzador**. Ventana única verificada por XID, PID, clase
  `Brave-browser`, `_NET_WM_NAME` y geometría `[0,0,1920,1080]`.
- Un único FrameServer de Personal produjo imagen real BGR 1920×1080. Home se
  reconoce con `DungeonVision` y sus plantillas actuales, sin cambiar umbrales:
  `HOME_QUEST` en `(22,24)` y `HOME_SETTINGS` en `(1780,932)`.
- XTest dirigido solo a ese servidor abrió Settings; la visión existente confirmó
  `SETTINGS` y el movimiento no cambió el cursor del escritorio. F8 se consultó
  antes de los inputs; no se certificó todavía una parada conjunta con F8 físico.
- **Bloqueo reproducido:** Escape salió del Fullscreen del navegador en vez de
  devolver Home. La ventana X mantuvo 1920×1080 mientras el iframe cambió de tamaño:
  la geometría X sola no garantiza la geometría del contenido. La prueba supervisada
  `validate-personal-input.py` permanece roja; no se declara roundtrip aprobado.
  Se restauró Fullscreen y se pulsó la X de Settings, contrastada con el recorte
  real anterior. Home apareció en una lectura posterior, fuera del timeout de
  12 s: tampoco se certifica esa alternativa como recuperación fiable.
- Al detener el flujo de imagen, gamescope abortó en `destroy_buffer` de
  `pipewire.cpp:54`. Luego se verificó que navegador, gamescope y FrameServer de
  esta prueba habían terminado, CDP estaba cerrado y la SHM propia retirada.
  Se desconectaron únicamente las tres sesiones Agent Browser creadas para Personal.

Evidencias privadas en el directorio temporal citado arriba: imágenes
`personal-gamescope-pipewire-loaded.png`, `personal-gamescope-pipewire-settings.png`
y `personal-gamescope-after-close-check.png`; metadatos `personal-gamescope.json`
(marcados detenidos) y log `personal-gamescope-kiosk.log`. No se adjuntan capturas
del escritorio ni se consultan perfiles originales.

**Incidente de privacidad:** una salida de diagnóstico mostró por error el título
de un iframe, que contenía un enlace autenticado con un token. Se informó al
usuario; el valor no se copia a notas, archivos del proyecto ni configuración.
No volver a volcar títulos, URLs completas ni respuestas CDP sin una allowlist de
campos: incluso `title` puede contener secretos. Se recomienda revocar ese token
desde Kongregate; al terminar esa prueba no se había confirmado su invalidación
ni que cerrar sesión bastara. La mitigación posterior se registra más abajo.

**Pendiente:** resolver Escape y verificar la geometría efectiva del contenido
antes de cada input, estabilizar la parada del flujo y validar Perfil 1/cuentas
distintas. `require_calibrated_client()` sigue intacto:
Brave no se habilitó. Supervisor y farmeo triple continúan pendientes.

Verificación final de esta prueba: 33 tests de cuentas/gamescope/orquestador pasan
headless (8,217 s); los tres PNG de Home/Settings/Home se reclasifican offline con
las plantillas actuales, y `git diff --check` pasa. No se cambió código del bot,
no se retiraron guardas y no hay commits ni publicación.

### Mitigación del token expuesto — 2026-10-07

- La cuenta afectada era Kortzz, del perfil entonces etiquetado Personal. No se
  cambió la contraseña de fmani ni de Steam.
- El usuario pidió gestionar la revocación y autorizó específicamente cambiar la
  contraseña de la cuenta afectada, después de explicar ese efecto. Kongregate
  exigió login manual para acceder a los ajustes. No se abrió el juego, no se
  leyeron credenciales ni se tocaron los perfiles originales.
- Ajustes de Password & Security y Authorized Apps revisados; no se encontró una
  acción separada de revocación para el token de juego. La
  [documentación oficial de autenticación](https://docs.kongregate.com/docs/concepts-authentication)
  establece que el token de juego cambia cuando el usuario cambia su contraseña.
- El primer envío fue rechazado por falta de contraseña nueva: no se consideró
  un cambio aplicado. A petición del usuario se generó una contraseña únicamente
  dentro de Brave con `crypto.getRandomValues`, sin devolver el valor al agente,
  copiarlo al chat, guardarlo en notas ni leer la contraseña anterior. El usuario
  confirmó haberla guardado y haber introducido la actual directamente en Brave.
- Segundo envío autorizado: Kongregate mostró la confirmación de cambio de
  contraseña y no presentó errores de validación. Con ese cambio se mitiga el
  token anterior conforme al mecanismo oficial; no se reutilizó el token expuesto
  para intentar autenticarse ni se leyeron tokens nuevos para compararlos.
- Se cerraron limpiamente solo ese Brave del bot y su sesión de diagnóstico,
  sin juegos ni motores. El bloqueo por el token ya no queda pendiente; permanecen
  los problemas de Escape/FullScreen y parada de PipeWire, la validación de Perfil 1
  y el supervisor multicuenta. Farmeo Brave todavía deshabilitado.

### Cierre del lector GStreamer — incremento offline, 2026-10-07

Las reglas actuales limitan las pruebas a offline. No se inició Brave, gamescope,
un panel ni un motor, no se capturó el escritorio y no se enviaron inputs.

- Defecto reproducido sin juego: `PipeWireFrames.close()` enviaba SIGTERM, no
  esperaba al hilo lector ni cerraba stdout; al forzar la salida tampoco esperaba
  después de `kill()`. Un flujo real de GStreamer con `videotestsrc` terminaba con
  código -15, en vez de cerrar limpiamente.
- Cierre corregido en la función compartida: `gst-launch -e`, SIGINT, espera del
  proceso, hilo y tubería. Si no termina, escalada acotada a SIGTERM/SIGKILL y espera
  del hijo propio. Se mantiene el flujo único de cada FrameServer y no se añaden
  reaperturas ni recuperaciones globales. El cierre repetido también se comprueba.
- Mecanismo respaldado por la
  [documentación de gst-launch](https://gstreamer.freedesktop.org/documentation/tools/gst-launch.html)
  y el [código de GStreamer 1.28.7](https://github.com/GStreamer/gstreamer/blob/1.28.7/subprojects/gstreamer/tools/gst-launch.c):
  registra SIGINT para la interrupción y `-e` solicita EOS antes de apagar.
- Tres regresiones nuevas: salida normal/forzada, lector ya terminado y flujo
  sintético real (solo `videotestsrc` → conversión BGR → tubería, sin PipeWire ni
  ventana). Primero fallaron; después pasan los 20 tests de `test_gamescope.py`
  (7,205 s). Una mutación SIGINT → SIGTERM solo en memoria hizo fallar la prueba
  sintética: el test detecta volver al cierre abrupto.

**Límite:** esto corrige el ciclo de vida del lector, no certifica la eliminación
del aborto de gamescope. En el
[código de gamescope 3.16.25](https://github.com/ValveSoftware/gamescope/blob/3.16.25/src/pipewire.cpp#L37-L55),
la aserción de la línea 54 corresponde a un tipo de buffer inesperado; no basta
ese mensaje para determinar su causa. La versión instalada es 3.16.25-1, con
PipeWire 1.6.9-1 y GStreamer 1.28.7-2.1. No se actualizaron paquetes ni se parcheó
gamescope. Escape y la geometría del iframe siguen pendientes de validación real:
no se inventaron coordenadas de cierre, no se aumentaron timeouts y
`require_calibrated_client()` continúa bloqueando Brave. Perfil 1, cuentas
distintas, supervisor y F8 conjunto todavía no están certificados.

### Asignación corregida y validación de ambos Brave — 2026-10-07

- Tras confirmar cerrados ambos Brave del bot y vacío el destino, se trasladó
  íntegramente el perfil autenticado de Kortzz a `runs/accounts/perfil-1/brave-data`.
  Se conservó el inode y el modo 0700, sin leer ni copiar secretos; el directorio
  vacío anterior quedó respaldado. Personal se recreó vacío y el usuario realizó
  el login manual de la cuenta cuyo personaje es fmani.
- Antes de abrir juegos aislados, el usuario confirmó cerrados los juegos de
  fmani y Kortzz en los clientes originales. Steam original se mantuvo intacto.
  La autorización gráfica permite diagnóstico de Home, Settings y perfil del
  personaje, no farmeo, compras, cambios de equipo ni gasto.
- Una prueba real anterior de Personal midió viewport, dos iframe anidados y
  canvas/buffer 1920×1080, escala 1. NEWS se cerró por XTest, pero Home quedó UNKNOWN:
  Quest contenía una variante no cubierta por la máscara de las referencias Steam.
  Se detuvieron los inputs. Al cerrar su FrameServer, la SHM desapareció y gamescope
  sobrevivió; después se cerraron solo ese juego, navegador y diagnóstico propios.
- Regresión offline: fixture `home_personal`, con solo Quest y Settings. Primero
  falló con UNKNOWN; añadir `HOME_QUEST_TOWN_PERSONAL` al mecanismo de variantes
  existente permite reconocerla, sin modificar `.97/12`, geometría ni guardas.
  Se conservaron exactamente los 293 templates y 146 frames anteriores. Casos
  oscuros, grises, sin iconos y con el pergamino dañado siguen rechazándose; retirar
  la nueva variante solo en memoria vuelve a hacer fallar la regresión.
  Límite: máscara de variantes observadas, no alfa universal. Efectos transitorios
  de brillo todavía pueden dar UNKNOWN; no se compensan con clics ni umbrales menores.
- Nueva validación: ambos juegos coexisten con display, nodo PipeWire, CDP, PID y
  SHM distintos. Capturas BGR 1920×1080 y Home independientes, sin motores activos.
  Settings se abre por XTest y Escape CDP devuelve Home en ambos sin abandonar
  Fullscreen. También se abrió únicamente el perfil del personaje: encabezados
  **FMANI** y **KORTZZ** contrastados gráficamente; Escape devuelve Home.
- Escape probado: `Input.dispatchKeyEvent`, `rawKeyDown`/`keyUp`, `key` y `code`
  Escape, `windowsVirtualKeyCode=27`, sin `nativeVirtualKeyCode`. El diagnóstico
  comprueba antes la ventana propia y toda la cadena iframe/canvas; esto aún no
  está integrado en `GamescopeIO.escape()` ni en las guardas del bot.
- Perfil 1 restauró una ventana sin kiosco efectivo: HTML Fullscreen dio
  1920×1024. Se cerró ese juego antes de crear una ventana nueva del mismo perfil
  con `--kiosk --new-window`, cerrar la ventana antigua y volver a abrir el juego.
  Entonces se comprobaron 1920×1080 en contenido y buffer. No se da por correcta
  ninguna ventana restaurada por tener solo geometría X correcta.
- Suite final offline de este incremento: **375 tests, 366 pasan y 9 omisiones
  existentes** (6 Tk sin pantalla, 3 Windows), 211,110 s. Los 21 tests de visión
  pasan; `git diff --check` correcto. Sin commits, publicación ni dependencias nuevas.

Evidencias privadas: `/tmp/opencode/bitheroes-brave-roundtrip-1791423813631319413/`,
con metadatos y recortes por cuenta; no reutilizar endpoints efímeros.
Respaldo previo: `/tmp/opencode/bitheroes-home-before-1791423622882422229/`.
**Pendiente actual:** parada conjunta con Detener del panel, integración de
guardas web/Escape, Steam identificado y supervisor/farmeo triple. Se mantiene
`require_calibrated_client()` bloqueando Brave; las pruebas manuales no lo habilitan.

### Parada real de ambos flujos y F8 global — diagnóstico posterior

- Los FrameServer de Personal y Perfil 1 se detuvieron por separado: SHM retirada
  y gamescope siguió vivo en ambos (1,113 s y 1,111 s, incluida la espera de salud).
  Después se cerraron los dos juegos/Brave del bot y las conexiones de diagnóstico;
  PID, CDP y SHM quedaron comprobados detenidos/retirados. Steam original intacto.
- Dos observadores sin input no detectaron la pulsación F8 comunicada por el
  usuario durante su ventana de prueba de 90 s. `LinuxAPI.emergency()` consulta
  XWayland; eso no prueba una parada global desde cualquier ventana Wayland.
- El usuario autorizó un atajo nativo de niri. Añadido únicamente F8 en
  `~/.config/niri/config.d/90-user-extra.kdl`, sin repetición y sin permitir que
  una aplicación inhiba el atajo. Configuración validada y recargada, sin reinicio
  ni cambios visuales. Respaldo: `/tmp/opencode/bitheroes-niri-f8-before-1791424941628468523.kdl`.
- `fishing_core/global_stop.py` reutiliza SIGINT, como el botón Detener existente.
  Solo selecciona intérpretes/workers conocidos del mismo usuario y proyecto;
  no paneles, navegadores, Steam, FrameServer, tests ni fragmentos `python -c`.
  Abre un pidfd antes de contrastar la identidad para no señalar un PID reciclado.
  No lee teclas ni argumentos de procesos con otro directorio de trabajo.
- Cinco regresiones offline pasan, incluida una señal real a un proceso inerte.
  Una mutación que elimina la comprobación de propietario se detecta. La acción
  `spawn` de niri detuvo tres probes inertes, uno por cuenta, en 0,044 s; otro
  proceso Python del mismo directorio siguió vivo. **Esto prueba la orden, no la tecla.**
- Las pruebas físicas no certificaron F8. Una agotó sus 15 minutos mientras el
  usuario estaba ausente. Al volver aclaró que usa **Fn+8**; la prueba de una
  pulsación en una ventana propia no recibió evento y una comprobación temporal
  directamente en el atajo de niri no produjo su marcador de activación.
  No se concluye qué otra tecla genera esa combinación ni se registra un historial.
  Se retiró la comprobación temporal, se restauró el atajo directo y se cancelaron
  únicamente los probes propios. **Fn+8/F8 físico sigue pendiente.**
- Suite completa después de añadir la parada: **380 tests, 371 pasan y 9 omisiones
  existentes**, 208,712 s. Sin nuevos paquetes, permisos, captura del escritorio,
  farmeo, entradas, compras ni gasto. El backend Brave continúa bloqueado.

### Decisión posterior: Detener del panel, sin seguir bloqueados por Fn+8

- El usuario pide detener mediante la aplicación y abandonar el diagnóstico del
  RK61/Fn+8 para no retrasar las tres cuentas. F8 queda conservado como respaldo
  no certificado; no se exige certificar su tecla física para seguir integrando.
- La prueba en vivo confirmó sesión niri activa y desbloqueada, ventana Wayland
  preparada con foco y recepción de **8 sin Fn**. Fn+8 no generó evidencia en el
  atajo ni en esa ventana. Esto no identifica la tecla ni demuestra un fallo del
  teclado. No se registraron letras/texto ni se accedió como administrador.
- Se cerró únicamente la ventana de diagnóstico y se restauró exactamente el
  archivo de niri respaldado: atajo directo, configuración validada y recargada,
  sin reinicio. No quedaron diagnósticos activos ni enlaces a scripts temporales.
- En Linux, STOP del panel reutiliza `global_stop.stop_workers()` para señalar
  también hijos y motores de las otras cuentas, no solo su `farm_all`. Cerrar
  un panel en marcha sigue la misma acción. Clientes, otros paneles, FrameServer
  y procesos ajenos no son seleccionados; la ruta no Linux mantiene su señal previa.
- Regresión roja→verde sin juego ni GUI: tres procesos inertes con las identidades
  Personal/Perfil 1/Steam terminan por SIGINT y otro Python del proyecto sigue vivo.
  El conjunto enfocado de ocho pruebas pasa; volver a señalar solo al padre falla
  por mutación en memoria, sin modificar archivos originales.
- Suite completa final: **383 tests, 374 pasan y 9 omisiones existentes**,
  202,991 s; `git diff --check` correcto. Sin commits ni publicación.
- Detener de los motores reales y el supervisor siguen pendientes: esto no
  certifica farmeo triple ni desbloquea Brave antes de integrar sus guardas/Escape.
  Evidencias y respaldo: `/tmp/opencode/bitheroes-f8-live-rk61-RpSZs8dt/`.

### Runtime Brave: guardas y Escape integrados, validación offline — 2026-10-08

- `fishing_core/brave.py` fija cuenta, PID/pidfd, ejecutable, perfil exclusivo,
  puerto loopback poseído por ese PID y target CDP. La ventana X debe conservar
  identidad, clase, PID, geometría y foco; no se intenta cerrar otra ventana.
  Esto vincula el cliente al perfil aprobado; no hace OCR del personaje ni
  sustituye la comprobación gráfica de FMANI/KORTZ (cuenta Kongregate Kortzz).
- `fishing_core/brave_cdp.mjs` usa el WebSocket nativo de Node ya instalado, sin
  paquetes nuevos. El adaptador recibe solo comandos acotados y devuelve ID/booleano,
  nunca títulos, URLs, respuestas CDP, credenciales ni datos del perfil. No hereda
  credenciales, proxies ni `NODE_OPTIONS`; no admite redirecciones del endpoint.
- La guarda compartida de captura/input comprueba la única página oficial fijada,
  ventana, documentos/contextos y cadena de iframe (incluidos procesos separados).
  Exige viewport, iframe, canvas y buffer 1920×1080, escala 1, sin scroll y con foco.
  La captura vuelve a comprobar la guarda después de copiar el fotograma BGR.
  Antes de cada clic/rueda, el punto debe llegar al canvas sin overlays DOM.
- Escape utiliza `rawKeyDown`/`keyUp`, `key/code: Escape` y
  `windowsVirtualKeyCode: 27`, sin `nativeVirtualKeyCode` ni fallback XTest en Brave.
  Se suelta en el target original aunque falle una guarda, haya STOP o muera el
  padre; cerrar el adaptador desconecta CDP, no ejecuta `Browser.close`.
  La ruta Steam mantiene Escape XTest y sus guardas existentes.
- Brave no reintenta automáticamente una parada de seguridad, reconexión o UNKNOWN:
  evita crear otra guarda que acepte una identidad distinta. Steam conserva sus
  reintentos; los límites deliberados de duración siguen siendo independientes.
- Regresiones rojas→verdes, cadena sintética y un servidor CDP ficticio en loopback:
  transporte WebSocket nativo, geometría incorrecta, overlays en cada iframe/canvas,
  proceso reciclado, EOF durante Escape y errores de limpieza. Cuatro mutaciones
  detectadas: escala, identidad de documento, overlay y reintento automático.
- Suite completa: **405 tests, 396 pasan y 9 omisiones existentes**, 178,729 s.
  Sintaxis Python/Node y `git diff --check` correctos. Registro de esta ejecución:
  `/tmp/opencode/bitheroes-brave-runtime-suite-20261008.log`. Sin commits ni publicación.
- **Límite:** no se abrió navegador, juego ni panel; no hubo captura del escritorio,
  pulsaciones reales, farmeo ni gasto. `require_calibrated_client()` sigue bloqueando
  Brave. Falta certificar este mismo runtime y el arranque restaurado, contrastar
  Steam/brandonr2600 y conectar el supervisor/parada de motores reales antes del
  farmeo triple. Reconfirmar cuentas originales cerradas antes de reabrir juegos.

Fuentes oficiales del transporte y comandos: [WebSocket de Node](https://nodejs.org/api/globals.html#class-websocket),
[Page](https://chromedevtools.github.io/devtools-protocol/tot/Page/),
[DOM](https://chromedevtools.github.io/devtools-protocol/tot/DOM/) e
[Input.dispatchKeyEvent](https://chromedevtools.github.io/devtools-protocol/tot/Input/#method-dispatchKeyEvent).

### Guardas Brave: diagnóstico real autorizado — 2026-10-08

- Autorización gráfica renovada por el usuario: únicamente perfiles exclusivos
  del bot, sin farmeo, entradas, compras, cambios de equipo ni gasto. No se abrió
  una segunda instancia del mismo juego ni se accedió a perfiles originales.
- El runtime real mostró diferencias no presentes en los mocks: redirección
  oficial a `/en/games/juppiomenz/bit-heroes`, argumentos de Brave aplanados en
  `/proc`, clase X con la ruta exacta del perfil y un iframe remoto omitido del
  árbol padre. Se acepta solo esa ruta adicional, se parsea el título de proceso
  con `shlex` sin ejecutarlo y se une el iframe por su `parentId` explícito.
- La selección X de Brave usa PID y clase del perfil aprobado, no el título web:
  cambia al cargar y no es una identidad fiable. `BraveGuard` mantiene XID,
  pidfd, ejecutable, puerto propio, foco, origen y geometría; Steam conserva su
  selección por título. Las regresiones impiden volver a leer títulos de Brave.
- Personal y Perfil 1 completaron **Home→Settings→Home** y apertura/cierre del
  perfil usando `GamescopeCapture`, `GamescopeIO`, `BraveGuard` y Escape CDP reales.
  Viewport, ambos iframe, canvas y buffer: **1920×1080, escala 1**, sin scroll,
  con endpoints y servidores de imagen separados. No hubo motores de farmeo.
  El diagnóstico construyó explícitamente los componentes para probarlos sin
  alterar `require_calibrated_client()` ni arrancar el backend bloqueado.
- Identidad contrastada ahora: **FMANI** y **KORTZ**. La etiqueta pública de
  Kongregate en Perfil 1 corresponde a **Kortzz**. Las anotaciones anteriores de
  encabezado «KORTZZ» eran imprecisas; no cambió la asignación de cuentas.
- **Arranque restaurado todavía no certificado:** Perfil 1 volvió a dar contenido
  1920×1024 pese a tener ventana X 1920×1080. Fue necesaria una ventana nueva de
  kiosco: primero vacía, cierre del juego anterior, navegación posterior y retiro
  de la ventana vieja del bot. El origen de la ventana propia se fijó a 0,0.
  La guarda rechazó la geometría incorrecta y dos ventanas candidatas; no se
  redujeron sus exigencias. Falta incorporar y repetir un arranque estable.
- Las pausas ante UNKNOWN funcionaron: no se pulsó el aviso de inactividad.
  Una desconexión posterior se reconectó manualmente, con RECONNECT reconocido,
  solo para esta prueba. El hover sobre Settings también producía UNKNOWN:
  el diagnóstico omitía apartar el cursor, operación ya existente en
  `DungeonControl.click`. Se reutilizó su zona neutra, sin añadir templates ni
  bajar `.97/12`. Los motores Brave siguen sin reintentos automáticos de seguridad.
- Cierre selectivo: ambos FrameServer terminaron, retiraron su SHM y dejaron
  gamescope vivo (0,065 s y 0,042 s). Después se cerraron solo ambos Brave,
  gamescope y sesiones Agent Browser propios. Steam original y su gamescope
  siguieron vivos. **Todos estos endpoints gráficos/CDP quedaron detenidos.**
- No se pudo vincular inequívocamente la sesión Steam existente a una pantalla
  de juego. No se inició ni se intervino Steam; brandonr2600 sigue pendiente de
  contraste gráfico. Supervisor, Detener con motores reales y farmeo triple
  tampoco quedan certificados. F8 físico continúa aplazado.
- Verificación offline: 42 pruebas enfocadas pasan y cinco mutaciones detectadas
  (argv aplanado, clase del perfil, título web, ruta oficial y unión del iframe).
  Suite completa final: **407 tests, 398 pasan y 9 omisiones existentes**,
  219,512 s; ejecutada sin DISPLAY, WAYLAND_DISPLAY ni NIRI_SOCKET.
  Respaldo y evidencias privadas: `/tmp/opencode/bitheroes-runtime-live-feditr2k/`.
  Sin secretos en notas, dependencias nuevas, commits ni publicación.

### Preparación de ventana Brave — incremento offline, 2026-10-08

- El diagnóstico anterior de arranque mostró que `--app=about:blank` restauraba
  el juego y que `--no-startup-window` aplazaba la restauración hasta crear una
  ventana. No bastaba comprobar cero páginas al abrir CDP. Con Perfil 1, cerrar
  aquella restauración antes de navegar permitió después Home→Settings→Home con
  las guardas reales. Ese diagnóstico no certificó Personal ni un arranque automático.
- `prepare_brave(pid, port)` valida la cuenta Brave explícita, propietario,
  ejecutable/perfil/puerto propios y pidfd; el adaptador nativo tiene timeout,
  entorno mínimo y respuesta acotada sin datos web. Rechaza PID muerto o identidad
  cambiada y cierra solo el adaptador/pidfd, nunca el navegador o gamescope.
  **No lanza Brave:** el llamador debe confirmar exclusividad y abrir el perfil
  del bot con `--no-startup-window`; ese lanzador todavía falta.
- `prepareTarget` crea un target vacío, admite como máximo una restauración
  oficial y confirma su desaparición antes de navegar a la ruta fija del juego.
  Páginas ajenas, duplicadas o nuevas inesperadas detienen la preparación sin
  cerrarlas. No reutiliza ni sustituye una guarda activa. EOF del padre cancela
  el adaptador; no envía teclas ni clics ni ejecuta `Browser.close`.
- La ventana vacía requiere viewport 1920×1080, escala 1, foco, sin scroll/canvas,
  y la misma ventana CDP situada en 0,0. Cambiar bounds o solicitar Fullscreen no
  sustituye la comprobación efectiva. La navegación puede perder ese tamaño:
  **el target devuelto no significa «juego listo»**. Play/Fullscreen del sitio,
  posición X, iframe/canvas/buffer y personaje aún deben validarse después.
- Regresiones rojas→verdes: 19 pruebas Python y 18 Node enfocadas pasan, incluyendo
  transporte WebSocket real contra CDP ficticio, cierre asíncrono, restauración
  tardía, geometría incorrecta, identidad cambiada y EOF antes de crear páginas.
  Tres mutaciones en memoria detectadas: retirar validación de viewport, ventana
  o la separación entre el adaptador de la guarda y el modo de preparación.
  El adaptador de captura/input exige puerto entero y target hexadecimal antes
  de abrir Node; no puede aceptar `--prepare` ni acceder al flujo de preparación.
- En este incremento rige la instrucción actual de **solo pruebas offline**:
  no se iniciaron clientes, juegos, paneles ni motores; no hubo capturas, inputs
  reales, gasto ni acceso a perfiles. No se comprobó ni intervino el estado actual
  de los diagnósticos anteriores. `require_calibrated_client()` permanece intacto;
  panel/supervisor, Steam, Detener real y farmeo triple siguen pendientes.
  Respaldo de código y pruebas: `runs/startup-offline-nwgq1_ap/`, ignorado por Git.

Contrato CDP: [Target.createTarget](https://chromedevtools.github.io/devtools-protocol/tot/Target/#method-createTarget),
[Browser.setWindowBounds](https://chromedevtools.github.io/devtools-protocol/tot/Browser/#method-setWindowBounds)
y [Page.navigate](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-navigate).

### Arranque posterior y diagnóstico offline por etapas — 2026-10-08

- La suite final del incremento anterior terminó con **413 tests, 404 pasan y
  9 omisiones existentes** (191,002 s). Resultado confirmado en la conversación
  anterior; no se ha vuelto a consultar su log en este incremento.
- Durante las pruebas gráficas posteriormente autorizadas, ambos perfiles del
  bot completaron Home→Settings→Home y perfil→Home con guardas reales. Personal
  mostró **FMANI** y Perfil 1 **KORTZ**. Play/Fullscreen se pulsaron manualmente;
  ese resultado **no certifica el arranque automático**.
- Tras autorización específica se pidió abrir Bit Heroes una sola vez en el
  Steam existente, sin reiniciarlo: personaje **BRANDONR2600**, imagen 1920×1080,
  perfil→Home y Home→Settings→Home contrastados, sin farmeo ni gasto. Se reutilizó
  solo en el diagnóstico el FrameServer antiguo, después de vincular su proceso
  y nodo. Falta integrar esa compatibilidad en el supervisor multicuenta.
- `prepare_brave` ahora también intenta Play/Fullscreen del sitio, foco del
  canvas y comprobación final de la cadena web. Solo esos dos botones DOM,
  target propio y sin overlays; no pulsa coordenadas del juego. Una restauración
  vacía adicional del kiosco solo se retira si URL y DOM están vacíos. Viewport
  vacío y documento cargado se esperan de forma acotada antes de actuar.
- Las regresiones offline cubren esas carreras, pero el último arranque automático
  de ambos perfiles **siguió fallando** después de verificar la ventana vacía.
  No hay evidencia suficiente para atribuirlo a una causa concreta. No aumentar
  timeouts, repetir clics ni debilitar guardas para disimularlo.
- El error genérico impedía localizar el paso. El adaptador devuelve ahora solo
  una etapa fija: `connection`, `blank`, `play`, `fullscreen`, `canvas` o `snapshot`.
  Python muestra una etiqueta propia tras validar forma, tipos y lista cerrada;
  nunca incorpora errores CDP, títulos, URLs, DOM ni otros datos web al mensaje.
  El éxito y el protocolo de la guarda activa no cambian; no implica reintentos.
- Verificación enfocada: **21 pruebas Python y 26 Node pasan**. La regresión de
  diagnóstico falló antes del cambio y pasa con WebSocket/pipe nativos contra CDP
  ficticio. Una mutación en memoria de la lista segura fue detectada; fuentes
  originales intactas. Sintaxis Python/Node y `git diff --check` correctos.
  Suite completa final: **415 tests, 406 pasan y 9 omisiones existentes**, 207,258 s,
  sin DISPLAY, WAYLAND_DISPLAY ni NIRI_SOCKET; no se omitieron pruebas adicionales.
- En este nuevo incremento rige otra vez **solo offline**: no se iniciaron ni
  inspeccionaron clientes reales, no hubo capturas/inputs ni acceso a perfiles.
  Los últimos diagnósticos gráficos podrían seguir abiertos; **su estado actual
  no se ha comprobado ni intervenido**. Las validaciones anteriores no renuevan
  autorización para tocar esos clientes.
- Se conservan `require_calibrated_client()`, umbrales `.97/12`, pausa ante
  UNKNOWN, exclusividad y límites de gasto. Lanzador, panel/supervisor, STOP con
  motores reales y farmeo triple siguen sin certificar. Sin dependencias nuevas,
   commits ni publicación. Respaldo de este cambio: `runs/startup-stages-offline-p7hx4isg/`.

### Prueba online renovada, sin farmeo — 2026-10-08

- Autorización actual del usuario: probar online las tres cuentas sin gasto;
  acordar los límites antes de iniciar farmeo. No autoriza compras ni aventuras.
- Los tres clientes ya estaban abiertos. Se reutilizaron sus procesos, sin
  iniciar duplicados ni leer perfiles, credenciales, títulos o URLs de iframe.
  Los endpoints se identificaron por PID/perfil/puerto, ventana X y propietario
  PipeWire actuales, no reutilizando metadatos históricos.
- Ambos Brave estaban en Play. `finishPreparation()` sobre esos targets propios
  completó Play/Fullscreen y su guarda final en ambos, sin cambios de código,
  timeouts, umbrales o guardas. Esto **no valida un arranque desde perfiles
  cerrados ni el flujo completo de `prepare_brave()`**: la causa del fallo anterior
  sigue sin determinarse.
- `BraveGuard` y `GamescopeCapture` reales confirmaron imagen 1920×1080 antes y
  después de copiarla. Se cerró NEWS en Personal, se abrió el perfil de ambos y
  Escape devolvió HOME conservando la guarda web. Los anuncios globales taparon
  parcialmente los encabezados de FMANI/KORTZ; no se cambiaron preferencias.
- Steam estaba DISCONNECTED. Se pulsó RECONNECT una sola vez, contrastado con
  las plantillas existentes. La transición inicial desconocida solo se observó,
  sin acciones ni reintentos; después llegó HOME. Perfil BRANDONR2600 leído
  gráficamente y cerrado con Escape; HOME confirmado. Se reutilizó su servidor
  de imagen antiguo tras vincular su PID y el target PipeWire, sin reiniciar Steam.
- Los tres juegos quedaron vivos y en HOME. Los FrameServer temporales de Brave
  terminaron con código 0 y retiraron sus SHM; el servidor antiguo de Steam y el
  panel existente se conservaron. No hubo motores, aventuras, gasto ni compras.
- Diagnóstico y capturas exclusivamente del juego: `/tmp/opencode/`, prefijo
  `bitheroes-online-20261008-`; script `bitheroes-online-check-20261008.py`.
  Archivos privados (0600), sin capturas del escritorio ni secretos.
- `git diff --check` pasa. No se reejecutó la suite ni modificó código del
  proyecto; el bloqueo Brave permanece. Supervisor/STOP con motores reales,
  arranque desde perfiles cerrados y farmeo simultáneo siguen pendientes.

### Arranque corregido y supervisor acotado — 2026-10-08

- En la fase online posteriormente autorizada se localizaron dos carreras: URL
  vacía transitoria al navegar y Fullscreen disponible antes de crear el canvas.
  La URL vacía solo se espera durante la navegación propia de arranque; nunca
  se acepta como identidad activa. Fullscreen espera al canvas y usa una única
  pulsación nativa CDP sobre el botón del sitio, tras hit-test; sin reintentos.
- `prepare_brave()` completo pasó después en ambos **procesos ya abiertos**, con
  geometría final 1920×1080. Perfil→HOME y captura/guardas se comprobaron sin
  farmeo. No equivale a validar el lanzador desde perfiles cerrados. Suite de esa
  fase: 415 tests, 406 pasan y 9 omisiones (233,232 s).
- La nueva instrucción del usuario vuelve a limitar el trabajo a **solo offline**.
  En el incremento del supervisor no se abrieron ni inspeccionaron clientes,
  paneles reales o perfiles, ni hubo captura del escritorio, input o gasto.
- `fishing_core.farm_multi` prepara un entorno independiente por cuenta, valida
  formato y separación de display/serial/PID/puerto/target y supervisa tres
  workers concurrentes. No descubre endpoints ni abre clientes. El preflight
  aplica `require_calibrated_client()` antes del primer worker: Brave sigue
  bloqueado y tampoco se inicia Steam parcialmente.
- `farm_all --single-dungeon` conserva la ruta configurada por cuenta pero fija
  Normal, 1 run, máximo 10 energía, cero oro y objetivos vacíos. Sin runas, otros
  modos, progreso previo ni reintentos; Special/sin calibrar se rechazan. STOP o
  pérdida del supervisor limpian el hijo de dungeon antes de soltar su lock.
- El panel tiene una entrada opt-in `farm_app --trial`, con endpoints JSON por
  stdin (máximo 8192 caracteres); sin flag conserva el START antiguo. Pantalla
  limitada, START/STOP por botón o espacio y sin guardar preferencias. El JSON
  contiene exactamente `personal`, `perfil-1`, `steam`; cada valor solo incluye
  `FARM_GAMESCOPE_DISPLAY`/`FARM_GAMESCOPE_SERIAL`, más los tres `FARM_BRAVE_*`
  del contrato para Brave. No se guardaron endpoints reales ni se activó el panel.
- Verificación offline: límites y fallos con dobles; supervisor probado con tres
  probes inertes, STOP selectivo y otro Python intacto. No son motores del juego.
  El dibujo del panel se comprueba en memoria con PIL, no en una ventana real.
  31 pruebas Node pasan; tres mutaciones de aislamiento, cuota y selección STOP
  detectadas en memoria. Suite Python completa: **437 tests, 428 pasan y 9 omisiones
  existentes** (223,957 s), sin DISPLAY, WAYLAND_DISPLAY ni NIRI_SOCKET. Sintaxis
  y `git diff --check` correctos; no se debilitaron ni omitieron pruebas adicionales.
- Pendientes antes de habilitar Brave: arranque desde perfiles cerrados, captura
  Steam antigua sin duplicar flujos, identidad/guardas de cada worker y STOP con
  motores reales. Farmeo triple todavía **no certificado**. Sin dependencias,
   commits o publicación; respaldo: `runs/multi-supervisor-offline-tkinba45/`.

### Preparación de STOP sin input — revisión solo offline, 2026-10-08

- Revisado el incremento `--stop-check` de panel → supervisor → worker → dungeon.
  Selecciona el backend de observación, bloquea clic/movimiento/rueda/Escape y
  exige HOME antes de publicar readiness con cuotas sin reservar. Se conserva el
  bloqueo del START de farmeo Brave y la exclusividad anterior.
- Corregidos con regresiones rojas→verdes: la restauración de foco podía cerrar
  avisos de Steam mediante una llamada directa; una captura antigua no verificable
  podía abrir un segundo flujo; un panel de observación sin endpoints podía caer
  en el flujo habitual; el lector accedía al mmap antes de comprobar su integridad.
- Steam antiguo se reutiliza **solo en observación**, verificando proceso propio,
  memoria privada y un único lector GStreamer del serial exacto. Restos no
  verificables detienen, sin borrar ni duplicar. El lector detecta sustitución,
  symlink y truncado antes del acceso; la carrera de truncado concurrente no queda
  eliminada por estas comprobaciones.
- Pruebas enfocadas: **155 tests, 149 pasan y 6 omisiones Tk existentes**; **31 tests
  Node pasan**. Tres mutaciones de foco, tamaño de memoria y bloqueo de duplicación
  fueron detectadas en memoria, sin modificar los archivos para esa comprobación.
  Flags, F8, IPC, pérdida del padre y plazo de observación cubiertos con dobles.
- Suite completa final, sin DISPLAY, WAYLAND_DISPLAY ni NIRI_SOCKET: **456 tests,
  447 pasan y 9 omisiones existentes** (213,403 s). Sintaxis de 13 archivos y
  `git diff --check` correctos; no se debilitaron ni omitieron pruebas adicionales.
- En esta revisión no se inspeccionaron ni iniciaron clientes, paneles o motores
  reales, ni hubo captura de escritorio, input o gasto. El script gráfico preparado
  no se ejecutó y no constituye evidencia. STOP real, captura Steam de farmeo,
  arranque desde perfiles cerrados y farmeo triple siguen **sin certificar**.
- Sin commits, publicación, dependencias ni cambios de preferencias; respaldo
  previo a la revisión: `runs/stop-check-review-offline-s5c301ed/`.

### Intento online autorizado y vuelta a offline — 2026-10-08

- Durante la autorización online posterior pasaron las guardas de las tres cuentas
  en observación, pero no se completó HOME/readiness simultáneo. El evento STOP
  del panel no llegó a enviarse: esta prueba **no certifica la parada real**.
- Se atendieron diálogos de inactividad, reconexión, recompensa gratuita y ventanas
  conocidas; aparecieron también perfil PvP y diálogo de historia. No se ejecutó
  una dungeon ni farmeo triple. Estas intervenciones no validan el arranque desde
  perfiles cerrados ni justifican eliminar el bloqueo Brave.
- La instrucción posterior de `AGENTS.md` restablece **solo offline**. Desde ese
  cambio no se inspeccionaron clientes, capturó imagen real ni enviaron inputs;
  no se revalidó el estado actual de juegos, paneles o servidores anteriores.

### Protección de captura Steam en farmeo — revisión offline, 2026-10-08

- El bloqueo de duplicación antigua solo cubría `start_frame_server(read_only=True)`.
  La ruta habitual/prueba de dungeon podía intentar abrir otro servidor. Ahora
  los restos antiguos (imagen, PID o enlace, incluido uno roto) también bloquean
  el farmeo, antes de lanzar procesos o reutilizar un servidor de cuenta.
- `FrameServer` comprueba lo mismo tras obtener su lock y antes de consultar
  PipeWire o crear memoria. No borra ni modifica los restos; la reutilización
  verificada sigue permitida exclusivamente en observación. Steam sin esos
  archivos conserva su ruta de arranque. No se habilita Brave.
- Dos regresiones fallaron antes del cambio en nueve subcasos; después pasan.
  Las mutaciones en memoria de ambas guardas fueron detectadas, sin editar
  archivos para esa comprobación. Se añadió también el caso positivo sin restos.
- Suite completa offline, sin DISPLAY, WAYLAND_DISPLAY ni NIRI_SOCKET: **459 tests,
  450 pasan y 9 omisiones existentes** (403,329 s). **31 tests Node pasan**;
  sintaxis de 13 archivos Python y `git diff --check` correctos. Los mensajes de
  supervisor de esta suite proceden de dobles/probes, no de farmeo real.
- Sigue pendiente comprobar STOP con motores reales, arranque desde perfiles
  cerrados y compatibilidad de captura Steam durante farmeo. No se ejecutó el
  diagnóstico gráfico ni se completó la prueba triple en esta revisión offline.
- Sin commits, publicación, dependencias ni cambios de preferencias. Respaldo:
  `runs/steam-stream-guard-offline-5oges9_z/`.

### Lanzador Brave: exclusividad ante metadatos inciertos — solo offline, 2026-10-08

- Al retomar ya existían `launch_brave()` y las referencias de recompensas gratuitas
  Trials/Fishing; se conservaron junto al resto del trabajo local. El registro
  histórico informa dos lanzamientos desde perfiles cerrados que pasaron; no se
  revalidaron clientes, endpoints, capturas ni pantallas durante esta revisión.
- `require_closed_profile()` ignoraba errores de lectura y podía omitir un perfil
  activo si el argv estaba truncado, malformado o escapado. También se añadió el
  caso de un Brave vivo cuyo ejecutable aparece como eliminado tras una actualización.
  Ahora esas incertidumbres bloquean antes de crear otro cliente, sin leer perfiles
  ni mostrar los datos consultados. La desaparición del proceso sigue tolerada.
- Tres regresiones rojas→verdes cubren seis fallos iniciales; una comprobación del
  llamador verifica bloqueo antes de `Popen` y liberación del lock en ambas cuentas.
  **29 tests Brave pasan**, **31 Node pasan** y cuatro mutaciones de las guardas
  fueron detectadas en memoria, sin modificar archivos para esa comprobación.
- Suite completa final sin DISPLAY, WAYLAND_DISPLAY ni NIRI_SOCKET: **468 tests
  Python, 459 pasan y 9 omisiones existentes** (478,526 s). Sintaxis de 13 archivos
  Python y del adaptador Node, más `git diff --check`, correctos. Los mensajes de
  Quest/cuentas corresponden a dobles y probes offline, no a entradas reales.
- No se inició ni inspeccionó ningún cliente, panel o motor real; no hubo captura,
  input, gasto, cambios de preferencias, dependencias, commits ni publicación.
  Brave sigue bloqueado, Steam antiguo solo se reutiliza en observación y quedan
  pendientes HOME/identidad/STOP integrados y el farmeo triple real.
- Respaldo previo: `runs/brave-launch-review-offline-hffgf65e/`.
