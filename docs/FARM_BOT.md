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
