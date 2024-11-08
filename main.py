import os
import sys
import shutil
from gui import ClamAVScannerApp

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
            os.system(f'notify-send "Dependencias Faltantes" "{missing_deps_message}"')
        except Exception as e:
            print(f"No se pudo mostrar la notificación: {e}")

        sys.exit(1)

def check_and_elevate():
    if os.geteuid() != 0:
        print("Este programa necesita permisos de administrador.")
        try:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        except Exception as e:
            print(f"Error al intentar elevar permisos: {e}")
            sys.exit(1)

def main():
    check_dependencies()
    check_and_elevate()

    import tkinter as tk
    root = tk.Tk()
    app = ClamAVScannerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
