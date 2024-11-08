# gui.py

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import threading
import multiprocessing
import os
import shutil
import logging
import time
from functools import partial
from scanner import get_files_to_scan, scan_file, chunker, update_virus_database
import subprocess

class ClamAVScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('ClamAV Scanner')
        self.directories = []
        self.exclude_dirs = ['/proc', '/sys', '/dev', '/run', '/tmp', '/var/lib', '/var/run']
        self.quarantine_dir = ''
        self.log_file = 'clamav_scan.log'
        self.batch_size = 500
        self.update_db = tk.BooleanVar()
        self.nucleos_libres = tk.IntVar(value=0)
        self.jobs = tk.IntVar(value=max(1, multiprocessing.cpu_count() - self.nucleos_libres.get()))
        self.infected_files = []
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        dirs_label = tk.Label(frame, text='Directorios a Escanear:')
        dirs_label.grid(row=0, column=0, sticky='w')

        self.dirs_listbox = tk.Listbox(frame, width=50, height=5)
        self.dirs_listbox.grid(row=1, column=0, columnspan=2, sticky='we')

        add_dir_button = tk.Button(frame, text='Agregar Directorio', command=self.add_directory)
        add_dir_button.grid(row=2, column=0, sticky='we')

        remove_dir_button = tk.Button(frame, text='Eliminar Seleccionado', command=self.remove_selected_directory)
        remove_dir_button.grid(row=2, column=1, sticky='we')

        options_frame = tk.LabelFrame(frame, text='Opciones')
        options_frame.grid(row=3, column=0, columnspan=2, sticky='we', pady=5)

        update_db_check = tk.Checkbutton(options_frame, text='Actualizar Base de Datos de Virus', variable=self.update_db)
        update_db_check.grid(row=0, column=0, sticky='w')

        quarantine_label = tk.Label(options_frame, text='Directorio de Cuarentena:')
        quarantine_label.grid(row=1, column=0, sticky='w')

        self.quarantine_entry = tk.Entry(options_frame, width=40)
        self.quarantine_entry.grid(row=1, column=1, sticky='we')

        browse_quarantine_button = tk.Button(options_frame, text='Examinar', command=self.browse_quarantine_dir)
        browse_quarantine_button.grid(row=1, column=2, sticky='we')

        nucleos_libres_label = tk.Label(options_frame, text='Núcleos a Dejar Libres:')
        nucleos_libres_label.grid(row=2, column=0, sticky='w')

        nucleos_libres_spinbox = tk.Spinbox(options_frame, from_=0, to=multiprocessing.cpu_count(), textvariable=self.nucleos_libres)
        nucleos_libres_spinbox.grid(row=2, column=1, sticky='we')

        batch_size_label = tk.Label(options_frame, text='Tamaño de Lote:')
        batch_size_label.grid(row=3, column=0, sticky='w')

        self.batch_size_entry = tk.Entry(options_frame)
        self.batch_size_entry.insert(0, '500')
        self.batch_size_entry.grid(row=3, column=1, sticky='we')

        log_file_label = tk.Label(options_frame, text='Archivo de Log:')
        log_file_label.grid(row=4, column=0, sticky='w')

        self.log_file_entry = tk.Entry(options_frame)
        self.log_file_entry.insert(0, 'clamav_scan.log')
        self.log_file_entry.grid(row=4, column=1, sticky='we')

        start_button = tk.Button(frame, text='Iniciar Escaneo', command=self.start_scan)
        start_button.grid(row=4, column=0, columnspan=2, sticky='we', pady=5)

        self.progress = Progressbar(frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=2, pady=5)

        self.status_label = tk.Label(frame, text='Estado: Listo')
        self.status_label.grid(row=6, column=0, columnspan=2, sticky='w')

    def add_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directories.append(directory)
            self.dirs_listbox.insert(tk.END, directory)

    def remove_selected_directory(self):
        selected_indices = self.dirs_listbox.curselection()
        for index in reversed(selected_indices):
            self.directories.pop(index)
            self.dirs_listbox.delete(index)

    def browse_quarantine_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.quarantine_entry.delete(0, tk.END)
            self.quarantine_entry.insert(0, directory)

    def start_scan(self):
        if not self.directories:
            messagebox.showwarning('Advertencia', 'Por favor, agrega al menos un directorio para escanear.')
            return

        self.quarantine_dir = self.quarantine_entry.get()
        self.log_file = self.log_file_entry.get()
        self.batch_size = int(self.batch_size_entry.get())
        self.jobs.set(max(1, multiprocessing.cpu_count() - self.nucleos_libres.get()))

        logging.basicConfig(filename=self.log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        if self.update_db.get():
            self.status_label.config(text='Estado: Actualizando base de datos de virus...')
            self.root.update()
            update_virus_database()

        if shutil.which('clamdscan'):
            self.scanner_cmd = 'clamdscan'
        elif shutil.which('clamscan'):
            self.scanner_cmd = 'clamscan'
        else:
            logging.error('No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')
            messagebox.showerror('Error', 'No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')
            return

        if self.quarantine_dir:
            self.quarantine_dir = os.path.abspath(self.quarantine_dir)
            os.makedirs(self.quarantine_dir, exist_ok=True)
        else:
            self.quarantine_dir = None

        self.status_label.config(text='Estado: Obteniendo archivos para escanear...')
        self.root.update()

        files_to_scan = []
        exclude_dirs = [os.path.abspath(d) for d in self.exclude_dirs]
        for directory in self.directories:
            directory = os.path.abspath(directory)
            if not os.path.exists(directory):
                logging.warning(f'Directorio no encontrado: {directory}')
                continue
            logging.info(f'Obteniendo archivos de {directory}')
            files = get_files_to_scan(directory, exclude_dirs)
            files_to_scan.extend(files)

        self.total_files = len(files_to_scan)
        if self.total_files == 0:
            logging.info('No se encontraron archivos para escanear.')
            messagebox.showinfo('Información', 'No se encontraron archivos para escanear.')
            return

        self.progress['maximum'] = self.total_files
        self.progress['value'] = 0
        self.status_label.config(text='Estado: Escaneando archivos...')
        self.root.update()

        self.manager = multiprocessing.Manager()
        self.infected_files = self.manager.list()

        scan_func = partial(scan_file, self.scanner_cmd, self.quarantine_dir, self.infected_files)

        self.pool = multiprocessing.Pool(processes=self.jobs.get())

        file_batches = list(chunker(files_to_scan, self.batch_size))

        self.start_time = time.time()

        self.scan_thread = threading.Thread(target=self.run_scan, args=(file_batches, scan_func))
        self.scan_thread.start()
        self.monitor_progress()

    def run_scan(self, file_batches, scan_func):
        try:
            for nfiles in self.pool.imap_unordered(scan_func, file_batches):
                self.progress.step(nfiles)
        except Exception as e:
            logging.error(f'Escaneo interrumpido: {e}')
        finally:
            self.pool.close()
            self.pool.join()

    def monitor_progress(self):
        if self.scan_thread.is_alive():
            self.root.after(100, self.monitor_progress)
        else:
            end_time = time.time()
            elapsed_time = end_time - self.start_time
            files_per_second = self.total_files / elapsed_time if elapsed_time > 0 else 0

            logging.info(f'Análisis completo. Total de archivos escaneados: {self.total_files}')
            logging.info(f'Tiempo total de escaneo: {elapsed_time:.2f} segundos')
            logging.info(f'Archivos por segundo: {files_per_second:.2f}')
            logging.info(f'Total de archivos infectados: {len(self.infected_files)}')

            result_message = f'Análisis completo.\nTotal de archivos escaneados: {self.total_files}\n' \
                             f'Tiempo total de escaneo: {elapsed_time:.2f} segundos\n' \
                             f'Archivos por segundo: {files_per_second:.2f}\n' \
                             f'Total de archivos infectados: {len(self.infected_files)}'

            if self.infected_files:
                result_message += '\nArchivos infectados:\n'
                for file_path, output in self.infected_files:
                    result_message += f'- {file_path}\n  {output}\n'

            messagebox.showinfo('Escaneo Completo', result_message)
            self.status_label.config(text='Estado: Escaneo completo.')

def main():
    root = tk.Tk()
    app = ClamAVScannerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()