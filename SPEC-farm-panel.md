# farm-panel

## Objetivo
El acceso habitual abre Bit Heroes Farm Bot con Dungeons primero y Fishing
segundo. Conservar el panel/motores de pesca existentes y sus preferencias.

## Estructura, estilo y comandos
Reutilizar `FISHING_BOT_APP.py` y CustomTkinter 6.0.0;
componente de dungeon en `fishing_core/dungeon_panel.py`, entrada
`FARM_BOT_APP.py`. `./ABRIR_BOT.sh` abre el panel, nunca inicia una run.
Usar controles nativos etiquetados, p. ej. `CTkTabview.add("Dungeons")`.
Fuente: https://customtkinter.tomschimansky.com/documentation/widgets/tabview/

## Pruebas y aceptación
`.venv/bin/python -B -m unittest discover -s tests`
Verificar panel real sin motores: Dungeons inicial; selección de Bob cambia
a Dryad's Heart; errores visibles para nombres sin ruta; Fishing sigue disponible.
No permitir dos modos activos simultáneamente; restaurar panel tras F8/parada.

## Límites
No cambiar la apariencia del escritorio ni sustituir preferencias personales.
Mostrar claramente catálogo no validado y pausar rutas todavía no reconocidas;
no presentar un selector como si acreditara farmeo real.

## Primera pasada visual · 2026-10-03
- Referencias: ventanas de dificultad, Settings y Team de las fixtures locales;
  capturas oficiales: https://store.steampowered.com/app/666860/Bit_Heroes_Quest/.
- Fondo propio de mampostería azul oscura; interiores marrón piedra, marco
  plateado en relieve y títulos dorados. Sin copiar imágenes ni fuentes del juego.
- START verde y DETENER rojo en ambas pestañas, con texto, foco de teclado y
  estados habilitado/deshabilitado conservados. Selectores cuadrados y legibles.
- No modificar motores, rutas, presupuestos, preferencias ni apariencia del PC.
- Comprobación visual sin motores: `.venv/bin/python -B scripts/comprobar_panel_farm.py`.
- Limitación previa local: Tk 9 del Python de uv solo enumera `fixed`, sin Xft;
  ignora tamaños/familias y algunos glifos. No se reemplazó el entorno.
  Referencia: https://github.com/astral-sh/python-build-standalone/issues/740.
