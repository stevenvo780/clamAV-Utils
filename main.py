import os
import sys
from gui import main

def check_and_elevate():
    if os.geteuid() != 0:
        print("Este programa necesita permisos de administrador.")
        try:
            os.execvp("sudo", ["sudo", "python3"] + sys.argv)
        except Exception as e:
            print(f"Error al intentar elevar permisos: {e}")
            sys.exit(1)

if __name__ == '__main__':
    check_and_elevate()
    main()
