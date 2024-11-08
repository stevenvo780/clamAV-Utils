# clamav_scanner/gui/scanner_app.py

import os
import tkinter as tk
from gui.widgets import create_main_frame, create_widgets
from gui.event_handlers import on_close_handler

class ClamAVScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('ClamAV Scanner')
        self.directories = []
        self.exclude_dirs = ['/proc', '/sys', '/dev', '/run', '/tmp', '/var/lib', '/var/run']

        user_home = os.path.expanduser(f"~{os.getenv('SUDO_USER')}" if os.getenv("SUDO_USER") else "~")
        user_dir = os.path.join(user_home, "clamav_scanner")
        os.makedirs(user_dir, exist_ok=True)

        self.quarantine_dir = os.path.join(user_dir, 'quarantine')
        os.makedirs(self.quarantine_dir, exist_ok=True)

        self.log_file = os.path.join(user_dir, 'clamav_scan.log')
        self.batch_size = 500
        self.update_db = True
        self.logging_enabled = tk.BooleanVar(value=True)
        self.nucleos_libres = tk.IntVar(value=0)
        self.jobs = tk.IntVar()
        self.total_files = 0
        self.elapsed_time = 0
        self.infected_files = []
        self.stop_requested = False
        self.scan_thread = None
        self.pool = None
        self.delete_infected = tk.BooleanVar(value=False)

        self.frame = create_main_frame(self.root)
        create_widgets(self)

        self.update_jobs()
        self.root.protocol("WM_DELETE_WINDOW", lambda: on_close_handler(self))

    def update_jobs(self):
        total_cpus = os.cpu_count()
        nucleos_libres = self.nucleos_libres.get()
        self.jobs.set(max(1, total_cpus - nucleos_libres))
