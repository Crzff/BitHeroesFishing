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
- [x] Una dungeon supervisada, cierre y repetición finita.
  - Aceptación: entrada/resultado únicos, F8/foco/derrota detienen y energía limitada.
  - Verificar: suite y una run registrada; runtime y proceso propio, sin CATCH.
  - Entrada/cierre de Z5D2 Normal comprobados en `20261002_140836_70c52d4b0fe5`,
    con pausa y continuación supervisada; repetición autónoma real aún pendiente.
  - F8 real `20261002_141807_df80cbf262f4`: 0 inputs/entradas, panel restaurado.
  - Oro autorizado durante la prueba: una persuasión Melvguin / 2.000 GOLD;
    reclutamiento desconocido. `max_gold=0` automático se conserva por ahora.
  - Repetición autónoma certificada 2026-10-03: `20261003_131256_f3ef71365838`,
    6/6 runs Z5D2 Normal (62→~4 energía), 3 ofertas rechazadas sin objetivo,
    parada por límite de runs. Antes: 4/10 en `20261003_130308_1b472c88bb8f`.
- [ ] Calibrar navegación de zonas y siguientes rutas; ampliar por familiar.
  - Z5D3 Heroic/Tealk: una entrada de 30 energía y cierre supervisado confirmados
    en `20261002_154802_ca83930eecdc`; límite 1 run/sesión, repetición pendiente.
  - Rechazo selectivo Mummih/Brute con referencia exacta y confirmación; Brute
    probado en dos ofertas de la misma dungeon. Objetivo/desconocido pausa.
- [ ] Integrar cuota/lectura de oro para Persuade, sin gemas ni gasto ilimitado.

Evidencia y límites completos: `docs/FARM_BOT.md`; no modificar la investigación
compartida para sustituir propuestas por hechos que todavía no se verificaron.

## Multicuenta — Personal + Perfil 1 + Steam

Asignación: Personal = fmani; Perfil 1 = Kortzz; Steam = brandonr2600.

- [x] Estado, IPC, logs y exclusividad por cuenta, con Steam antiguo compatible.
  - Aceptación: tres procesos offline coexisten; un duplicado de la misma cuenta falla.
- [x] Aislamiento de endpoints explícitos y guardas sin fallback, validado offline.
  - Aceptación: ausencia/ambigüedad/cambio de ventana detienen; no se cierra Steam globalmente.
- [x] Dos directorios de datos Brave nuevos, vacíos y privados; originales intactos.
  - Preparación inicial vacía; ahora ambos tienen login manual. El perfil de Kortzz
    se reasignó íntegro a Perfil 1, sin copiar credenciales; Personal contiene fmani.
- [ ] Validar Brave real y su geometría, sin certificarlo solo con mocks.
  - Ambos Brave coexisten: ventanas y endpoints distintos, imagen/canvas 1920×1080,
     Home→Settings→Home con Escape CDP sin perder Fullscreen y personajes
     contrastados gráficamente. Aquella prueba no validó las guardas del runtime.
  - Perfil 1 restaurado daba 1920×1024; ventana nueva de kiosco validada después
    de cerrar el juego anterior, sin duplicar la misma cuenta.
  - Variante Quest de Personal añadida sin bajar umbrales: regresión roja→verde,
    negativos y mutación comprobados. Suite: 375 tests, 366 pasan, 9 skips existentes.
  - Token expuesto de Kortzz mitigado: cambio autorizado y confirmado por
     Kongregate, sin leer/guardar secretos; mecanismo respaldado por su documentación.
  - Lector GStreamer: cierre ordenado y liberación de proceso/hilo/tubería corregidos
    y comprobados offline; una parada posterior con fmani real dejó gamescope vivo.
  - Ambas paradas reales de FrameServer dejaron gamescope vivo y retiraron su SHM;
    se cerraron solo los diagnósticos propios.
  - Atajo niri F8 configurado con autorización y respaldo; orden SIGINT probada
    con tres workers inertes y proceso ajeno intacto. Fn+8 físico no certificado.
    Suite posterior: 380 tests, 371 pasan, 9 omisiones existentes.
  - [x] STOP/Detener del panel solicita la parada conjunta de motores propios;
    regresión con tres probes por cuenta y otro Python intacto, sin juegos ni GUI.
    El usuario difiere el diagnóstico físico de Fn+8; F8 se conserva, no certificado.
    Suite final: 383 tests, 374 pasan y 9 omisiones existentes.
   - [x] Guardas web/Escape integrados y comprobados offline (2026-10-08):
     proceso/perfil/puerto propios, foco, geometría efectiva y punto sobre canvas.
     Sin reintentos automáticos de seguridad en Brave; Steam antiguo conservado.
     CDP ficticio con transporte nativo real, liberación de Escape al morir el
     padre y cuatro mutaciones detectadas. No habilita aún el backend Brave.
     Suite: 405 tests, 396 pasan y 9 omisiones existentes; sintaxis/diff correctos.
    - [x] Guardas/captura/Escape reales validados con ambos Brave (2026-10-08):
      Home→Settings→Home y perfil→Home, contenido/buffer 1920×1080, escala 1.
      FMANI y KORTZ contrastados; cuenta pública de Perfil 1: Kortzz.
      Corregidos ruta oficial, argv aplanado, clase X e iframe remoto omitido;
      Brave se identifica por PID/perfil, sin leer su título web. 42 tests enfocados
      pasan; cinco mutaciones detectadas. Suite final: 407 tests, 398 pasan y
      9 omisiones existentes. Clientes/servidores propios cerrados.
     - [x] Preparación explícita de ventana probada offline (2026-10-08): cierre
       confirmado de restauración tardía antes de navegar, viewport vacío validado,
       pidfd/identidad y cancelación por EOF. 19 pruebas Python/18 Node enfocadas;
       tres mutaciones detectadas. No abre clientes al importar ni habilita Brave.
      - Suite final de aquella preparación: 413 tests, 404 pasan y 9 omisiones.
      - Prueba posterior autorizada: los tres personajes contrastados, Steam
        BRANDONR2600 y Home→Settings→Home sin gasto. Ambos Brave con Play/Fullscreen
        manuales; no certifica arranque automático ni supervisor. Steam reutilizó
        su flujo antiguo verificado, solo dentro del diagnóstico.
      - [x] Play/Fullscreen y diagnóstico de fallo por etapas cubiertos offline:
        21 pruebas Python/26 Node pasan; lista segura de etapas y mutación comprobadas.
        El arranque automático real de ambos perfiles sigue fallando: causa pendiente,
        no reintentar acciones ni relajar guardas. Instrucción actual: solo offline;
        no se comprobó ni intervino el estado de los últimos clientes gráficos.
        Suite completa final: 415 tests, 406 pasan y 9 omisiones existentes (207,258 s).
      - Pendientes: localizar el fallo con el diagnóstico seguro, después certificar
        arranque restaurado estable desde ambos perfiles cerrados y su lanzador;
        conectar panel/supervisor y flujo Steam antiguo, comprobar STOP con motores reales.
     No usar Fn+8 como bloqueo de la integración.
    Evidencias y límites: `docs/FARM_BOT.md`.
- [ ] Lanzamiento y farmeo de las tres cuentas a la vez, validación supervisada.

### Prueba online posterior — 2026-10-08

- Autorizada solo puesta en línea sin gasto; se reutilizaron los tres clientes.
- Play/Fullscreen con `finishPreparation()` pasó en ambos Brave; captura/guardas
  y perfil→HOME comprobados. Steam reconectado una vez, BRANDONR2600 y HOME
  confirmados. Servidores temporales Brave cerrados; clientes vivos, sin farmeo.
- No certifica `prepare_brave()` completo desde perfiles cerrados ni supervisor.
  Antes de farmeo: acordar límites, integrar y comprobar parada; guardas intactas.
- Sin código modificado ni suite reejecutada; `git diff --check` pasa.

### Supervisor acotado posterior — instrucción vigente: solo offline

- [x] Causa del fallo de preparación localizada y corregida: navegación transitoria
  y canvas aún ausente al pulsar Fullscreen. Preparación completa pasó en ambos
  Brave ya abiertos durante la fase online autorizada; no valida perfiles cerrados.
- [x] Supervisor de prueba de tres cuentas e integración opt-in del panel, offline.
  - Una Normal por cuenta, máximo 10 energía, cero oro/gemas, sin reintentos ni
    cambios de preferencias. Bloqueo Brave intacto antes de cualquier worker.
  - STOP, fallos parciales y pérdida del supervisor cubiertos; tres probes inertes
    detenidos y otro Python vivo. No confundir estos probes con motores reales.
  - 31 tests Node pasan y tres mutaciones fueron detectadas; dibujo PIL sin panel
    o escritorio real.
  - Suite completa offline: 437 tests, 428 pasan y 9 omisiones existentes
    (223,957 s). Sintaxis y `git diff --check` correctos.
- [ ] Validar arranque desde perfiles cerrados y compatibilidad de captura Steam
  antigua; después STOP con motores reales y prueba triple, con permiso vigente.
- No se inspeccionó ni intervino el estado de los clientes en este incremento
  offline. Sin commits; respaldo: `runs/multi-supervisor-offline-tkinba45/`.

### Preparación de STOP sin input — revisión solo offline

- [x] `--stop-check` separado de la prueba de dungeon y propagado hasta el backend
  sin input; HOME, F8, IPC, pérdida del padre y plazo cubiertos con dobles.
- [x] Reutilización de captura Steam antigua solo en observación, con identidad
  y serial verificados. Restos inciertos detienen sin abrir un segundo flujo.
- [x] Bloqueo de restauración de foco directa, panel sin endpoints y lectura de
  memoria modificada antes de comprobarla; regresiones rojas→verdes.
- Pruebas enfocadas: 155 tests, 149 pasan y 6 omisiones Tk existentes; 31 Node
  pasan y tres mutaciones detectadas en memoria. Dibujo PIL, no panel real.
- Suite completa final offline: 456 tests, 447 pasan y 9 omisiones existentes
  (213,403 s). Sintaxis de 13 archivos y `git diff --check` correctos.
- [ ] Validar STOP con motores reales, arranque desde perfiles cerrados y captura
  Steam durante farmeo. Requiere nueva autorización: sigue vigente solo offline.
- El script gráfico no se ejecutó en esta revisión. Sin commits ni publicación;
  respaldo: `runs/stop-check-review-offline-s5c301ed/`.

### Captura Steam — revisión posterior, solo offline

- Intento online autorizado anterior: las tres guardas de observación pasaron,
  pero no hubo HOME/readiness simultáneo ni evento STOP del panel. Sin dungeon;
  no certifica STOP real ni farmeo. La instrucción posterior vuelve a solo offline.
- [x] Impedir otra captura Steam en farmeo cuando quedan imagen/PID antiguos,
  incluso enlaces rotos o un servidor de cuenta aparentemente vivo. Protección
  también en el constructor directo; no borra restos ni habilita input Brave.
- Regresiones rojas→verdes y dos mutaciones detectadas en memoria; caso positivo
  sin restos cubierto. Reutilización antigua solo en observación, como antes.
- Suite completa offline: **459 tests, 450 pasan y 9 omisiones existentes**
  (403,329 s); **31 Node pasan**. Sintaxis de 13 archivos y diff correctos.
- [ ] STOP real, arranque desde perfiles cerrados y captura Steam durante farmeo
  siguen pendientes y requieren nueva autorización online. No revalidar endpoints
  ni ejecutar diagnósticos reales con la restricción actual.
- Respaldo: `runs/steam-stream-guard-offline-5oges9_z/`; sin commits ni publicación.

### Lanzador Brave — revisión posterior, solo offline

- [x] Lanzador opt-in implementado y probado con bootstrap/CDP ficticios; no está
  conectado al START. Se conserva el trabajo posterior de recompensas Trials/Fishing.
- [x] Bloquear lanzamientos con metadatos ilegibles, truncados o malformados,
  detectar argv escapado y ejecutable activo eliminado, sin leer perfiles.
  Tres regresiones rojas→verdes y cuatro mutaciones detectadas en memoria;
  llamador de ambas cuentas bloqueado antes de crear procesos y locks liberados.
  29 tests Brave y 31 Node pasan.
- Suite final offline: **468 tests Python, 459 pasan y 9 omisiones existentes**
  (478,526 s); sintaxis de 13 archivos Python, adaptador Node y diff correctos.
- El registro histórico informa dos lanzamientos desde perfiles cerrados que
  pasaron; no se repiten ni equivalen a certificación de HOME/STOP/farmeo integrado.
- [ ] Validar el ciclo cerrado→HOME/personaje→STOP con tres motores reales y
  resolver la captura Steam durante farmeo, únicamente con nueva autorización online.
- Brave sigue bloqueado; captura antigua solo en observación. No se inspeccionó
  ningún cliente ni se ejecutaron diagnósticos reales. Respaldo:
  `runs/brave-launch-review-offline-hffgf65e/`; sin commits ni publicación.
