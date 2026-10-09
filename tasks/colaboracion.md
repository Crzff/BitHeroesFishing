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
- t2-brave-reconnect · Codex · GamescopeIO.rebaseline_web(): tras RECONNECT renueva la guarda Brave para la misma
  ventana/PID/puerto/target (identidad comparada); mensaje CDP genérico con un reintento, 'Cambió la identidad'
  definitivo; farm_all sale con 1 si algún modo no terminó OK. · Revisión Claude: la renovación iba después de
  la espera (que captura con la guarda vieja) → redelegado.
- t2b-reconnect-order · Codex · renovación en bucle (2 s, hasta 90 s) antes de esperar; réplicas fallidas
  cerradas. · Claude añadió 6 s de espera previa (el iframe recarga ~4 s tras RECONNECT).
  · Entorno real: 489 tests OK (3 omitidas), configs intactas. Pendiente: validación en vivo.
- Error de Claude: lanzar el supervisor con `bash … &` hace que ignore SIGINT y STOP no lo para; lanzar
  siempre desde Python (como el panel) con SIGINT por defecto.

- t3 (Codex): huecos de runa vacíos (INSERT) se saltan; 493 OK.
- t4 (Codex, timeout 124 pero diff completo): Mercader → DECLINE; 495 OK.
- t5 (Codex, timeout 124 con diff completo): SETTINGS ampliado, IDLE_PROMPT, EVENT_WINDOW; 500 OK.
- Claude: CDP de Brave fallaba al cargar escenas (Unity bloquea el iframe >1,5 s); timeouts 8 s/30 s. En vivo: KORTZZ completa dungeon + RERUN, FMANI rechaza familiares; ajustes aplicados en las 3 cuentas.
- t7 (Codex): Gauntlet en hueco Trials, REDUCED EFFECTS/BATTLE TEXT; 508 OK. GvG pendiente (auto mode bloqueó aceptar la confirmación de gremio en la calibración).
- t8a/t8b (Codex) boosts: en vivo FMANI ya activos, Steam consumió 4, KORTZZ consumió Speed y la compra paró por icono de tienda animado (arreglado con máscara).
- t12a/t12b (Codex) backend CDP: validado en vivo, ciclo completo de KORTZZ sin gamescope. Calibración rueda: mouseMoved previo + deltaY 100/paso.
- Fase 2 (seguridad) s1–s4 (Codex) hecha: escrituras privadas, identidad CDP, compras seguras, retención, plazo supervisor, hashes, intermediario CDP por pipe. Pendiente DACL Windows y lock con red.
