# Sesiones simultáneas — Personal, Perfil 1 y Steam

## Objetivo y alcance confirmado
Tres cuentas distintas, concurrentes, no alternadas. El usuario aprobó crear dos
perfiles Brave exclusivos del bot sin copiar ni modificar los originales, y
separar primero las tres sesiones antes de integrar Brave. Este incremento cubre
ese aislamiento; no certifica la geometría web ni habilita el farmeo Brave real.
Asignación confirmada: Personal/fmani, Perfil 1/Kortzz, Steam/brandonr2600.

## Contrato
- `FARM_ACCOUNT`: `personal`, `perfil-1` o `steam`; ausente conserva el modo actual.
- Estado, IPC, registros, configuración y botín propios bajo `runs/accounts/<id>`.
- Exclusividad por cuenta; Steam comparte los locks con el modo antiguo para no
  ejecutar dos motores sobre la misma cuenta. Cada servidor de imagen tiene lock.
- En modo multicuenta solo gamescope: `FARM_GAMESCOPE_DISPLAY` y
  `FARM_GAMESCOPE_SERIAL` obligatorios. Nunca buscar otra pantalla/nodo al fallar.
- Brave añade `FARM_BRAVE_PID`, `FARM_BRAVE_CDP_PORT` (solo loopback) y
  `FARM_BRAVE_TARGET_ID` explícitos. El PID debe poseer el puerto y usar el perfil
  exclusivo de esa cuenta; pidfd, ventana y cadena de documentos/contextos fijados.
- Brave se selecciona por PID y clase del perfil aprobado, nunca por el título
  web cambiante; Steam conserva su selección antigua. No leer ni registrar títulos.
- Antes de capturas/inputs: foco real y geometría 1920×1080 de viewport, iframe,
  canvas y buffer, escala 1 y sin desplazamiento. Antes de clic/rueda: el punto
  debe atravesar los iframe hasta el canvas, sin overlays DOM. Escape por CDP
  al target fijado, sin `nativeVirtualKeyCode` ni fallback a XTest en Brave.
- Una parada de seguridad de Brave no se reintenta automáticamente ni permite
  continuar al siguiente modo; un nuevo START manual inicia otra validación.
- Memoria de imagen ligada a usuario, cuenta y ambos endpoints; un cambio de
  pantalla/nodo no reutiliza los fotogramas anteriores. Entorno fijo por proceso.
- Perfiles Brave nuevos, vacíos, privados y separados. Login manual; sin copiar
  cookies, credenciales, historial ni preferencias del navegador personal.
- Preparación explícita `prepare_brave(pid, port)`: proceso propio ya abierto y
  cuenta Brave fijada en el entorno. Exige propietario/perfil/puerto y pidfd vivo;
  devuelve únicamente el target nuevo. No lanza clientes ni cambia preferencias.
  El llamador debe confirmar exclusividad y arrancar con `--no-startup-window`.
  Se crea una página vacía, se confirma cerrada como máximo una restauración
  oficial y se verifica su geometría antes de navegar. Solo durante ese arranque
  puede retirar además una vacía del kiosco, tras verificar URL y DOM vacío.
  Automatiza únicamente Play/Fullscreen del sitio y foco del canvas, comprobando
  overlays y geometría web final. No sustituye guardas activas ni reintenta acciones.
  Ventana X, captura, Home y personaje requieren validación posterior; esta API
  no certifica ni habilita farmeo y su arranque automático real sigue pendiente.
  El protocolo `--prepare` conserva éxito `{id:0, ok:true, target}`; al fallar
  devuelve `{id:0, ok:false, stage}` con un valor fijo: `connection`, `blank`,
  `play`, `fullscreen`, `canvas` o `snapshot`. Sin texto web, URLs ni títulos.
   Python acepta solo esas etapas y muestra una etiqueta local; una respuesta
   malformada produce error genérico. El protocolo de la guarda activa no cambia.
- Lanzador opt-in `launch_brave(executable=None)`: solo cuenta Brave explícita con
  backend gamescope; lock por cuenta y perfil privado antes de crear su cliente.
  No certifica un perfil cerrado con metadatos ilegibles, incompletos o malformados;
  normaliza el argv aplanado y detecta también un ejecutable activo marcado como
  eliminado. Consulta metadatos, nunca archivos del perfil ni credenciales.
  Devuelve el proceso gamescope propio y sus endpoints, tras preparación web;
  no cambia el entorno del llamador ni habilita farmeo. Un fallo limpia su proceso
  y libera el lock. No está conectado al START del panel ni al supervisor.
- El relanzamiento global de Steam queda prohibido en sesiones identificadas.
- F8, foco, identidad de ventana, geometría y límites de gasto se conservan.
- Por decisión posterior del usuario, STOP/Detener del panel es la parada conjunta
  principal: señala solo motores propios de las tres cuentas, no clientes ni
  FrameServer. F8 se conserva sin certificar su pulsación física; su diagnóstico
  queda diferido y no es requisito para seguir integrando las cuentas. Validar
  Detener con motores reales sigue siendo necesario antes de certificar el farmeo.
- Cuentas nuevas sin preferencias guardadas: cuota de oro cero. No se modifica
  ningún valor de la configuración antigua ni preferencias ya guardadas.

## Estructura y estilo
Python y dependencias existentes, sin paquetes nuevos. Código en `fishing_core/`,
pruebas `unittest` en `tests/`, contrato y resultados en `docs/FARM_BOT.md`.
El transporte CDP usa el WebSocket nativo del Node ya instalado (estable desde
22.4), sin npm ni librerías nuevas. Si no está disponible, rechaza Brave.
Funciones pequeñas, constantes y rutas `Path`, como el código actual:
`PATH=state_root(ROOT)/'farm_config.json'`.

## Verificación y criterios de aceptación
- Pruebas rojas antes de implementar; helpers puros y procesos Python de prueba
  offline para demostrar tres locks simultáneos y aislamiento de archivos.
- Identificadores inválidos, endpoints ausentes/ambiguos y cambio de ventana
  deben detener la sesión, nunca seleccionar otra cuenta.
- Configuraciones existentes intactas; todos los tests previos siguen pasando.
- `env -u DISPLAY -u WAYLAND_DISPLAY -u NIRI_SOCKET .venv/bin/python -B -m unittest discover -s tests`.
- `git diff --check`.
- Brave, PipeWire real, juego y concurrencia gráfica quedan pendientes de una
  validación supervisada; no confundir simulación offline con certificación.
- Guardas/Escape conectados al runtime y probados offline; mantener el bloqueo
  de `require_calibrated_client()` hasta certificar ese mismo flujo con Brave real.
  Diagnóstico real posterior: ambos Brave completaron Home/Settings/perfil con
  dichas guardas, pero el arranque restaurado estable continúa pendiente y el
  bloqueo permanece. No convertir la sustitución manual de ventana en certificación.
- Preparación de ventana añadida con CDP ficticio y transporte nativo offline;
  no está conectada al panel/supervisor. Las pruebas posteriores con Play/Fullscreen
  manuales contrastaron los tres personajes, incluido Steam/BRANDONR2600; el
  arranque automático sigue fallando y no se considera certificado. El diagnóstico
  por etapas se valida offline, sin volver a intervenir clientes reales.
- Las seis pruebas Tk existentes requieren pantalla y se omiten por su propio
  `setUp` en esta ejecución headless; no eliminar ni debilitar esas pruebas.

## Límites
Siempre: pruebas offline, conservar Windows/niri, F8 y trabajo ajeno.
Consultar antes: dependencias, sustitución de preferencias, cambios del escritorio.
Nunca: iniciar juegos/paneles/motores para analizar, capturar escritorio, enviar
input, gastar recursos, leer perfiles originales, guardar secretos, hacer commits
o publicar sin petición.

Excepción posterior confirmada por el usuario: abrir ambos Brave aislados/juegos
y realizar validación gráfica supervisada de Home, Settings e identidad del
personaje. Confirmar antes cerrada esa misma cuenta en cualquier cliente original.
Login manual; sin leer secretos, importar perfiles originales, gastar recursos
ni eliminar guardas para probar. No confundir dos capturas concurrentes con
farmeo triple certificado.

Instrucción actual posterior: solo trabajo y pruebas offline. La excepción gráfica
anterior es histórica, no permiso vigente para abrir, inspeccionar ni enviar inputs
a clientes. El estado de los últimos diagnósticos reales no se ha vuelto a comprobar.

## Incremento del supervisor acotado — 2026-10-08

La aprobación posterior de una dungeon por cuenta queda subordinada a la nueva
instrucción de trabajo **solo offline**. No ejecutar la prueba real en este incremento.

- `farm_all --single-dungeon`: cuenta explícita, ruta de su configuración conservada,
  dificultad Normal, una run, 10 energía como máximo, cero oro y sin objetivos.
  No cambia preferencias, no usa progreso previo, runas, otros modos ni reintentos.
  Rutas Special o sin calibrar se rechazan, nunca se sustituyen.
- `farm_multi.run_trial(sessions)`: exactamente las tres cuentas; cada registro
  contiene solo sus variables de display/serial y, para Brave, PID/puerto/target.
  Sin descubrir endpoints, preparar páginas ni abrir clientes. Validación completa
  antes de crear workers; mismo display (incluido alias `.0`), serial, PID, puerto
  o target compartidos entre cuentas se rechazan. La validación previa es de formato
  y aislamiento, no acredita que el cliente siga vivo. El entorno del supervisor no cambia.
- El bloqueo `require_calibrated_client()` también se aplica antes del primer worker;
  por ahora rechaza Brave y evita una ejecución parcial de Steam.
- El panel acepta esta prueba solo con `--trial` y JSON por stdin; se conserva su
  flujo antiguo sin el flag. No escribe preferencias ni endpoints. Los estados
  muestran prueba limitada/parada, nunca que se gastaron todos los recursos.
- Un worker por cuenta, concurrentes, sin reinicio automático. Fallo, STOP o fallo
  parcial de lanzamiento señalan solo a los hijos propios y esperan su limpieza.
  STOP del panel/F8 reconocen el supervisor, no clientes ni servidores de imagen.
- Integración comprobada con dobles y procesos inertes offline; no certifica el
  arranque desde perfiles cerrados, servidores antiguos, STOP de motores reales
  ni farmeo triple. No activar el START multicuenta general mientras falten esos pasos.

## Preparación de STOP sin input — revisión offline, 2026-10-08

- `--stop-check` es opt-in en panel, supervisor y worker; requiere las tres cuentas
  y sus endpoints explícitos. No sustituye `--trial` ni desbloquea el farmeo Brave.
  Su ejecución con clientes reales sigue prohibida mientras rija solo offline.
- El proceso de dungeon selecciona `backend(read_only=True)` y únicamente observa
  HOME: dos lecturas antes de publicar readiness, límite de 60 segundos, sin navegar,
  reservar entradas ni enviar input. F8, IPC, identidad, foco y pérdida del padre
  conservan sus guardas. Una pantalla distinta de HOME detiene sin reconectar.
- Clic, movimiento, rueda y Escape quedan bloqueados; tampoco se cierran avisos
  de Steam ni se restaura el foco, incluso mediante una llamada directa.
- Solo en observación, Steam puede reutilizar su memoria antigua tras verificar
  propietario, permisos, tamaño, proceso Python de este proyecto, descriptor de
  memoria y único hijo GStreamer con el serial exacto. Si hay restos antiguos no
  verificables, se detiene: no crea otro flujo ni elimina esos archivos.
- En farmeo, cualquier archivo o enlace antiguo de imagen/PID de Steam bloquea
  el arranque, incluso si parece vivo un servidor de la cuenta. El constructor
  directo de `FrameServer` aplica también esa protección antes de abrir PipeWire
  o crear memoria nueva. No habilita la reutilización antigua con input.
- El lector comprueba identidad y tamaño de la memoria antes de leerla; sustitución,
  enlace simbólico o truncado detectados provocan parada. No promete eliminar la
  carrera de un truncado concurrente entre la comprobación y el acceso al mmap.
- Las pruebas son sintéticas y el panel se dibuja con PIL en memoria. No equivalen
  a verificar STOP de motores reales, compatibilidad Steam durante farmeo ni el
  arranque desde perfiles cerrados. No ejecutar el script gráfico preparado sin
  nueva autorización y revalidación de exclusividad/endpoints.

## Revisión posterior del lanzador — solo offline, 2026-10-08

El registro histórico de la conversación informa lanzamientos que pasaron desde
ambos perfiles cerrados. No se repitieron ni se inspeccionaron sus clientes en esta
revisión. Ese resultado no certifica el ciclo integrado hasta HOME, identidad,
STOP con tres motores ni farmeo. La restricción vigente continúa siendo offline;
Brave permanece bloqueado y la captura Steam antigua solo admite observación.
