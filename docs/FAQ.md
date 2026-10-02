# Problemas frecuentes

### No se encuentra Python

Instala Python **3.13 de 64 bits**, Tcl/Tk, pip y Python Launcher desde python.org.
Abre una terminal nueva y comprueba `py -3.13 --version`. El alias de Microsoft
Store llamado `python` no sustituye una instalación completa. Ejecuta INSTALAR.

### La instalación falla al descargar paquetes

Revisa conexión, proxy y el mensaje de pip. No desactives antivirus ni cambies
permisos globales. Conserva la consola del error y elimina datos personales
antes de adjuntar un fragmento en Issues.

### El panel no abre

Ejecuta COMPROBAR. Desde PowerShell puedes abrirlo con
`.\.venv\Scripts\python.exe -B FISHING_BOT_APP.py` para ver el error.
No ejecutes varios paneles con motores activos.

### No identifica la ventana del juego

Selecciona **Steam** para `Bit Heroes.exe` o **Chrome** para el título exacto
`Play Bit Heroes Online | Kongregate - Google Chrome`. Steam no necesita Chrome.
Auto se niega a elegir si detecta varias ventanas. Cierra duplicadas y deja la
pantalla principal, Fishing/Play o START. Brave y títulos traducidos no son
compatibles con ese enfoque automático.

### ¿Funciona mientras uso otra ventana o con el juego minimizado?

No. Lee píxeles visibles de la pantalla y envía input al juego en primer plano.
Ahora intenta enfocarlo al iniciar; después se detiene si pierde el foco, cambia
de pestaña o se minimiza. No vuelve a robar el foco ni reanuda una pesca a medias.

### ¿Steam está completamente validado?

No de forma universal. La beta.3 completó cinco pescas reales en Steam 1920×1080,
incluida la entrada desde la pantalla principal: cuatro CATCH SUCCESS y una
recompensa directa, con inventario inicial único y cierre de cada resultado.
Los CAST retenidos fueron 42–46 con máximo 48. Es una prueba corta en una sola
configuración, no garantía para otras cuentas, cañas, escalas o sesiones largas.

### ¿Puedo iniciar desde la pantalla principal?

Sí: INICIAR BOT abre Fishing, pulsa Play y espera al personaje hasta ver START.
También puedes iniciar con el menú Fishing abierto o ya en START. No toca Shop,
Events, New Bait ni otros modos. Si hay un popup desconocido, ciérralo manualmente
con el bot detenido y vuelve a iniciar; no compra ni reclama cebos automáticamente.

### Steam se queda en CAST con la beta.2

Actualiza a la beta.3 en una carpeta nueva y cierra los paneles antiguos: conservan
el código anterior en memoria. La corrección adapta el muestreo a capturas más lentas
de Steam sin desactivar las guardias. Vuelve a START antes de iniciar otra sesión.

### La resolución es correcta pero no detecta el juego

Las coordenadas también dependen de zoom, escalado, posición y disposición.
1920×1080 no garantiza coincidencia. Detén el bot y revisa la interfaz;
no fuerces lecturas ni cambies los umbrales a ciegas.

### ¿Siempre consigue CAST 40?

No. Lee el máximo de la caña e intenta alcanzarlo, pero los valores retenidos
pueden ser inferiores. Tampoco se promete captura exitosa en cada intento.

### ¿El cero del panel es un recuento real al terminar?

No: es inventario inicial menos CAST enviados. No hay recuento final. No añadas,
retires ni cambies cebos mientras una sesión usa ese presupuesto.

### ¿Puede continuar después de un FAILED?

Sí, el modo normal puede continuar tras su cierre. Detén con F8 si quieres revisar
el fallo. No se promete supervisión automática que repare todos los errores.

### ¿Qué hago si se queda un CAST o resultado abierto?

Pulsa F8. Recupera manualmente un START estable sin iniciar otra sesión a medias.
No uses un presupuesto anterior para continuar. Al iniciar de nuevo contará
inventario para una sesión nueva.

### ¿Hay riesgo para mi cuenta?

Sí. Es automatización no oficial: revisa las reglas del juego. El proyecto no
evita ni garantiza protección frente a restricciones o sanciones.

### ¿Es gratis? ¿Apoyar es obligatorio?

El código propio se publica bajo MIT. El apoyo por Ko-fi es voluntario, no
desbloquea una precisión garantizada ni es requisito para usar el bot.
