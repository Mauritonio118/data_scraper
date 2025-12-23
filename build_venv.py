#!/usr/bin/env python3

import os
import sys
import subprocess

VENV_NAME = ".venv"

def run(cmd):
    subprocess.check_call(cmd)

def venv_python():
    if os.name == "nt":  # Windows
        return os.path.join(VENV_NAME, "Scripts", "python.exe")
    else:                # Linux / macOS
        return os.path.join(VENV_NAME, "bin", "python")

def main():
    if not os.path.isdir(VENV_NAME):
        print("Creating virtual environment...")
        run([sys.executable, "-m", "venv", VENV_NAME])

    py = venv_python()

    print("Upgrading pip...")
    run([py, "-m", "pip", "install", "--upgrade", "pip"])

    if os.path.exists("requirements.txt"):
        print("Installing dependencies...")
        run([py, "-m", "pip", "install", "-r", "requirements.txt"])

    print("Installing Playwright browsers...")
    run([py, "-m", "playwright", "install"])

    print("\nSETUP COMPLETE")
    if os.name == "nt":
        print(f"Activate with: {VENV_NAME}\\Scripts\\activate")
    else:
        print(f"Activate with: source {VENV_NAME}/bin/activate")
    print("Deactivate with: deactivate")

if __name__ == "__main__":
    main()
