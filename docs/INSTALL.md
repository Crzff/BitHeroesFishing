# Instalación y retención

El instalador usa `requirements.lock` con `--require-hashes` si existe; si falta,
conserva `requirements.txt`. No se pudo generar un lock verificable offline:
el entorno instalado no contiene wheels y los hashes de RECORD no son hashes
de los archivos que descarga pip. En un entorno con red y pip-tools disponible:

```sh
pip-compile --generate-hashes --output-file requirements.lock requirements.txt
```

Generar y revisar el lock para cada plataforma/Python soportados (Windows y Linux).
Alternativa: descargar todas las dependencias con `pip download -r requirements.txt
-d wheels`, obtener sus hashes con `pip hash wheels/*` y fijar también las transitivas.

Al iniciar supervisor/farm_all se eliminan sesiones con más de siete días de
inactividad, y después las más antiguas hasta un máximo conjunto de 2 GiB.
Solo se seleccionan directorios de sesión con ID generado por el bot; no perfiles,
configuraciones ni estado persistente. Los logs rotan a `.1` al superar 5 MiB.
`diagnostic_screenshots` en farm_config es `true` por defecto para crzf;
`false` desactiva los PNG de dungeon. Siempre se excluyen las filas y<100.
Un worker de farmeo sin salida durante 45 minutos queda PARADO «sin progreso»:
SIGINT, SIGTERM 30 segundos después y SIGKILL tras otros 30 segundos.
