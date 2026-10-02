# Instalación en Windows

## 1. Descargar y descomprimir

Descarga el ZIP de la beta en **Releases → Assets**. Descomprímelo completo:
`fishing_core/` y `assets/` deben permanecer junto a `FISHING_BOT_APP.py`.
No muevas un archivo aislado ni lo ejecutes desde el explorador del ZIP.

El paquete actual necesita **Python 3.13 de 64 bits**; no contiene un ejecutable
autónomo. Obtén Python únicamente desde [python.org](https://www.python.org/downloads/windows/).
Incluye Tcl/Tk, pip y Python Launcher durante la instalación.

## 2. Instalar dependencias

Haz doble clic en `INSTALAR.bat`. El instalador crea un entorno virtual local
`.venv` y usa `requirements.txt`. Descarga paquetes de PyPI, muestra los errores
y no inicia el bot. No solicita administrador ni instala dependencias globales.

Alternativa desde PowerShell, abierta en la carpeta descomprimida:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B scripts\comprobar.py
.\.venv\Scripts\python.exe -B FISHING_BOT_APP.py
```

No necesitas activar `.venv` ni cambiar la política de ejecución de PowerShell.

## 3. Preparar el juego

1. Pantalla principal a **1920 × 1080**.
2. Abre Bit Heroes de Kongregate en **Google Chrome**.
3. Ve al minijuego de pesca y deja START visible, sin resultados o CAST pendientes.
4. Mantén la disposición compatible. La implementación usa coordenadas fijas:
   una resolución correcta por sí sola no demuestra que zoom y escala coincidan.
5. Comprueba el título de la ventana:
   `Play Bit Heroes Online | Kongregate - Google Chrome`.

El enfoque actual no identifica el juego en Brave, Edge, Firefox u otro idioma.
Ko-fi y GitHub sí pueden abrirse en tu navegador habitual.

## 4. Abrir y detener

`ABRIR_BOT.bat` abre solamente el panel. Pulsa INICIAR BOT cuando el juego esté
preparado. El inicio verifica la vista compacta y enfoca Chrome sin un clic de
pesca. Al llegar a START se realiza el inventario inicial de la sesión.

**F8 detiene ambos motores.** También sirven DETENER BOT y cerrar el panel.
No hay reanudación automática después de una parada del usuario. No pulses
REINICIAR para recuperar un minijuego a medias: vuelve primero a START manualmente.

## Actualizar o desinstalar

Detén el bot antes de actualizar. Descomprime cada versión en una carpeta nueva;
no copies sesiones ni presupuestos de `runs/` a la nueva instalación. Repite
INSTALAR para crear el entorno de esa versión.

Para desinstalar, detén todos los procesos y elimina la carpeta descomprimida.
Python es una instalación independiente y no se elimina automáticamente.

## Comprobar una descarga

Cada Release incluye `SHA256SUMS.txt`. Puedes calcular el hash del ZIP:

```powershell
Get-FileHash .\BitHeroesFishing-v0.1.0-beta.1-source.zip -Algorithm SHA256
```

Compáralo con el publicado. Un hash coincidente comprueba integridad respecto
de ese archivo; **no es una firma digital ni una certificación de seguridad**.
No desactives el antivirus para ejecutar una descarga: revisa cualquier alerta.
