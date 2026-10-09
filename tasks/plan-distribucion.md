# Plan: Farm Bot para otros jugadores (Linux → Windows .exe)

Pedido por crzf (2026-10-09). Orden acordado: primero que funcione para otros en Linux
con un backend que también sirva en Windows; después seguridad; al final instalador `.exe`.

## Fase 1 — Base multiplataforma

1. ✅ (2026-10-09: ciclo completo de KORTZZ en vivo con FARM_BACKEND=cdp) **Backend CDP para cuentas de navegador** (`FARM_BACKEND=cdp`): imagen con
   `Page.captureScreenshot` e input con `Input.dispatchMouseEvent` del propio navegador,
   sin gamescope, XTest ni mover el ratón del usuario. Misma interfaz que GamescopeIO/
   GamescopeCapture y mismas guardas (identidad, geometría 1920×1080, foco del canvas, F8).
   Sirve igual en Linux y Windows. Navegadores Chromium: Chrome, Chromium, Brave, Edge.
2. ✅ código (sin validar en Windows; en Linux/niri se mantiene gamescope como anfitrión) **Lanzador de clientes de navegador sin gamescope**: perfil propio por cuenta,
   ventana 1920×1080 sin bloqueo de render en segundo plano, puerto CDP local; escribe la
   sesión sola (sin `sessions.json` a mano).
3. **Cuentas configurables en la app**: lista de cuentas (nombre, tipo Steam/navegador,
   navegador), «+ Añadir cuenta», pestañas y FARMEAR generadas desde la lista.
4. **Primer inicio de sesión guiado**: ventana visible una vez para que el jugador entre
   en su cuenta; el bot nunca lee ni guarda contraseñas o cookies.
5. **Valores por defecto prudentes** para cuentas nuevas: sin objetivos, oro 0, máxima
   dificultad disponible.

## Fase 2 — Seguridad

- Revisión de guardas (nunca gemas; compras solo boosts Minor con oro; F8; paradas ante
  pantallas desconocidas), aislamiento de perfiles, CDP solo en 127.0.0.1, sin secretos
  en registros, actualizaciones firmadas. Auditoría con `security-and-hardening`.

## Fase 3 — Windows

- Steam en Windows: una cuenta, ventana en primer plano (modo Windows original).
- Instalador `.exe` (PyInstaller + Inno Setup o similar), Node incluido para el adaptador
  CDP, accesos directos y desinstalador.

## Aviso

Usar bots puede ir contra las condiciones de Bit Heroes: avisar a cada jugador.
