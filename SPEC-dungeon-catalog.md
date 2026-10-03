# dungeon-catalog

## Objetivo
Guardar todas las dungeons de las fuentes consultadas y seleccionar rutas por
familiar exacto. Separar catálogo público de disponibilidad real de la cuenta.

## Estructura y estilo
Datos locales en `assets/dungeons.json`, lector puro en
`fishing_core/dungeon_catalog.py`; pruebas `tests/test_dungeons.py` con unittest.
Ejemplo de contrato: `routes_for("Bob")` devuelve rutas, no envía input.
Sin descarga web durante el farmeo; Python 3.13 y stdlib para el catálogo.

## Comandos y pruebas
`.venv/bin/python -B -m unittest discover -s tests -p test_dungeons.py`
Comprobar IDs únicos, referencias válidas, Bob/Shrump → Z1D2, normalización
de apóstrofos y rechazo de nombres desconocidos/fusiones como capturas directas.

## Límites y aceptación
- Catálogo consultado: 77 dungeons/20 zonas y rutas de 220 familiares; fuentes
  comunitarias, no declaración de cobertura perpetua ni desbloqueos de cuenta.
- Nunca inventar una ruta ni confundir dungeons con flags, raids o fusiones.
- Catálogo y motor no deben hacer compras, fusión o Exchange.

Fuentes: https://bit-heroes.fandom.com/wiki/Zones y
https://bit-heroes.fandom.com/wiki/Familiar (consultadas 2026-10-02).
