# Validación y límites de la beta

Motor de referencia: **AUDIT-R3.15**. Extensión actual:
**AUDIT-R3.15+WINDOWS.2**, distribuida como **v0.1.0-beta.3**.
La extensión añade seguridad de ventana, perfil CAST de Steam y navegación a
Fishing. La versión pública y el perfil histórico son diferentes; las pruebas
reales nuevas son limitadas a la configuración descrita abajo.

## Evidencia previa

La revisión local R3.15 aprobó **252 pruebas**. Esas pruebas internas incluyen
fixtures y herramientas privadas que no se redistribuyen íntegramente aquí.
El repositorio público ofrece un subconjunto sin sesiones ni capturas de cuentas.
Las dos pruebas de geometría del detector que usaban capturas privadas se
sustituyen aquí por escenas sintéticas; no se presentan como ensayos reales.

En una sesión real anterior del motor R3.14 se observaron 221 CAST y 221 cierres
SUCCESS, con 198 CATCH y 23 recompensas directas. CAST retenido varió de 27 a 40.
R3.15 reprodujo esos registros offline y comprobó la GUI con motores detenidos.

**No fue una sesión real nueva de R3.15**, ni una certificación para otras cuentas,
escalas, resoluciones o cambios del juego. Los registros originales permanecen
privados por contener información de la cuenta. Esta documentación no permite
verificar independientemente todos esos resultados históricos.

## Qué se conserva

Se conservan CATCH, las plantillas de pesca y la demora CAST de **32 ms** de R3.15.
La beta.2 cambió el lanzador y WindowsIO para vincular la ventana y bloquear input
al perder foco o geometría. La beta.3 cambia el muestreo CAST solo para Steam y
añade plantillas mínimas de navegación. Chrome conserva sus límites CAST históricos.
No se presentan los archivos modificados como idénticos a los hashes R3.15.
CONTROL y CATCH siguen separados. El enlace de apoyo no inicia pesca ni procesa pagos.

La configuración de CI se ofrece en `docs/ci-windows.example.yml` como ejemplo
opcional, no como un workflow activo. Publicar esta beta no requiere ampliar el
permiso OAuth de GitHub a `workflow`. Las pruebas indicadas se ejecutaron
localmente; no se presentan como una ejecución de GitHub Actions.

## Comprobaciones públicas

La beta.1 pasó **123 pruebas públicas** en un entorno virtual nuevo.
La beta.2 pasó **139 pruebas públicas**, incluidas 16 nuevas pruebas de ventana,
propagación de identidad a los dos motores y bloqueo de input con foco perdido.
Se comprobó el panel real sin iniciar motores: el botón de apoyo aparece al
estar detenido y queda oculto en la vista compacta; DETENER sigue visible.
La beta.3 pasó **159 pruebas públicas**, incluidas reproducción sintética del
bloqueo CAST a 30 Hz, frescura, navegación acotada e integración Steam con IO/MSS
falsos. La suite interna completa pasó **290 pruebas**; incluye fixtures privados
que no se distribuyen. El ZIP se comprueba también tras extraerlo aparte.

## Steam: alcance de la comprobación

Con el cliente real de Steam abierto se comprobó `Bit Heroes.exe`, clase
`UnityWndClass`, título `Bit Heroes` y área 1920×1080 en (0,0). La imagen de
START se clasificó offline como START listo (similitud aproximada 0,962).
Se comprobó foco nativo desde el panel, selector oculto durante la vista compacta,
DETENER visible, restauración del selector y bloqueo de input al minimizar el juego.

Esas comprobaciones de beta.2 no enviaron clics de pesca. Después se reprodujo
un fallo real: capturas Steam de 26–40 ms impedían reunir las seis muestras
requeridas por el perfil histórico en 160 ms. Una primera corrección aún cancelaba
predicciones inestables y terminó sin CAST. No se ocultan esos fallos previos.

## Pruebas reales nuevas de beta.3 — 2 de octubre de 2026

Se hicieron tres sesiones nuevas supervisadas con límite de uno, uno y tres ciclos:

| Inicio | Ciclos cerrados | CATCH SUCCESS | Recompensa directa | CAST retenido / máximo |
| --- | ---: | ---: | ---: | --- |
| Menú Fishing / Play | 1 | 1 | 0 | 43/48 |
| Pantalla principal | 1 | 1 | 0 | 43/48 |
| START | 3 | 2 | 1 | 43/48, 42/48, 46/48 |

Total: **5 ciclos SUCCESS completos, 4 CATCH y 1 recompensa directa**, sin FAILED
en esas cinco pescas. Se comprobó Fishing → Play → espera → START, el inventario
una sola vez por sesión, un débito por CAST enviado y el cierre confirmado antes
de detenerse sin otro START. Tres CAST usaron la alternativa de máximo mostrado
y dos la predicción. Los valores retenidos demuestran que **no se garantiza el máximo**.

Cliente Steam, UnityWndClass, Bit Heroes, área 1920×1080 en (0,0), misma caña con
rango leído 20–48. No se modificaron archivos del juego, equipo ni rarezas y no
se entró en Shop/Events ni otros modos. Los registros y capturas de cuenta permanecen
privados; esta tabla es un resumen, no un dataset reproducible públicamente.

No se validaron sesiones largas, otras cañas ni toda la navegación en Chrome.
Steam permanece beta/experimental. Las 152 evidencias históricas de runs cubiertas
por la auditoría original conservaron sus hashes; la auditoría no se reescribió.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B scripts\comprobar.py
```

Las pruebas no deben iniciar motores en vivo. COMPROBAR no captura la pantalla
ni envía inputs. Un resultado correcto de estas comprobaciones no demuestra que
la disposición del juego coincida con las coordenadas del detector.

## Lo que no se garantiza

Siempre máximo, éxito universal de CATCH, autenticidad de una genealogía V6.2,
inventarios con scroll, cambio automático de rareza o ausencia de sanciones.
La causa de un CAST retenido 27 observado históricamente sigue sin demostrarse.
