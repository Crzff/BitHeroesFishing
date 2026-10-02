"""CONTROL del perfil vigente: interfaz y resultados; nunca decide/pulsa CATCH.

La version previa completa esta en el backup 00_baseline. Importar este
modulo no captura pantalla ni ejecuta bucles. F8 detiene ambos motores.
"""

from fishing_core.runtime import run_control


if __name__ == "__main__":
    raise SystemExit(run_control())
