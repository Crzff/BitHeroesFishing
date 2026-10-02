# v0.1.0-beta.2 — Selección de Steam y protección de ventana

Bit Heroes Fishing Bot para Windows, extensión **AUDIT-R3.15+WINDOWS.1**.
Corrige el inicio que solo aceptaba Chrome. **Steam es experimental**:
ventana, foco y START comprobados, sin una pesca completa validada en ese cliente.

## Descargar e instalar

1. Detén y cierra los paneles anteriores. Descarga
   **BitHeroesFishing-v0.1.0-beta.2-source.zip** y descomprímelo en otra carpeta.
2. Instala **Python 3.13 de 64 bits**, Tcl/Tk, pip y Python Launcher desde python.org.
3. Ejecuta **INSTALAR.bat**, después **COMPROBAR.bat**.
4. Abre Steam o Google Chrome, pantalla principal 1920×1080, START visible.
   Steam requiere área de juego 1920×1080 en (0,0), sin bordes ni desplazamiento.
5. Ejecuta **ABRIR_BOT.bat**, elige **Steam / Chrome / Auto** y pulsa INICIAR BOT.
   **F8 detiene ambos motores.** Steam no necesita Chrome abierto.

La descarga **no es un ejecutable portable**. La primera instalación necesita
Internet para descargar dependencias. Abrir el panel no inicia la pesca.

## Incluye

Selector de cliente, enfoque inicial y guardias de ventana compartidas por los
dos motores. Detiene la sesión si pierde foco, se minimiza, cambia de pestaña o
se mueve/redimensiona. **No funciona en segundo plano** ni se reanuda solo.
Conserva CAST 32 ms, políticas, contador de cebos único y cierre final.

**139 pruebas públicas aprobadas**. Panel real, enfoque de Steam y bloqueo al
minimizar comprobados sin iniciar motores. Inventario, CAST, CATCH y cierre en
Steam siguen pendientes de validación real. No se modifica ningún archivo del juego.

[Apoyo voluntario en Ko-fi](https://ko-fi.com/fmani3496).

## Advertencias

Proyecto no oficial y beta: revisa las reglas del juego y el riesgo de sanciones.
No garantiza siempre CAST máximo, capturas exitosas ni compatibilidad con otras
escalas o disposiciones. Los restantes son estimados, no un recuento final.

El código propio usa MIT; los gráficos y marcas del juego conservan sus derechos.
Consulta el README y THIRD_PARTY_NOTICES.md. Reporta errores en Issues sin adjuntar
datos personales. El apoyo económico es opcional y no desbloquea garantías.
