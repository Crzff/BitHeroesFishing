# 🎣 Bit Heroes Fishing Bot

Automatización de la pesca de Bit Heroes para **Windows**, con un panel oscuro,
dos motores separados y parada de emergencia con **F8**.

<!-- PROJECT_LINKS_START -->
[![Estado](https://img.shields.io/badge/estado-beta-555555?style=for-the-badge)](#limitaciones)
[![Descargar](https://img.shields.io/badge/Descargar-ZIP-555555?style=for-the-badge)](https://github.com/Crzff/BitHeroesFishing/releases/tag/v0.1.0-beta.3)
[![Descargas](https://img.shields.io/github/downloads/Crzff/BitHeroesFishing/total?label=descargas&color=555555&style=for-the-badge)](https://github.com/Crzff/BitHeroesFishing/releases)
[![Licencia](https://img.shields.io/badge/c%C3%B3digo-MIT-555555?style=for-the-badge)](LICENSE)
<!-- PROJECT_LINKS_END -->

> **Proyecto no oficial.** La automatización puede incumplir las reglas del
> juego y causar restricciones o sanciones a tu cuenta. Revisa sus condiciones
> antes de usarlo. No garantiza capturas exitosas ni CAST máximo en cada intento.

![Panel del bot detenido, sin información de una cuenta](docs/images/panel.png)

## Qué hace

- **CONTROL** gestiona inventario, START, CAST, resultados y modales.
- Puede iniciar desde **pantalla principal → Fishing → Play → START**;
  espera al personaje antes de pescar. Si ya está en START, no repite el recorrido.
- **CATCH** decide y envía el clic del minijuego; CONTROL no lo sustituye.
- Lee los cebos **una vez al inicio de cada sesión** y muestra los restantes
  **estimados**: inventario inicial menos un cebo por CAST enviado.
- Confirma el cierre del último resultado antes de detenerse con cero estimados.
- Distingue CAST enviado de valor retenido, CATCH exitosos de recompensas
  directas y resultados FAILED de cierres completos.
- Ofrece **Siempre visible** y una vista compacta comprobada para no tapar
  el inventario ni las barras en la disposición compatible.
- Selecciona **Auto / Steam / Chrome** y vincula ambos motores a esa ventana.
  Steam tiene cinco pescas completas comprobadas en una configuración concreta;
  sigue siendo beta, no una certificación para todas las cuentas.

No compra ni reclama cebos gratis, no abre Shop/Events, no entra en otros modos,
no cambia equipo ni selecciona rarezas automáticamente.
F8, DETENER y cerrar el panel detienen la sesión; no la reinician solos.

## Requisitos

| Componente | Configuración de referencia |
| --- | --- |
| Sistema | Windows, Python de 64 bits |
| Python | **3.13**, con Tcl/Tk y Python Launcher |
| Pantalla principal | **1920 × 1080** |
| Cliente del juego | **Steam (experimental)** o **Google Chrome / Kongregate** |
| Juego | Pantalla principal, menú Fishing con Play o pesca con START; en primer plano |
| Disposición | Interfaz y escala compatibles con las coordenadas comprobadas |

**Steam no necesita Chrome abierto.** Se identifica `Bit Heroes.exe` por su
ejecutable, clase Unity y título `Bit Heroes`; no hace falta instalar el bot junto
al juego ni modificar sus archivos. Usa pantalla completa sin bordes: área de
juego 1920×1080 en la pantalla principal, sin desplazamiento.

Para Chrome se conserva el título exacto
`Play Bit Heroes Online | Kongregate - Google Chrome` y la disposición compatible.
Si Steam y Chrome están abiertos, elige uno: Auto no adivina entre dos ventanas.
**No funciona en segundo plano ni minimizado**: lee la pantalla y envía input
al juego visible. Al perder el foco, cambiar de pestaña o mover/redimensionar
la ventana, detiene la sesión. Brave y otras resoluciones no están certificados.

## Descarga

En [**Releases**](https://github.com/Crzff/BitHeroesFishing/releases), abre la última versión beta y descarga
`BitHeroesFishing-v0.1.0-beta.3-source.zip` de **Assets**.

**Esta descarga contiene código Python, no un .exe portable.** Python y una
conexión a Internet son necesarios para la primera instalación de dependencias.
No ejecutes el programa directamente dentro del ZIP.

## Instalación rápida

1. Instala [Python 3.13 de 64 bits](https://www.python.org/downloads/windows/).
   Incluye **Tcl/Tk**, **pip** y **Python Launcher**; activa *Add Python to PATH*.
2. Descomprime el ZIP en una carpeta donde puedas escribir, por ejemplo
   Documentos. No uses `Program Files` ni reemplaces una instalación en ejecución.
3. Haz doble clic en **`INSTALAR.bat`**. Crea `.venv` dentro de esa carpeta e
   instala las dependencias desde PyPI. **No necesita administrador.**
4. Ejecuta **`COMPROBAR.bat`** para revisar Python, dependencias, plantillas y
   resolución. Esta comprobación no inicia pesca ni envía clics.
5. Abre el juego en Steam o Chrome y deja visible la **pantalla principal**,
   el menú **Fishing / Play** o **START**. No dejes un CAST pendiente.
6. Haz doble clic en **`ABRIR_BOT.bat`**, elige **Steam / Chrome / Auto**
   y pulsa **INICIAR BOT** en el panel. Enfoca el juego e inicia el recorrido de
   pesca si hace falta; al aparecer START comprueba el inventario inicial.
7. Para detener: **F8**, **DETENER BOT** o cierra el panel.

Abrir el panel **no inicia la pesca**. No uses el ratón ni cambies la ventana,
la escala o los cebos durante una sesión. Supervisa los primeros intentos y
detén el bot si la pantalla no coincide con la configuración compatible.

Guía completa: [instalación](docs/INSTALACION.md) ·
[funcionamiento](docs/FUNCIONAMIENTO.md) · [problemas frecuentes](docs/FAQ.md).

## Limitaciones

- **Beta**, no una garantía de funcionamiento universal ni de ausencia de sanciones.
- CAST intenta alcanzar el máximo leído de la caña, pero **no siempre lo alcanza**.
- Steam admite capturas más lentas y una verificación alternativa del máximo
  mostrado; esa lectura no garantiza que el juego retenga el máximo.
- La entrada automática desde la pantalla principal se probó en Steam; en Chrome
  requiere la misma disposición y todavía no tiene una prueba real nueva.
- Los restantes son un presupuesto estimado, **no un recuento final de inventario**.
- Una lectura ambigua no se trata como cero.
- No se certifican inventarios con desplazamiento ni cambio automático de rareza.
- Un input enviado por el programa no demuestra recepción por parte del juego.
- El modo normal no es una supervisión externa que revise cada FAILED antes
  del próximo START; puedes detenerlo con F8 para revisar cualquier fallo.

Los resultados de pruebas anteriores son evidencia limitada a esas condiciones,
no una promesa para otras cuentas o sesiones. Más detalles en
[validación](docs/VALIDACION.md).

## Errores y sugerencias

Usa [**Issues**](https://github.com/Crzff/BitHeroesFishing/issues/new/choose) y la plantilla correspondiente. Indica versión,
Python, resolución, zoom y pasos para reproducir el problema. **No publiques
contraseñas, tokens, datos de pago, nombres de cuenta ni capturas completas del PC.**

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) antes de adjuntar registros.

## Apoyar el proyecto

<!-- SUPPORT_START -->
[![Apoyar en Ko-fi](https://img.shields.io/badge/%E2%99%A1_Apoyar-Ko--fi-555555?style=for-the-badge)](https://ko-fi.com/fmani3496)

Si te resulta útil, puedes apoyar a **Fmani** para dedicar tiempo a pruebas,
documentación y mejoras. Es voluntario: no desbloquea precisión garantizada,
ventajas dentro del juego ni es requisito para usar el bot. El botón del panel
abre el mismo perfil externo solamente cuando lo pulsas, con pesca detenida.
<!-- SUPPORT_END -->

## Licencia y atribución

El código propio se publica bajo [MIT](LICENSE). Las marcas, fuentes y gráficos
del juego siguen perteneciendo a sus respectivos titulares y **no se relicencian
bajo MIT**. Las referencias visuales de `assets/` son plantillas de reconocimiento,
no una copia del cliente del juego. Revisa [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Este proyecto no está afiliado ni avalado por los propietarios de Bit Heroes,
Kongregate o Google.
