# Validación y límites de la beta

Motor de referencia: **AUDIT-R3.15**. Extensión actual:
**AUDIT-R3.15+WINDOWS.1**, distribuida como **v0.1.0-beta.2**.
La extensión añade seguridad y selección de ventana; no es una nueva
certificación de pesca. La versión pública y el perfil histórico son diferentes.

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

Se conservan predictor, políticas, plantillas y demora CAST de **32 ms** de R3.15.
La beta.2 cambia el lanzador y la capa WindowsIO para vincular la ventana Steam
o Chrome y bloquear input al perder foco o geometría. No se presentan esos archivos
modificados como idénticos a los hashes de la auditoría histórica R3.15.
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

## Steam: alcance de la comprobación

Con el cliente real de Steam abierto se comprobó `Bit Heroes.exe`, clase
`UnityWndClass`, título `Bit Heroes` y área 1920×1080 en (0,0). La imagen de
START se clasificó offline como START listo (similitud aproximada 0,962).
Se comprobó foco nativo desde el panel, selector oculto durante la vista compacta,
DETENER visible, restauración del selector y bloqueo de input al minimizar el juego.

**No se iniciaron motores ni se enviaron clics de pesca.** No se validaron en
Steam inventario, CAST, CATCH ni cierre de una pesca completa. No se incluyen
capturas de la cuenta en el repositorio. Steam permanece experimental.

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
