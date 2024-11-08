import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import threading
import multiprocessing
import os
import logging
import time
from scanner import perform_scan, update_virus_database, get_scanner_command, get_files_to_scan

class ClamAVScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('ClamAV Scanner')
        self.directories = []
        self.exclude_dirs = ['/proc', '/sys', '/dev', '/run', '/tmp', '/var/lib', '/var/run']
        self.quarantine_dir = os.path.abspath('quarantine')
        self.log_file = 'clamav_scan.log'
        self.batch_size = 500
        self.update_db = True
        self.logging_enabled = tk.BooleanVar()
        self.nucleos_libres = tk.IntVar(value=0)
        self.jobs = tk.IntVar(value=max(1, multiprocessing.cpu_count() - self.nucleos_libres.get()))
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

        quarantine_label = tk.Label(options_frame, text='Directorio de Cuarentena:')
        quarantine_label.grid(row=0, column=0, sticky='w')

        self.quarantine_entry = tk.Entry(options_frame, width=40)
        self.quarantine_entry.insert(0, self.quarantine_dir)
        self.quarantine_entry.grid(row=0, column=1, sticky='we')

        browse_quarantine_button = tk.Button(options_frame, text='Examinar', command=self.browse_quarantine_dir)
        browse_quarantine_button.grid(row=0, column=2, sticky='we')

        enable_logging_check = tk.Checkbutton(options_frame, text='Habilitar Logs', variable=self.logging_enabled)
        enable_logging_check.grid(row=1, column=0, sticky='w')

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
        start_button.grid(row=5, column=0, columnspan=2, sticky='we', pady=5)

        self.progress = Progressbar(frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=2, pady=5)

        self.status_label = tk.Label(frame, text='Estado: Listo')
        self.status_label.grid(row=7, column=0, columnspan=2, sticky='w')

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

        if self.logging_enabled.get():
            logging.basicConfig(filename=self.log_file, level=logging.INFO,
                                format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            logging.disable(logging.CRITICAL)

        if self.update_db:
            self.status_label.config(text='Estado: Actualizando base de datos de virus...')
            self.root.update()
            update_virus_database()

        scanner_cmd = get_scanner_command()
        if not scanner_cmd:
            messagebox.showerror('Error', 'No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')
            return

        if self.quarantine_dir:
            self.quarantine_dir = os.path.abspath(self.quarantine_dir)
            os.makedirs(self.quarantine_dir, exist_ok=True)

        self.status_label.config(text='Estado: Obteniendo archivos para escanear...')
        self.root.update()

        # Obtener archivos para escanear y total de archivos
        files_to_scan = get_files_to_scan(self.directories, self.exclude_dirs)
        self.total_files = len(files_to_scan)
        if self.total_files == 0:
            messagebox.showinfo('Información', 'No se encontraron archivos para escanear.')
            return

        self.progress['maximum'] = self.total_files
        self.progress['value'] = 0

        # Inicia el hilo de escaneo y monitoriza el progreso
        self.scan_thread = threading.Thread(target=self.run_scan, args=(files_to_scan,))
        self.scan_thread.start()
        self.monitor_progress()

    def run_scan(self, files_to_scan):
        start_time = time.time()
        try:
            total_files, processed_files, infected_files = perform_scan(
                files_to_scan=files_to_scan,
                quarantine_dir=self.quarantine_dir,
                batch_size=self.batch_size,
                jobs=self.jobs.get(),
                logging_enabled=self.logging_enabled.get(),
                progress_callback=self.update_progress
            )
            self.total_files = total_files
            self.infected_files = infected_files
        except Exception as e:
            self.root.after(0, self.show_error_message, f'Error durante el escaneo: {e}')
            self.root.after(0, self.update_status_label, 'Estado: Error durante el escaneo.')
            return
        finally:
            end_time = time.time()
            self.elapsed_time = end_time - start_time

    def update_progress(self, nfiles):
        self.root.after(0, self._update_progress, nfiles)

    def _update_progress(self, nfiles):
        self.progress['value'] += nfiles
        self.progress.update_idletasks()

    def monitor_progress(self):
        if self.scan_thread.is_alive():
            self.root.after(100, self.monitor_progress)
        else:
            self.display_results()

    def display_results(self):
        files_per_second = self.total_files / self.elapsed_time if self.elapsed_time > 0 else 0

        result_message = f'Análisis completo.\nTotal de archivos escaneados: {self.total_files}\n' \
                         f'Tiempo total de escaneo: {self.elapsed_time:.2f} segundos\n' \
                         f'Archivos por segundo: {files_per_second:.2f}\n' \
                         f'Total de archivos infectados: {len(self.infected_files)}'

        if self.infected_files:
            result_message += '\nArchivos infectados:\n'
            for file_path, output in self.infected_files:
                result_message += f'- {file_path}\n  {output}\n'

        messagebox.showinfo('Escaneo Completo', result_message)
        self.status_label.config(text='Estado: Escaneo completo.')

    def show_error_message(self, message):
        messagebox.showerror('Error', message)

    def update_status_label(self, message):
        self.status_label.config(text=message)

def main():
    root = tk.Tk()
    app = ClamAVScannerApp(root)
    root.mainloop()
