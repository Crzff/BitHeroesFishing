# Validación y límites de la beta

Motor de referencia: **AUDIT-R3.15**. Primera distribución pública:
**v0.1.0-beta.1**. La versión pública y el perfil de auditoría son identificadores
diferentes.

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

La distribución no cambia el predictor, las políticas, los inputs ni los tiempos
de los motores R3.15. Las adiciones públicas son instalación, documentación y
enlaces de apoyo. El enlace de apoyo no inicia pesca ni procesa pagos dentro del bot.

La configuración de CI se ofrece en `docs/ci-windows.example.yml` como ejemplo
opcional, no como un workflow activo. Publicar esta beta no requiere ampliar el
permiso OAuth de GitHub a `workflow`. Las 123 pruebas indicadas se ejecutaron
localmente; no se presentan como una ejecución de GitHub Actions.

## Comprobaciones públicas

La copia limpia pasó **123 pruebas públicas** en un entorno virtual nuevo.
Se comprobó el panel real sin iniciar motores: el botón de apoyo aparece al
estar detenido y queda oculto en la vista compacta; DETENER sigue visible.

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
