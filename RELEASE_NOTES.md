# v0.1.0-beta.3 — CAST Steam y entrada automática a Fishing

Bit Heroes Fishing Bot para Windows, extensión **AUDIT-R3.15+WINDOWS.2**.
Corrige el bloqueo de CAST en Steam y permite iniciar desde la pantalla principal:
**Fishing → Play → esperar al personaje → START → pesca**.

## Descargar e instalar

1. Detén y cierra los paneles anteriores. Descarga
   **BitHeroesFishing-v0.1.0-beta.3-source.zip** y descomprímelo en otra carpeta.
2. Instala **Python 3.13 de 64 bits**, Tcl/Tk, pip y Python Launcher desde python.org.
3. Ejecuta **INSTALAR.bat**, después **COMPROBAR.bat**.
4. Abre Steam o Google Chrome, pantalla principal 1920×1080. Deja la pantalla
   principal, Fishing/Play o START; no inicies con un CAST pendiente.
   Steam requiere área de juego 1920×1080 en (0,0), sin bordes ni desplazamiento.
5. Ejecuta **ABRIR_BOT.bat**, elige **Steam / Chrome / Auto** y pulsa INICIAR BOT.
   **F8 detiene ambos motores.** Steam no necesita Chrome abierto.

La descarga **no es un ejecutable portable**. La primera instalación necesita
Internet para descargar dependencias. Abrir el panel no inicia la pesca.

## Incluye

Perfil CAST de Steam adaptado a capturas más lentas y alternativa con máximo
mostrado confirmado en una captura fresca. Chrome conserva sus límites históricos.
Navegación Fishing/Play con identidad estable, revalidación y espera hasta START.
No abre Shop/Events, no reclama cebos gratis ni entra en otros modos.

Conserva CATCH, demora CAST 32 ms, inventario inicial único, cierre confirmado y
F8. Ambos motores siguen vinculados a la misma ventana: se detienen al perder
foco o geometría. **No funciona en segundo plano** ni se reanuda solo.

## Pruebas y alcance

**159 pruebas públicas aprobadas** y cinco pescas reales Steam completas en tres
sesiones cortas: cuatro CATCH SUCCESS y una recompensa directa, con cierre
confirmado y sin otro START al alcanzar el límite. Se probó desde Fishing/Play,
pantalla principal y START. No se modifica ningún archivo del juego.

**CAST retenidos: 42–46 de máximo 48**, no siempre máximo. Steam sigue siendo
beta/experimental: una configuración 1920×1080 y una sola caña no certifican
otras cuentas, resoluciones o sesiones largas. La navegación nueva en Chrome
no tiene prueba real nueva. Los registros y capturas de cuenta no se publican.

Las Releases beta.1 y beta.2 permanecen intactas.

[Apoyo voluntario en Ko-fi](https://ko-fi.com/fmani3496).

## Advertencias

Proyecto no oficial y beta: revisa las reglas del juego y el riesgo de sanciones.
No garantiza siempre CAST máximo, capturas exitosas ni compatibilidad con otras
escalas o disposiciones. Los restantes son estimados, no un recuento final.

El código propio usa MIT; los gráficos y marcas del juego conservan sus derechos.
Consulta el README y THIRD_PARTY_NOTICES.md. Reporta errores en Issues sin adjuntar
datos personales. El apoyo económico es opcional y no desbloquea garantías.
