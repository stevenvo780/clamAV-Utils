import os
import sys
import logging
from gui import ClamAVScannerApp

def check_and_elevate():
    if os.geteuid() != 0:
        print("Este programa necesita permisos de administrador.")
        try:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        except Exception as e:
            print(f"Error al intentar elevar permisos: {e}")
            sys.exit(1)

def main():
    check_and_elevate()
    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter no está instalado. Por favor, instálalo e inténtalo de nuevo.")
        sys.exit(1)

    root = tk.Tk()
    app = ClamAVScannerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
