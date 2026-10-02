# Cambios

## v0.1.0-beta.2

- Corrige la dependencia exclusiva del título de Chrome; selector Auto / Steam / Chrome.
- Steam experimental, identificado por ejecutable, clase Unity y título.
- Vincula ambos motores a la misma ventana; las consolas no la desactivan al abrir.
- Bloquea input y detiene ante pérdida de foco, minimización, cambio de pestaña o geometría.
- Mantiene CAST 32 ms, plantillas, políticas, presupuesto inicial único y cierre final.
- 139 pruebas públicas y panel/ventana Steam comprobados sin pesca real.
- La beta.1 y su ZIP quedan conservados; Steam aún no tiene una pesca completa validada.

## v0.1.0-beta.1

Primera distribución pública, basada en el motor AUDIT-R3.15.

- Panel oscuro, CAST retenido y contadores separados por resultado.
- Vista compacta y comprobación de zona segura y botón DETENER visible.
- Conteo inicial único, presupuesto por sesión y parada tras el último cierre.
- START/CAST/resultados y CATCH en procesos separados; F8 detiene ambos.
- Instalación local con `.venv`, lanzadores de doble clic y diagnóstico sin pesca.
- Guías en español, plantillas de Issues y licencia MIT para el código propio.
- Integración opcional con Ko-fi, fuera del flujo de pesca.

El paquete es código Python: **no incluye .exe ni Python portable**. No garantiza
CAST máximo, éxito universal ni compatibilidad con otras disposiciones del juego.
