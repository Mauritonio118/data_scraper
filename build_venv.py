#!/usr/bin/env python3
"""
Script automatizado para crear entorno virtual y configurar el proyecto data_scraper.

Este script:
1. Crea un entorno virtual llamado 'envData'
2. Actualiza pip a la última versión
3. Instala el proyecto en modo editable (pip install -e .)
4. Instala navegadores de Playwright

Uso:
    python build_venv.py
"""

import os
import sys
import subprocess

VENV_NAME = "envData"

def run(cmd, description=""):
    """Ejecuta un comando y muestra descripción."""
    if description:
        print(f"\n→ {description}")
    subprocess.check_call(cmd)

def venv_python():
    """Retorna la ruta del ejecutable de Python del entorno virtual."""
    if os.name == "nt":  # Windows
        return os.path.join(VENV_NAME, "Scripts", "python.exe")
    else:                # Linux / macOS
        return os.path.join(VENV_NAME, "bin", "python")

def main():
    print("=" * 60)
    print("CONFIGURACIÓN AUTOMÁTICA DEL PROYECTO data_scraper")
    print("=" * 60)
    
    # 1. Crear entorno virtual
    if not os.path.isdir(VENV_NAME):
        run([sys.executable, "-m", "venv", VENV_NAME], 
            f"Creando entorno virtual '{VENV_NAME}'...")
    else:
        print(f"\n→ Entorno virtual '{VENV_NAME}' ya existe (saltando creación)")

    py = venv_python()

    # 2. Actualizar pip
    run([py, "-m", "pip", "install", "--upgrade", "pip"], 
        "Actualizando pip...")

    # 3. Instalar proyecto en modo editable
    run([py, "-m", "pip", "install", "-e", "."], 
        "Instalando proyecto en modo editable (pip install -e .)...")

    # 4. Instalar navegadores de Playwright
    run([py, "-m", "playwright", "install"], 
        "Instalando navegadores de Playwright...")

    # Mensaje final
    print("\n" + "=" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print("\nPara comenzar a trabajar:")
    print("  1. Activa el entorno virtual:")
    if os.name == "nt":
        print(f"     {VENV_NAME}\\Scripts\\activate")
    else:
        print(f"     source {VENV_NAME}/bin/activate")
    print("\n  2. Configura las variables de entorno:")
    print("     - Copia .env.example a .env")
    print("     - Completa las credenciales de MongoDB")
    print("\n  3. Ejecuta los workflows:")
    print("     python -m src.workflows.list_to_scrap_to_model_to_DB")
    print("\n  Para desactivar el entorno: deactivate")
    print("=" * 60)

if __name__ == "__main__":
    main()
