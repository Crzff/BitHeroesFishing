# Cómo funciona

## Dos motores, responsabilidades separadas

El panel inicia una sesión nueva con dos procesos Python. CONTROL identifica
pantallas y gestiona entrada a Fishing, START, CAST, inventario, recompensas y modales. CATCH
observa el minijuego y es el único que decide y envía su clic.

La comunicación usa archivos por sesión y bloqueos de intento para evitar
duplicados. Una sesión nueva tiene otro identificador y no importa presupuestos
ni bloqueos de sesiones anteriores.

## Secuencia habitual

```text
pantalla principal → Fishing → Play → esperar llegada
                                       ↓
START → inventario inicial único → START → CAST
                                      ↓
                         CATCH o recompensa directa
                                      ↓
                     resultado → cierre confirmado
                                      ↓
                    otro START o parada con cero
```

También acepta el menú Fishing ya abierto o START. La navegación exige varias
lecturas estables y otra captura fresca antes de cada clic; envía Fishing y Play
como máximo una vez cada uno. Tras Play solo espera, sin repetir clics durante
el viaje. El límite del recorrido es 60 s; F8 y las guardias siguen activos.
No entra en Shop, Events u otros modos ni reclama New Bait, y no usa su temporizador.

La lectura inicial puede abrir el selector de cebos para inspeccionarlo y
cerrarlo. No compra, cambia equipo ni selecciona una rareza automáticamente.
La compatibilidad con transiciones de rareza o inventarios con scroll no está
certificada.

## CAST

Lee mínimo, máximo y valor de la barra de la caña. El predictor usa
observaciones recientes y una demora experimental de **32 ms**, no una medición
de la latencia universal del juego. Revalida el estado antes del input.

Chrome conserva el perfil histórico de seis muestras y capturas de hasta 15 ms.
Steam usa cuatro muestras y hasta 45 ms para permitir capturas a ritmo de frames.
Si no hay una predicción utilizable cerca del pico, propone otra captura y solo
autoriza la alternativa al leer el máximo exacto en esa verificación fresca,
con historial ascendente. Esta rama no predice ni garantiza el valor retenido.
Ambas rutas mantienen verificación hasta 80 ms, contexto completo menor de 200 ms
y cancelación si el envío programado llega con más de 3 ms de retraso.

El panel distingue **input enviado**, **valor retenido observado** y
**lectura no confirmada**. Alcanzar el máximo no está garantizado.

## CATCH

El detector contextual y el predictor usan observaciones recientes. La guarda
del ajuste actual rechaza modelos incoherentes con la lectura más reciente.
El envío del clic, la respuesta del juego, el resultado y su cierre son
evidencias diferentes: el panel no suma un clic como una captura exitosa.

## Cebos y resultados

El presupuesto parte de una lectura inicial fiable y descuenta una vez por
CAST enviado. Los restantes que ves son **estimados**. No se vuelve a contar el
inventario entre pescas ni al terminar. Una lectura desconocida no equivale a cero.

CONTROL confirma la estabilidad y frescura del cierre del resultado. Con cero
estimados se detiene después del último cierre, sin otro START. Los contadores
del panel separan CATCH SUCCESS, recompensas directas, FAILED y ciclos completos.

## Panel y seguridad

El selector **Auto / Steam / Chrome** identifica una ventana por ejecutable,
clase y título. Ambos motores reciben la misma identidad y posición, sin
modificar variables de entorno globales. Las consolas arrancan minimizadas sin
activar otra ventana. El bot no modifica ni inyecta código en el cliente del juego.

Las guardias comprueban foco, visibilidad, minimización, identidad y geometría
en el bucle y antes de los clics. Si falla una comprobación, se solicita la parada
compartida. No se recupera foco automáticamente durante una sesión: no pesca en
segundo plano y nunca continúa una sesión interrumpida con el mismo presupuesto.

Durante la pesca utiliza una vista compacta fija en una región comprobada de
la pantalla. Comprueba su rectángulo real y que DETENER no quede recortado.
Al detenerse restaura la vista normal. Siempre visible solo cambia la preferencia
del panel; no adapta las coordenadas del juego a otras pantallas.

F8, DETENER o cerrar el panel paran la sesión. El modo normal puede continuar
después de cerrar un FAILED; no equivale a la herramienta privada de supervisión
de pruebas. Ante una anomalía, detén el bot y revisa el estado manualmente.

## Datos locales

El funcionamiento genera registros en `runs/` y archivos de log junto al
programa. Pueden contener rutas, tiempos, cantidades y capturas de pantalla.
No se incluyen sesiones reales en esta distribución. No subas esas carpetas
completas a GitHub y revisa cualquier adjunto antes de compartirlo.

El motor no incorpora un servicio remoto para enviar tus registros. El
instalador necesita acceso a PyPI; los enlaces de apoyo abren el navegador solo
cuando los pulsas.
