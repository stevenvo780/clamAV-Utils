# clamav_scanner/gui/widgets.py

import tkinter as tk
from tkinter.ttk import Progressbar
import multiprocessing
from gui.event_handlers import (
    add_directory_handler,
    remove_selected_directory_handler,
    browse_quarantine_dir_handler,
    start_scan_handler,
    stop_scan_handler
)

def create_main_frame(root):
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)
    return frame

def create_widgets(app):
    frame = app.frame

    dirs_label = tk.Label(frame, text='Directorios a Escanear:')
    dirs_label.grid(row=0, column=0, sticky='w')

    app.dirs_listbox = tk.Listbox(frame, width=50, height=5)
    app.dirs_listbox.grid(row=1, column=0, columnspan=2, sticky='we')

    add_dir_button = tk.Button(frame, text='Agregar Directorio', command=lambda: add_directory_handler(app))
    add_dir_button.grid(row=2, column=0, sticky='we')

    remove_dir_button = tk.Button(frame, text='Eliminar Seleccionado', command=lambda: remove_selected_directory_handler(app))
    remove_dir_button.grid(row=2, column=1, sticky='we')

    options_frame = tk.LabelFrame(frame, text='Opciones')
    options_frame.grid(row=3, column=0, columnspan=2, sticky='we', pady=5)

    quarantine_label = tk.Label(options_frame, text='Directorio de Cuarentena:')
    quarantine_label.grid(row=0, column=0, sticky='w')

    app.quarantine_entry = tk.Entry(options_frame, width=40)
    app.quarantine_entry.insert(0, app.quarantine_dir)
    app.quarantine_entry.grid(row=0, column=1, sticky='we')

    browse_quarantine_button = tk.Button(options_frame, text='Examinar', command=lambda: browse_quarantine_dir_handler(app))
    browse_quarantine_button.grid(row=0, column=2, sticky='we')

    enable_logging_check = tk.Checkbutton(options_frame, text='Habilitar Logs', variable=app.logging_enabled)
    enable_logging_check.grid(row=1, column=0, sticky='w')

    delete_infected_check = tk.Checkbutton(options_frame, text='Borrar archivos infectados', variable=app.delete_infected)
    delete_infected_check.grid(row=1, column=1, sticky='w')

    nucleos_libres_label = tk.Label(options_frame, text='Núcleos a Dejar Libres:')
    nucleos_libres_label.grid(row=2, column=0, sticky='w')

    nucleos_libres_spinbox = tk.Spinbox(
        options_frame,
        from_=0,
        to=multiprocessing.cpu_count() - 1,
        textvariable=app.nucleos_libres,
        command=app.update_jobs
    )
    nucleos_libres_spinbox.grid(row=2, column=1, sticky='we')

    batch_size_label = tk.Label(options_frame, text='Tamaño de Lote:')
    batch_size_label.grid(row=3, column=0, sticky='w')

    app.batch_size_entry = tk.Entry(options_frame)
    app.batch_size_entry.insert(0, '500')
    app.batch_size_entry.grid(row=3, column=1, sticky='we')

    log_file_label = tk.Label(options_frame, text='Archivo de Log:')
    log_file_label.grid(row=4, column=0, sticky='w')

    app.log_file_entry = tk.Entry(options_frame)
    app.log_file_entry.insert(0, app.log_file)
    app.log_file_entry.grid(row=4, column=1, sticky='we')

    start_button = tk.Button(frame, text='Iniciar Escaneo', command=lambda: start_scan_handler(app))
    start_button.grid(row=5, column=0, sticky='we', pady=5)

    stop_button = tk.Button(frame, text='Detener Escaneo', command=lambda: stop_scan_handler(app))
    stop_button.grid(row=5, column=1, sticky='we', pady=5)

    app.progress = Progressbar(frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
    app.progress.grid(row=6, column=0, columnspan=2, pady=5)

    app.status_label = tk.Label(frame, text='Estado: Listo')
    app.status_label.grid(row=7, column=0, columnspan=2, sticky='w')
