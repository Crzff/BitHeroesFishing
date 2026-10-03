# Bit Heroes Farm Bot

Alcance inicial confirmado por crzf el 2026-10-02. Fishing se conserva.

| Módulo | Responsabilidad | Depende de | Contrato |
| --- | --- | --- | --- |
| dungeon-catalog | Dungeons y rutas exactas por familiar, con fuentes | — | SPEC-dungeon-catalog.md |
| farm-panel | Dungeons principal, Fishing secundario y selección | dungeon-catalog | SPEC-farm-panel.md |
| dungeon-runner | Navegación, entrada supervisada y repetición acotada | dungeon-catalog | SPEC-dungeon-runner.md |

Orden: catálogo → panel → controlador. Compartir exclusividad, captura y F8;
no lanzar los motores de pesca para una dungeon. Plan: `tasks/plan.md`.
