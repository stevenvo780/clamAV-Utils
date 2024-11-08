import os
import sys
from utils.dependencies import check_dependencies
from gui.scanner_app import ClamAVScannerApp

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
