# dungeon-runner

## Objetivo
Recorrer HOME → Quest → zona → dungeon/dificultad → equipo/coste → una entrada;
supervisar Auto y cerrar un resultado confirmado. Repetir solo dentro de límites.

## Estructura, estilo y comandos
Runtime separado en `fishing_core/dungeon_runtime.py` y lector visual en
`fishing_core/dungeon_vision.py`, proceso `FARM_DUNGEON_PROCESS.py`.
Reutilizar `LinuxCapture`, `LinuxIO`, `WindowGuard`, `Mutex("LAUNCHER")`,
`Channel` y JSONL. Python/OpenCV/NumPy existentes, sin dependencias nuevas.
Ejemplo: `if energy is None: raise SafetyStop("Energia desconocida")`.
Suite: `.venv/bin/python -B -m unittest discover -s tests`.

## Pruebas y aceptación
UNKNOWN, compra, saldo/coste ilegibles, ruta bloqueada, F8 o pérdida de foco
no autorizan input. Entrada una vez; resultado una vez; límite finito de
runs/energía/tiempo; derrota detiene. Una run real supervisada antes de certificar.
Guardar referencias visuales recortadas, sin chat ni credenciales.

## Límites
Primera validación: Steam/niri 1920×1080 y una dungeon ya completada; mantener
equipo. Verificar auto-persuade oro/gemas apagado antes de entrar. Parar ante
oferta de familiar sin gastar; no prometer capturas sin Persuade autorizado.
Sin gemas/oro/compras/recargas/consumibles/fusiones/limpieza; no tocar Windows.
No compensar interferencias del ratón relajando guardas.

Fuente mecánica: https://bitheroes.zendesk.com/hc/en-us/articles/360031993472-What-are-Zones-Nodes-Dungeons-and-Stars
Las coordenadas y costes deben venir del cliente actual, no de esta descripción.

## Cambio de autorización — 2026-10-02

Ante la oferta real de Melvguin, crzf autorizó gastar oro. Se confirmó **una
persuasión supervisada por 2.000 GOLD**, sin Bribe/gemas ni compras; se terminó
solo la dungeon ya iniciada. El saldo exacto y reclutamiento no se certificaron.
Esto no habilita auto-Persuade nativo ni gasto automático sin cuota/lecturas.
El primer runner mantuvo `max_gold=0` y pausaba ante toda oferta de familiar.
Nueva política de oro automática pendiente de integración y verificación.

## Ampliación Tealk y rechazo selectivo — 2026-10-02

Una entrada Z5D3 Heroic, máximo 30 energía, equipo actual y sin compras/gemas.
Desactivar Decline duplicate familiars autorizado específicamente. Ruta limitada
a una run/sesión; otras dificultades no se habilitan por compartir menú.
«Si no estoy farmeando el familiar que quiero rechaza los demás»: rechazar solo
un nombre conocido, distinto del objetivo y estable, incluyendo la confirmación
específica de Decline. Objetivo/desconocido/sin objetivo: pausa, no gasto.
Referencias exactas iniciales Mummih/Brute; el catálogo no acredita reconocimiento.
Auto de combate no acredita Auto del mapa. Confirmaciones ajenas no autorizan YES.
Intenciones de rechazo inciertas bloquean continuación; no repetir ACCEPT.
Evidencia: `20261002_154802_ca83930eecdc`, CLEARED y Home, con supervisión.

## Zones y Escape — 2026-10-03

Autorizada exploración libre de estos menús, sin ACCEPT ni gasto. Aprender
Zones mediante nombres visibles, scroll acotado y confirmación del título
del mapa elegido; no inferir selección desde el número de fila. Zonas bloqueadas
o desconocidas detienen. El catálogo no habilita otras dungeons por sí solo.
Cerrar con Escape solo menús de navegación reconocidos, una pulsación por
nivel y destino estable confirmado. No enviar Escape en ofertas, confirmaciones
de gasto, combate, resultado ni pantalla desconocida; sin ráfagas ni reintentos.
Conservar foco/F8, equipo, ajustes, pesca, Windows y trabajo previo; referencias
sanitizadas, tests y navegación real sin entrada antes de declarar comprobado.
