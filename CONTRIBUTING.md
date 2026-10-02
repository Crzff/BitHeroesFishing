# Contribuir

Gracias por ayudar a mejorar el proyecto. Abre un Issue antes de un cambio grande.
No envíes compras, cambios de equipo ni lógica de input CATCH desde CONTROL.

## Pruebas

Instala las dependencias y ejecuta:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

No ejecutes pruebas reales de pesca en CI ni contra cuentas ajenas. Documenta
qué verificaste y qué no. No afirmes precisión universal a partir de una tanda.

## Privacidad al reportar

- No adjuntes `runs/`, `.venv/`, cookies, contraseñas, tokens ni datos de pago.
- Los registros pueden contener rutas de usuario, cantidades y capturas.
- Comparte solo un fragmento mínimo anonimizado, con la versión y el evento relevante.
- Recorta las capturas al problema; oculta nombres de cuenta y otros datos personales.
- Una credencial publicada debe revocarse; eliminar el comentario no basta.

Mantén las guardas de frescura, intento único, presupuesto por sesión, cierre
confirmado y parada F8. Cambios de temporización necesitan evidencia, no ajustes a ciegas.
