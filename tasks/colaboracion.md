# Registro Claude + Codex

Formato: fecha · id · quién · tarea · resultado · pruebas · pendiente.

## 2026-10-09
- setup · Claude · Puente `scripts/claude_codex_write.sh` (workspace-write, lock, 15 min) y reglas en
  CLAUDE.md. Conexión de solo lectura comprobada (análisis real de `farm_multi.py`).
- Estado inicial: suite 475 tests OK (3 omitidas). Brave habilitado solo desde el supervisor
  multicuenta (`FARM_SINGLE_DUNGEON`/`FARM_MULTI_FARM`) con identidad viva comprobada.
- t1-run-farm · Codex · run_farm anuncia cada cuenta al terminar (sondeo), una cuenta parada no detiene
  a las demás; pruebas de independencia, STOP/KeyboardInterrupt, preflight y CLI; pruebas del panel
  multicuenta aisladas en temporal. · Aceptado tras revisión del diff. · Codex: 43 enfocadas OK (su sandbox
  no permite sockets/Tk/locks: 14 errores ajenos). Claude, entorno real: 481 tests OK (3 omitidas),
  configs reales intactas (md5).
