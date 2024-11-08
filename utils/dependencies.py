import os
import sys
import shutil
import subprocess

def check_dependencies():
    dependencies_missing = []
    instructions = []

    try:
        import tkinter as tk
    except ImportError:
        dependencies_missing.append("Tkinter")
        instructions.append(
            "Para instalar Tkinter:\n"
            "  Ubuntu/Debian: sudo apt install python3-tk\n"
            "  Fedora: sudo dnf install python3-tkinter\n"
            "  Arch Linux: sudo pacman -S tk"
        )

    if not shutil.which("clamscan") and not shutil.which("clamdscan"):
        dependencies_missing.append("ClamAV")
        instructions.append(
            "Para instalar ClamAV:\n"
            "  Ubuntu/Debian: sudo apt install clamav clamav-daemon\n"
            "  Fedora: sudo dnf install clamav clamav-update\n"
            "  Arch Linux: sudo pacman -S clamav"
        )

    if dependencies_missing:
        missing_deps_message = f"Faltan las siguientes dependencias: {', '.join(dependencies_missing)}.\n\n" + "\n\n".join(instructions)
        print(missing_deps_message)
        
        try:
            subprocess.run(['notify-send', 'Dependencias Faltantes', missing_deps_message], check=True)
        except Exception as e:
            print(f"No se pudo mostrar la notificación: {e}")

        sys.exit(1)
