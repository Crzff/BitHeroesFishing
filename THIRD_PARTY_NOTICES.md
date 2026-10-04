# Recursos y dependencias de terceros

## Bit Heroes y servicios externos

Bit Heroes, sus gráficos, fuentes, iconos y marcas pertenecen a sus respectivos
titulares. Kongregate y Google son marcas de sus respectivos propietarios.
Este proyecto no está afiliado, avalado ni patrocinado por ellos.

Los archivos `assets/ui_templates.npz`, `assets/cast_digits.npz`,
`assets/bait_templates.npz` y `assets/fishing_navigation.npz` contienen referencias mínimas de reconocimiento
derivadas de la interfaz: máscaras, glifos y algunos iconos de cebos. **No son
contenido original del autor ni se ofrecen bajo MIT.** No incluyen el cliente
del juego, una cuenta ni capturas completas de sesiones.

La licencia del código no concede derechos sobre los recursos del juego. Este
aviso tampoco sustituye permisos de redistribución ni una revisión legal. Si
eres titular y tienes una objeción, contacta al mantenedor mediante el repositorio.

`assets/dungeon_templates.npz` y `tests/fixtures/dungeons.npz` derivan también
de Bit Heroes: referencias y capturas locales sanitizadas para pruebas, no
recursos MIT. No se han publicado. El catálogo `assets/dungeons.json` utiliza
nombres/rutas de https://bit-heroes.fandom.com/wiki/Zones y
https://bit-heroes.fandom.com/wiki/Familiar, consultadas el 2026-10-02; conservar
atribución y revisar las condiciones/licencia comunitarias antes de redistribuir
datos derivados. No incluye textos completos de artículos.

## Python y paquetes

El ZIP de código no incorpora Python ni copias instaladas de los paquetes.
INSTALAR los descarga desde PyPI. Cada dependencia conserva su propia licencia:

| Paquete | Página oficial del paquete |
| --- | --- |
| mss | https://pypi.org/project/mss/ |
| numpy | https://pypi.org/project/numpy/ |
| opencv-python | https://pypi.org/project/opencv-python/ |
| customtkinter | https://pypi.org/project/customtkinter/ |
| Pillow | https://pypi.org/project/Pillow/ |
| darkdetect | https://pypi.org/project/darkdetect/ |
| packaging | https://pypi.org/project/packaging/ |

Revisa sus licencias para cualquier redistribución futura de binarios o paquetes
instalados. Los badges del README usan shields.io; Ko-fi gestiona el apoyo fuera
de la aplicación.

## Protocolos Wayland (Linux)

Los adaptadores C usan las firmas v1 de `wlr-virtual-pointer` y `wlr-screencopy`,
publicadas en https://github.com/swaywm/wlr-protocols/tree/master/unstable.

Copyright © 2019 Josef Gajdusek (virtual-pointer)
Copyright © 2018 Simon Ser; © 2019 Andri Yngvason (screencopy)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Interfaz del Farm Bot

- `assets/fonts/Silkscreen-*.ttf`: fuente Silkscreen de Jason Kottke, SIL Open Font
  License 1.1 (texto en `assets/fonts/OFL-Silkscreen.txt`), obtenida de
  https://github.com/google/fonts/tree/main/ofl/silkscreen.
- `assets/ui/*.png`: iconos de modo recortados de capturas locales de Bit Heroes para
  la app; derivan del juego, no son recursos MIT y no deben redistribuirse sin revisar
  los derechos del titular.
