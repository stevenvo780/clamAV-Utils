import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Listbox, Scrollbar
import multiprocessing
import logging
import time
from scanner.scan import perform_scan, update_virus_database, get_scanner_command, get_files_to_scan

def add_directory_handler(app):
    directory = filedialog.askdirectory()
    if directory:
        app.directories.append(directory)
        app.dirs_listbox.insert(tk.END, directory)

def remove_selected_directory_handler(app):
    selected_indices = app.dirs_listbox.curselection()
    for index in reversed(selected_indices):
        app.directories.pop(index)
        app.dirs_listbox.delete(index)

def browse_quarantine_dir_handler(app):
    directory = filedialog.askdirectory()
    if directory:
        app.quarantine_entry.delete(0, tk.END)
        app.quarantine_entry.insert(0, directory)

def start_scan_handler(app):
    if not app.directories:
        messagebox.showwarning('Advertencia', 'Por favor, agrega al menos un directorio para escanear.')
        return

    app.quarantine_dir = app.quarantine_entry.get()
    app.log_file = app.log_file_entry.get()
    try:
        app.batch_size = int(app.batch_size_entry.get())
    except ValueError:
        messagebox.showerror('Error', 'El tamaño de lote debe ser un número entero.')
        return

    app.update_jobs()
    app.stop_requested = False

    if app.logging_enabled.get():
        logging.basicConfig(
            filename=app.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    else:
        logging.disable(logging.CRITICAL)

    if app.update_db:
        app.status_label.config(text='Estado: Actualizando base de datos de virus...')
        app.root.update()
        update_virus_database()

    scanner_cmd = get_scanner_command()
    if not scanner_cmd:
        messagebox.showerror('Error', 'No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')
        return

    if not os.path.exists(app.quarantine_dir) and not app.delete_infected.get():
        os.makedirs(app.quarantine_dir)

    app.status_label.config(text='Estado: Obteniendo archivos para escanear...')
    app.root.update()

    files_to_scan = get_files_to_scan(app.directories, app.exclude_dirs)
    app.total_files = len(files_to_scan)
    if app.total_files == 0:
        messagebox.showinfo('Información', 'No se encontraron archivos para escanear.')
        return

    app.progress['maximum'] = app.total_files
    app.progress['value'] = 0

    app.scan_thread = threading.Thread(target=run_scan, args=(app, files_to_scan), daemon=True)
    app.scan_thread.start()
    monitor_progress(app)

def run_scan(app, files_to_scan):
    start_time = time.time()
    try:
        app.pool = multiprocessing.Pool(processes=app.jobs.get())
        total_files, processed_files, infected_files = perform_scan(
            files_to_scan=files_to_scan,
            quarantine_dir=app.quarantine_dir if not app.delete_infected.get() else None,
            batch_size=app.batch_size,
            jobs=app.jobs.get(),
            logging_enabled=app.logging_enabled.get(),
            delete_infected=app.delete_infected.get(),
            progress_callback=lambda nfiles: update_progress(app, nfiles),
            stop_flag=lambda: app.stop_requested
        )
        app.total_files = total_files
        app.infected_files = infected_files
    except Exception as e:
        app.root.after(0, show_error_message, app, f'Error durante el escaneo: {e}')
        app.root.after(0, update_status_label, app, 'Estado: Error durante el escaneo.')
    finally:
        if app.pool:
            app.pool.terminate()
            app.pool.join()
            app.pool = None
        end_time = time.time()
        app.elapsed_time = end_time - start_time

def stop_scan_handler(app):
    app.stop_requested = True
    if app.pool:
        app.pool.terminate()
        app.pool.join()
        app.pool = None
    app.status_label.config(text="Estado: Escaneo detenido por el usuario.")
    app.progress.stop()

def update_progress(app, nfiles):
    app.root.after(0, _update_progress, app, nfiles)

def _update_progress(app, nfiles):
    app.progress['value'] += nfiles
    app.progress.update_idletasks()
    estimated_time = (app.elapsed_time / app.progress['value']) * (app.total_files - app.progress['value']) if app.progress['value'] > 0 else 0
    app.status_label.config(text=f'Estado: Escaneando... Tiempo estimado restante: {estimated_time:.2f} segundos')

def monitor_progress(app):
    if app.scan_thread and app.scan_thread.is_alive():
        app.root.after(100, lambda: monitor_progress(app))
    else:
        if not app.stop_requested:
            display_results(app)

def display_results(app):
    files_per_second = app.total_files / app.elapsed_time if app.elapsed_time > 0 else 0
    result_message = f'Análisis completo.\nTotal de archivos escaneados: {app.total_files}\n' \
                     f'Tiempo total de escaneo: {app.elapsed_time:.2f} segundos\n' \
                     f'Archivos por segundo: {files_per_second:.2f}\n' \
                     f'Total de archivos infectados: {len(app.infected_files)}'

    messagebox.showinfo('Escaneo Completo', result_message)
    app.status_label.config(text='Estado: Escaneo completo.')

def on_close_handler(app):
    app.stop_requested = True
    if app.pool:
        app.pool.terminate()
        app.pool.join()
        app.pool = None
    if app.scan_thread and app.scan_thread.is_alive():
        app.scan_thread.join()
    app.root.quit()
    app.root.destroy()

def show_error_message(app, message):
    messagebox.showerror('Error', message)

def update_status_label(app, message):
    app.status_label.config(text=message)

def show_infected_files_handler(app):
    if not app.infected_files:
        messagebox.showinfo('Sin archivos infectados', 'No se encontraron archivos infectados.')
        return

    window = Toplevel(app.root)
    window.title("Archivos Infectados")
    listbox = Listbox(window, width=60, height=20)
    scrollbar = Scrollbar(window)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    for file_path, output in app.infected_files:
        listbox.insert(tk.END, f'{file_path}: {output}')

def show_quarantine_handler(app):
    window = Toplevel(app.root)
    window.title("Cuarentena")
    listbox = Listbox(window, width=60, height=20)
    scrollbar = Scrollbar(window)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    for filename in os.listdir(app.quarantine_dir):
        listbox.insert(tk.END, filename)

    def restore_file():
        selected = listbox.curselection()
        if not selected:
            messagebox.showwarning('Advertencia', 'Selecciona un archivo para restaurar.')
            return
        filename = listbox.get(selected[0])
        file_to_restore = os.path.join(app.quarantine_dir, filename)
        destination_dir = os.path.expanduser("~")
        destination_path = os.path.join(destination_dir, filename)

        if os.path.exists(destination_path):
            overwrite = messagebox.askyesno('Confirmación', f'El archivo {filename} ya existe en {destination_dir}. ¿Deseas sobrescribirlo?')
            if not overwrite:
                return
            else:
                try:
                    os.remove(destination_path)
                except Exception as e:
                    messagebox.showerror('Error', f'No se pudo eliminar el archivo existente: {e}')
                    return
        try:
            os.rename(file_to_restore, destination_path)
            os.chmod(destination_path, 0o644)
            listbox.delete(selected)
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo restaurar el archivo: {e}')

    restore_button = tk.Button(window, text="Restaurar Archivo", command=restore_file)
    restore_button.pack(fill=tk.X)
