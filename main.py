import os
import sys
import subprocess
from utils.dependencies import check_dependencies
from gui.scanner_app import ClamAVScannerApp

def check_and_elevate():
    if os.geteuid() != 0:
        if os.environ.get("ELEVATED") != "1":
            print("Este programa necesita permisos de administrador.")
            try:
                env = os.environ.copy()
                env["ELEVATED"] = "1"
                result = subprocess.run(["sudo", "-E", sys.executable] + sys.argv, env=env)
                if result.returncode != 0:
                    print("Error al intentar elevar permisos.")
                    sys.exit(1)
                sys.exit(0)
            except Exception as e:
                print(f"Error al intentar elevar permisos: {e}")
                sys.exit(1)
        else:
            print("No se pudieron obtener permisos de administrador.")
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
