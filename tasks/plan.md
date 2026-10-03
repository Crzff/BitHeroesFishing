# Adaptación Linux — Steam / niri

Alcance aprobado: Steam, Windows conservado, F8 y verificación local. El usuario
autorizó continuar hasta que funcione en Linux, sin nuevas pausas de aprobación.

1. Resolver el riesgo principal: captura e input reales de XWayland y foco niri.
2. Conectar ese backend al runtime, exclusividad y arranque de los dos motores.
3. Adaptar panel, diagnóstico y lanzadores; ejecutar pruebas y comprobación real.

Verificar cada paso con `unittest`; no hacer commits ni publicar sin petición.
Contrato: `docs/LINUX.md`. Estado: `tasks/todo.md`.

## Nuevo bot de farmeo — 2026-10-02

Mapa y contratos: `CAPABILITY_MAP.md` y `SPEC-*.md`. Alcance inicial aprobado:
catálogo → Dungeons principal/Fishing secundario → una dungeon supervisada →
repetición limitada. Conservar todo el trabajo Linux y la investigación ajena.

1. Catálogo local con rutas por familiar y pruebas puras; sin input.
2. Panel real con selección por dungeon/familiar; comprobar cambio a Fishing.
3. Capturas actuales de Quest/configuración/equipo/resultados; probar lector
   offline y controles de gasto antes de implementar acciones de entrada.
4. Conectar un proceso de dungeon, exclusividad, F8 y límites; ejecutar una
   run supervisada y comprobar cierre. No certificar rutas no recorridas.

Riesgos: wiki incompleta/desactualizada, ofertas de pago, interferencia de cursor,
desbloqueos y Auto nativo. Parar ante incertidumbre; no inventar botín o precios.
No commits, publicación, servicios nuevos ni migración de lenguaje.
