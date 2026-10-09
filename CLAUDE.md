@AGENTS.md

## Claude + Codex: análisis con menor uso de Claude

El usuario autorizó delegar el análisis offline de este proyecto a su Codex CLI
con la sesión ya iniciada. Claude coordina y verifica; Codex hace la exploración
extensa, el diagnóstico de código y las revisiones. No se cambia el proveedor
de Claude: Codex consume su propia cuota y el ahorro no está garantizado.

- Delega primero los análisis amplios a Codex; no explores todo el mismo código
  antes ni después. Resuelve preguntas pequeñas directamente, sin llamar a ambos.
- Encarga un lote acotado con objetivo, archivos iniciales y una pregunta concreta.
  Pide como máximo 8 viñetas/400 palabras con evidencias `ruta:línea`, incertidumbres
  y siguiente comprobación offline, salvo que el usuario solicite más detalle.
- Usa únicamente este puente; fija el proyecto y el sandbox `read-only`, no acepta
  flags de permisos y no permite a Codex escribir cambios:

```bash
bash /home/crzf/Proyectos/BitHeroesFishing/scripts/claude_codex_readonly.sh <<'TAREA'
Analiza [pregunta concreta]. Empieza por [archivos pertinentes].
Solo lectura y sin ejecutar el bot ni tocar el juego. Respeta AGENTS.md.
Devuelve hasta 8 viñetas/400 palabras con ruta:línea, límites y siguiente paso.
TAREA
```

- En Bash, usa `timeout: 600000`; para tareas largas, `run_in_background: true`
  y espera la notificación final, sin consultar el progreso repetidamente.
- Lee el resumen y verifica únicamente los hallazgos decisivos. Cualquier cambio
  de código o prueba en vivo queda fuera de esta delegación de solo análisis.
- Si hay un bloqueo de permisos, sandbox, autenticación o cuota, informa y para;
  no uses bypass, otro ejecutable ni repitas el análisis pesado con Claude sin pedirlo.
- Comprobación local del puente: `bash -n scripts/claude_codex_readonly.sh`.
  Prueba sin cuentas ni red: `.venv/bin/python -B -m unittest discover -s tests -p test_claude_codex_readonly.py`.

## Claude + Codex: colaboración con escritura (autorizada por crzf, 2026-10-09)

Claude es arquitecto y supervisor; Codex implementa. Claude delega por iniciativa propia
las tareas de programación acotadas, sin esperar a que el usuario lo pida.

- Puente: `scripts/claude_codex_write.sh <id-tarea> < tarea` → `codex exec --sandbox
  workspace-write` (solo el proyecto, sin red), 15 min por llamada, un Codex a la vez (lock).
  Registro completo en `runs/codex/<id>.log`; resumen en `runs/codex/<id>.last.md`.
- Un solo agente escribe a la vez: mientras Codex trabaja, Claude no edita; OpenCode cerrado
  o inactivo. Antes de delegar, punto de recuperación en Git (commit en la rama actual).
- Codex nunca ejecuta el bot, juegos, Brave, Steam ni gamescope: solo pruebas offline.
  Las pruebas en vivo las hace Claude, con las guardas activas.
- Claude revisa el diff y repite la suite completa antes de aceptar; si falla, redelega.
- Límites: máximo 3 rondas de corrección por tarea y 8 delegaciones por objetivo; al
  alcanzarlos, o ante un bloqueo de permisos/seguridad, parar y preguntar al usuario.
- Registro compartido de tareas, errores, decisiones y resultados: `tasks/colaboracion.md`.
- Prohibido: modificar fuera del proyecto, borrar información, acciones destructivas o
  desactivar protecciones sin autorización expresa.
