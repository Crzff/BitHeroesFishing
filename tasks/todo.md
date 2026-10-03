# Linux — tareas

- [x] Backend Steam/niri: captura de ventana, foco, geometría, input y F8.
  - Captura actual Wayland persistente: pesca SUCCESS con CAST 48/48; F8 sin consumo.
- [x] Runtime y procesos Linux conservando Windows.
  - 184 pruebas pasan, 3 específicas de Windows omitidas; exclusividad real comprobada.
- [x] Panel, diagnóstico y lanzadores Linux.
  - Panel oculto/restaurado, instalador y diagnóstico comprobados; evidencia en `docs/LINUX.md`.
- [x] Evitar superficies X11 antiguas y procesos por frame en la ruta rápida.
  - Bucle nativo 6,378 ms; comprobación opt-in en `scripts/comprobar_captura_linux.py`.

## Trabajo posterior, no certificado por esta validación

- Sesiones largas y otras cañas/cantidades; Windows real y Brave.
- Aprender el flujo de farmeo en Steam, sin compras ni gasto de gemas automático.
  Investigación compartida: `docs/BIT_HEROES_FARMEO.md`; no sustituye pruebas reales.
  - Antes de otra prueba: aislar cambios de pantalla/cursor fuera de inputs previstos;
    mantener parada por foco/cursor, no compensar ni relajarla sin conocer la causa.

## Bit Heroes Farm Bot — alcance inicial aprobado

- [x] Catálogo local de dungeons y rutas por familiar.
  - Aceptación: IDs únicos, rutas válidas y nombres desconocidos sin sustitución.
  - Verificar: `test_dungeons.py`; archivos: datos, lector puro y prueba.
- [x] Dungeons principal y Fishing secundario, sin arranque al abrir.
  - Aceptación: seleccionar Bob propone Z1D2 y Fishing conserva su flujo.
  - Verificar: panel real y suite; archivos: componente, panel, entrada/lanzador.
- [x] Reconocimiento de una ruta real y guardas de gasto.
  - Aceptación: UNKNOWN/precio/saldo inciertos nunca autorizan entrada.
  - Verificar: capturas etiquetadas y casos negativos; lector y pruebas.
- [ ] Una dungeon supervisada, cierre y repetición finita.
  - Aceptación: entrada/resultado únicos, F8/foco/derrota detienen y energía limitada.
  - Verificar: suite y una run registrada; runtime y proceso propio, sin CATCH.
  - Entrada/cierre de Z5D2 Normal comprobados en `20261002_140836_70c52d4b0fe5`,
    con pausa y continuación supervisada; repetición autónoma real aún pendiente.
  - F8 real `20261002_141807_df80cbf262f4`: 0 inputs/entradas, panel restaurado.
  - Oro autorizado durante la prueba: una persuasión Melvguin / 2.000 GOLD;
    reclutamiento desconocido. `max_gold=0` automático se conserva por ahora.
- [ ] Calibrar navegación de zonas y siguientes rutas; ampliar por familiar.
  - Z5D3 Heroic/Tealk: una entrada de 30 energía y cierre supervisado confirmados
    en `20261002_154802_ca83930eecdc`; límite 1 run/sesión, repetición pendiente.
  - Rechazo selectivo Mummih/Brute con referencia exacta y confirmación; Brute
    probado en dos ofertas de la misma dungeon. Objetivo/desconocido pausa.
- [ ] Integrar cuota/lectura de oro para Persuade, sin gemas ni gasto ilimitado.

Evidencia y límites completos: `docs/FARM_BOT.md`; no modificar la investigación
compartida para sustituir propuestas por hechos que todavía no se verificaron.
