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
2. Abre **Bit Heroes de Steam** (experimental) o Kongregate en **Google Chrome**.
3. Deja visible la pantalla principal, el menú **Fishing con Play**, o **START**.
   El bot abre Fishing, pulsa Play y espera al personaje si hace falta.
   No dejes resultados ni un CAST pendiente al iniciar una sesión nueva.
4. Mantén la disposición compatible. La implementación usa coordenadas fijas:
   una resolución correcta por sí sola no demuestra que zoom y escala coincidan.
5. Steam: título `Bit Heroes`, ejecutable `Bit Heroes.exe`, área de juego
   **1920×1080 en (0,0)**. Usa pantalla completa sin bordes. No copies el bot a
   la carpeta de Steam, no modifiques DLL ni archivos del juego.
6. Chrome: título `Play Bit Heroes Online | Kongregate - Google Chrome`,
   ventana ocupando la pantalla principal y disposición compatible.

Steam **no necesita Chrome**. No se identifica el juego en Brave, Edge,
Firefox u otro idioma. El juego debe permanecer visible y en primer plano;
no hay modo de pesca en segundo plano ni minimizado.
Ko-fi y GitHub sí pueden abrirse en tu navegador habitual.

## 4. Abrir y detener

`ABRIR_BOT.bat` abre solamente el panel. Pulsa INICIAR BOT cuando el juego esté
preparado. Elige **Steam / Chrome / Auto** en el panel. Auto solo acepta una
ventana inequívoca; si ambos clientes están abiertos, selecciona el que usarás.
El inicio verifica la vista compacta y enfoca la ventana elegida sin un clic de
pesca. CONTROL entra a Fishing desde la pantalla principal, pulsa Play y espera
hasta 60 s a que aparezca START; entonces realiza el inventario inicial.
Si ya está en START, no vuelve al menú ni envía Play. No toca New Bait,
Shop, Events u otros modos de farmeo. Un modal desconocido detiene el recorrido
al agotar la espera; no lo cierra a ciegas.

Si Windows rechaza el cambio de foco, no inicia los motores. Si el juego pierde
el foco, se minimiza, cambia de pestaña, se mueve o redimensiona durante la
sesión, el bot se detiene y no se reanuda solo. Recupera START antes de iniciar
una sesión nueva. La selección del cliente se aplica solo a esa sesión.

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
Get-FileHash .\BitHeroesFishing-v0.1.0-beta.3-source.zip -Algorithm SHA256
```

Compáralo con el publicado. Un hash coincidente comprueba integridad respecto
de ese archivo; **no es una firma digital ni una certificación de seguridad**.
No desactives el antivirus para ejecutar una descarga: revisa cualquier alerta.
