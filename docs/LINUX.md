# Linux: Steam en niri / XWayland

## Objetivo y alcance autorizado

Adaptar el bot a este equipo CachyOS con niri, Steam y pantalla 1920×1080 a escala 1.
Conservar Windows, los motores CONTROL/CATCH, el presupuesto de cebos y la parada F8.
No cambiar las políticas de pesca ni prometer CAST máximo. Brave y otros compositores
no forman parte de esta primera adaptación.

## Implementación

- `fishing_core/linux.py`: identidad Steam por XWayland, foco real de niri,
  captura actual del compositor con `wlr-screencopy` y puntero virtual Wayland.
  `linux_capture.c` copia regiones a memoria compartida, sin procesos por frame,
  PNG, disco ni imágenes X11 antiguas; espera máxima de 750 ms y cierre al parar.
- Reutilizar `GameWindow`, `WindowGuard`, el IPC y los motores existentes.
- Exclusividad Linux con `fcntl.flock`; procesos sin flags ni consolas Windows.
- Panel Tk existente: se oculta al pescar y se restaura al parar. En Linux se
  selecciona Steam; F8 sigue disponible con el panel oculto. Windows conserva
  la vista compacta y sus opciones de cliente.
- Instalación en `.venv`, sin paquetes globales, servicios privilegiados ni cambios
  de credenciales, apariencia, SDDM o sesión gráfica.

## Comandos y estructura

Desde la raíz del proyecto:

```sh
./INSTALAR.sh
./COMPROBAR.sh
./ABRIR_BOT.sh
.venv/bin/python -B -m unittest discover -s tests -v
# Opt-in: enfoca Steam y comprueba la captura, sin clics ni pesca.
.venv/bin/python -B scripts/comprobar_captura_linux.py
```

Estilo: funciones y clases pequeñas como `game_window.py`, imports de plataforma
diferidos y `unittest` en `tests/`. Ningún módulo inicia pesca al importarse.
Abrir el panel no inicia pesca. El instalador comprueba Python 3.13 con Tk, no
reemplaza un entorno existente incompatible y rechaza una sesión del bot activa.
Requiere `uv`, `cc`, `flock` y cabeceras/biblioteca `libwayland-client`.

## Criterios y límites

- Rechazar juego ausente, duplicado, identidad cambiada, foco perdido, tamaño o
  escala incompatibles y captura inválida antes de enviar input.
- Confirmar los clics y F8 en una ventana de prueba antes de usar el juego.
- Ejecutar la suite completa; conservar las pruebas Windows específicas.
- Abrir y cerrar el panel real sin iniciar motores.
- No instalar nada como root ni modificar la otra copia `~/BitHeroesFishing`.
- Las comprobaciones técnicas sin pesca no certifican una captura real exitosa.

## Validación real — 2026-10-02

- Instalador compilado con `-Wall -Wextra -Werror`; diagnóstico completo correcto.
- Suite local: **187 pruebas ejecutadas, 184 pasan y 3 específicas de Windows se
  omiten en Linux**. La ejecución Windows real no se probó en este equipo.
- Sesión `20261002_081919_c42c4cc3dca1`, desde el panel real:
  HOME → Fishing → Play → auditoría fiable de 24 cebos → START → CAST → CATCH
  **SUCCESS** → TRADE → ITEMS → cierre confirmado en START. Un único ciclo,
  CAST retenido **42/48**, parada automática y panel restaurado.
- Sesión `20261002_082036_ab592cc8f264`: F8 detectado por ambos motores;
  panel restaurado en **0,614 s**, sin inputs al juego ni otro cebo gastado.
  Se rechazaron un segundo lanzador y el instalador durante esa sesión.
- En pruebas anteriores se rechazó una lectura ambigua del 9 de Hooked Spoon:
  un brillo coloreado tocaba su columna. La corrección separa únicamente ese
  fragmento y conserva umbrales de confianza, rechazo de ruido neutro y recortes.
- Una desconexión `0x201` hizo detener el bot sin pesca. Se reconectó manualmente
  una vez durante la supervisión; el bot no reconecta ni cambia cuentas solo.
- **Validación del backend final:** `20261002_130141_aca877edd096`, inventario
  fiable inicial 21, START → CAST retenido **48/48** → un CATCH **SUCCESS** →
  TRADE → ITEMS → cierre confirmado en START. Panel oculto/restaurado y ambos
  motores detenidos al límite de un ciclo. Ninguna política temporal relajada.
- F8 con el backend final: `20261002_130233_2f3a361ebe4d`, ambos motores
  detenidos y panel restaurado en **0,516 s**, sin inputs al juego ni otro cebo.
  Exclusividad y rechazo del instalador durante la sesión comprobados de nuevo.
- Revisión posterior: una inversión de la confirmación del cursor en memoria
  hizo fallar tres pruebas; el archivo original no se modificó para ese experimento.
- Dos pruebas se detuvieron al perder foco, una antes de CAST y otra sin inputs.
  No se desactivó esa protección ni se reanudó un intento consumido.

Evidencia limitada a este equipo y esta caña/disposición; una pesca completa con
el backend final y otra histórica con X11. También hubo dos ciclos FAILED durante
las pruebas de `grim`, antes de sustituirlo. No se afirma una tasa de éxito.
No valida sesiones largas, todas las cantidades de inventario, CAST máximo,
Brave, otros monitores o compositores. No usar el ratón, cambiar de ventana ni
abrir otra sesión de la misma cuenta durante la pesca. El modo normal conserva
`max_ciclos_por_sesion=0` (continuo); las pruebas usaron un límite temporal de un
ciclo sin modificar esa configuración. Ninguna compra, recarga o cambio de equipo.

En la exploración posterior de Settings se observaron desplazamientos del cursor
no confirmados (por ejemplo, solicitado 1250×600 y observado 1252×600) y cambios
de pantalla fuera de los inputs previstos. La causa no está confirmada. Se rechazó
el clic, se añadió la posición al diagnóstico y no se inició otra dungeon ni raid.
Coordinar una sesión sin entradas simultáneas antes de certificar farmeo.

## Diagnóstico de captura y rendimiento

Durante la exploración de dungeons se contrastaron imágenes X11 con el compositor:
X11 podía conservar una superficie antigua. No se usa como respaldo de captura.
`grim` daba imágenes actuales, pero su proceso/copia completa por frame impidió
el primer CATCH (`FRAME_LENTO`: intervalos medianos 23,10 ms, límite 20 ms).

Medidas del mismo bucle de captura/guardias/clasificador/detector, 100 muestras,
descartando cinco iniciales, con `cProfile` y Steam en START:

| Cambio | Mediana antes → después | Decisión |
| --- | --- | --- |
| Decoder OpenCV, región 1310×320 | 19,13 → 17,60 ms | Útil temporalmente; eliminado junto con PPM al adoptar SHM |
| Recorte 1235×279 con los mismos ROIs completos | 17,60 → 16,26 ms | Conservado solo en Linux; Windows mantiene su región |
| `grim` por stdout frente a `memfd` (solo proceso) | ≈9,40 → ≈9,37 ms | Descartado: dentro del ruido |
| Wayland persistente, región 1235×279 | 16,26 → **7,13 ms** | Conservado; p95 **7,96 ms**, 95/95 muestras bajo 20 ms |

La comprobación ejecutable sin profiler midió mediana **6,378 ms**, p95
**7,037 ms**, sin fugas de descriptores y rechazando capacidad de buffer insuficiente.
No mide FPS del juego ni garantiza todas las oportunidades. Se conservaron las
guardias antes/después de copiar, umbrales OCR, antigüedad máxima y un clic por intento.

## Fuentes de las interfaces

- IPC niri: https://github.com/YaLTeR/niri/blob/main/niri-ipc/src/lib.rs
- Xlib: https://python-xlib.github.io/python-xlib_15.html
- Captura Wayland: https://github.com/swaywm/wlr-protocols/blob/master/unstable/wlr-screencopy-unstable-v1.xml
- Referencia consultada: https://github.com/emersion/grim/blob/master/main.c
- XTEST: https://github.com/python-xlib/python-xlib/blob/master/Xlib/ext/xtest.py
- Puntero Wayland: https://github.com/swaywm/wlr-protocols/blob/master/unstable/wlr-virtual-pointer-unstable-v1.xml

XTEST no mueve el cursor de este XWayland; se usa el protocolo nativo de puntero
virtual de niri, sin ydotoold ni acceso a `/dev/uinput`. Los dos adaptadores C
se compilan localmente con `cc` y `libwayland-client`, ya disponibles aquí.
