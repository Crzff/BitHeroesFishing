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

## Multicuenta — 2026-10-07

Alcance confirmado: tres cuentas distintas (Personal, Perfil 1, Steam), simultáneas.
Asignación: Personal/fmani, Perfil 1/Kortzz, Steam/brandonr2600.
El usuario autorizó dos perfiles Brave nuevos y aislados, conservando los originales.
Contrato del primer incremento: `SPEC-multi-account.md`.

1. Aislar estado, locks, IPC y registros por cuenta; probarlo offline.
2. Fijar display/nodo PipeWire por sesión sin fallback y bloquear relanzamientos
   globales; comprobar guardas con ventanas y fotogramas sintéticos.
3. Preparar perfiles vacíos exclusivos del bot, sin iniciar navegador ni juego.
4. Ambos perfiles autenticados manualmente e identidades FMANI/KORTZZ contrastadas
   en el juego, sin sesiones originales duplicadas. Capturas separadas y roundtrip
   Home→Settings→Home con Escape CDP validados, manteniendo canvas 1920×1080.
    Antes de habilitar Brave: certificar la guarda de contenido y el Escape integrados,
    validar Detener del panel/parada conjunta, Steam y arranque estable desde perfiles
   restaurados. Luego integrar las tres sesiones y demostrar farmeo simultáneo.

   Incremento offline: cierre ordenado del lector GStreamer probado con vídeo
   sintético; una parada con fmani real también dejó gamescope vivo. Quest de
   Personal incorpora la variante observada con regresión offline y umbrales
   intactos. Mantener Brave bloqueado hasta conectar y validar las guardas reales;
   las pruebas manuales no certifican el supervisor.

   Parada posterior: ambos flujos cerraron sin abortar gamescope. Atajo F8 nativo
   configurado con autorización, respaldo y validación de niri; SIGINT selectivo
   comprobado con tres probes, sin cerrar procesos ajenos. La combinación Fn+8 del
    usuario no activó la comprobación del atajo: la parada física no está aprobada.
    Suite posterior: 380 tests, 371 pasan, 9 skips.

    Decisión posterior: el usuario pide usar Detener del panel y dejar el diagnóstico
    del RK61/Fn+8 para no retrasar la integración. Atajo normal restaurado y ninguna
    ventana/proceso de diagnóstico activo; sin permisos de administrador utilizados.
    STOP reutiliza la parada conjunta selectiva existente, también al cerrar un panel
    en marcha. Tres probes por cuenta se detienen y otro Python queda vivo; mutación
     detectada. Pendiente comprobar esa acción con motores reales, no repetir Fn+8.

    Incremento 2026-10-08: guardas de proceso/perfil/puerto CDP, foco y geometría
    web conectadas a captura e input; Escape por CDP, sin fallback nativo en Brave.
    Hit-test contra overlays antes de clic/rueda y limpieza de Escape por EOF,
    incluso si muere el padre. Transporte nativo de Node probado contra CDP
    ficticio en loopback; mutaciones de escala, identidad, overlays y reintento
    detectadas. Brave no reintenta paradas de seguridad ni acepta otra identidad
    automáticamente. Las guardas, captura y Escape del mismo runtime se validaron
    después con ambos Brave: Home→Settings→Home y perfil→Home, sin gasto. Personajes
    FMANI y KORTZ (cuenta Kortzz). Se corrigieron incompatibilidades observadas de
    ruta/argv/clase/iframe, sin identificar Brave por su título web.
    Siguiente: convertir la preparación de ventana nueva en arranque estable y
    repetir desde los perfiles cerrados, previa confirmación de exclusividad;
    identificar Steam y conectar supervisor/Detener con motores reales.
     El bloqueo de Brave sigue activo. Diagnósticos y endpoints propios cerrados.

     Incremento posterior, solo offline por la instrucción actual: preparación
     explícita `prepare_brave(pid, port)` sobre proceso propio ya iniciado. Crea
     ventana vacía y confirma cerrado el juego restaurado antes de navegar;
     rechaza ambigüedad, geometría incorrecta, PID terminado/cambiado y EOF del padre.
     No se conecta todavía al panel. El lanzador desde perfiles cerrados y la
     validación Play/Fullscreen/X/canvas/identidad de ambos juegos siguen pendientes;
      no repetir pruebas gráficas sin autorización actual y exclusividad confirmada.

     Pruebas posteriores autorizadas: Personal/FMANI,
     Perfil 1/KORTZ y Steam/BRANDONR2600 contrastados; todos completaron
     Home→Settings→Home sin gasto. Steam se abrió una sola vez en el cliente
     existente y reutilizó su captura antigua identificada. Esos resultados
     manuales no certifican el supervisor ni un arranque automático estable.

     Siguiente incremento, actualmente solo offline: Play/Fullscreen del sitio
     añadidos al adaptador con controles DOM/hit-test y geometría final estrictos.
     El arranque automático todavía falla en ambos perfiles tras la ventana vacía;
     no integrar el lanzador ni habilitar Brave hasta localizarlo. Diagnóstico
     acotado a seis etapas fijas, sin datos web; 21 tests Python/26 Node pasan y
     una mutación de la lista segura es detectada. No se inspeccionaron ni tocaron
     los últimos clientes gráficos, que podrían seguir abiertos. Antes de cualquier
     nueva prueba real: autorización actual, exclusividad y revalidar los procesos.
     Suite final offline: 415 tests, 406 pasan y 9 omisiones existentes (207,258 s).

Este incremento no activa farmeo Brave sin esa validación; Steam antiguo se conserva.
Verificar sin acceso gráfico:
`env -u DISPLAY -u WAYLAND_DISPLAY -u NIRI_SOCKET .venv/bin/python -B -m unittest discover -s tests`.

Incremento posterior: preparación completa de ambos Brave ya abiertos pasó tras
corregir las carreras de navegación/canvas, dentro de la fase online autorizada.
Luego el usuario volvió a exigir solo offline. Supervisor limitado y panel opt-in
conectados y probados con dobles/probes: 1 Normal, máximo 10 energía y cero oro,
sin reintentos. Brave sigue bloqueado antes del primer worker. Pendientes: abrir
desde perfiles cerrados, captura Steam antigua y STOP/farmeo con motores reales;
no repetir interacciones gráficas sin nueva autorización vigente.
Verificación final de este incremento: 437 tests Python, 428 pasan y 9 omisiones
existentes (223,957 s); 31 Node pasan y tres mutaciones detectadas. Diff correcto.

Preparación posterior de STOP, revisada únicamente offline: `--stop-check` recorre
panel/supervisor/worker/dungeon con backend sin input; HOME y cuotas cero antes de
readiness. Steam antiguo solo se reutiliza en observación tras verificar su origen;
restos inciertos no permiten duplicar flujos. Foco directo, endpoints ausentes y
memoria modificada tienen regresiones rojas→verdes. 155 pruebas enfocadas, 149
pasan y 6 omisiones Tk existentes; 31 Node y tres mutaciones detectadas en memoria.
Suite completa final offline: 456 tests, 447 pasan y 9 omisiones existentes
(213,403 s); sintaxis de 13 archivos y `git diff --check` correctos.
Siguiente: no ejecutar el script gráfico ni habilitar Brave con la restricción
vigente. STOP real, arranque cerrado y captura Steam durante farmeo requieren nueva
autorización y revalidación de exclusividad/endpoints. Sin commits ni publicación.

Revisión posterior: la autorización online permitió comprobar las tres guardas,
pero HOME/readiness no se completó y no se envió el evento STOP del panel. No hubo
dungeon; no certifica STOP o farmeo. `AGENTS.md` restablece después solo offline.
Corregida offline la protección de captura antigua Steam: los restos de imagen/PID
también bloquean la ruta de farmeo y el constructor directo, sin borrar archivos
ni abrir PipeWire. Reutilización únicamente en observación; Brave sigue bloqueado.
Regresiones rojas→verdes y dos mutaciones detectadas en memoria. El siguiente paso
real sigue requiriendo autorización nueva, identidad y endpoints revalidados;
no ejecutar el diagnóstico gráfico con la restricción vigente. Sin commits.
Verificación completa offline: 459 tests Python, 450 pasan y 9 omisiones existentes
(403,329 s); 31 Node pasan. Sintaxis de 13 archivos y `git diff --check` correctos.

Revisión posterior del lanzador, solo offline: conservar `launch_brave()` y las
referencias Trials/Fishing ya presentes. Corregida la guarda de perfil cerrado:
metadatos ilegibles/incompletos/malformados bloquean y el argv escapado o un
ejecutable activo eliminado no ocultan un perfil abierto. Tres regresiones
rojas→verdes, cuatro mutaciones detectadas en memoria y llamadores de ambas cuentas
sin `Popen` ante incertidumbre, con locks liberados. 29 tests Brave y 31 Node pasan.
El registro histórico informa dos lanzamientos desde perfiles cerrados que pasaron;
no se revalidó su estado y no certifican el flujo integrado. Siguiente: HOME/cuenta,
STOP real y captura Steam durante farmeo, solo con nueva autorización online;
mantener bloqueado Brave y la captura antigua limitada a observación. Sin commits.
Suite final offline: 468 tests Python, 459 pasan y 9 omisiones existentes (478,526 s);
31 Node pasan. Sintaxis de 13 archivos Python, adaptador Node y diff correctos.
