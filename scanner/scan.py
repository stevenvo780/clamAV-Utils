import os
import subprocess
import multiprocessing
import logging
import shutil
from multiprocessing import Pool, Manager

# Obtener lista de archivos a escanear
def get_files_to_scan(directories, exclude_dirs):
    exclude_dirs = [os.path.abspath(d) for d in exclude_dirs]
    files_to_scan = []
    visited_dirs = set()
    for directory in directories:
        for root, dirs, files in os.walk(directory, topdown=True, followlinks=False):
            root_realpath = os.path.realpath(root)
            if root_realpath in visited_dirs:
                continue
            visited_dirs.add(root_realpath)
            dirs[:] = [
                d for d in dirs
                if os.path.abspath(os.path.join(root, d)) not in exclude_dirs
                and not os.path.islink(os.path.join(root, d))
            ]
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.islink(file_path):
                    continue
                if os.access(file_path, os.R_OK):
                    files_to_scan.append(file_path)
                else:
                    logging.warning(f"Permiso denegado: {file_path}")
    return files_to_scan

# Escanear archivo o batch de archivos
def scan_file(args):
    scanner_cmd, quarantine_dir, file_batch, logging_enabled, delete_infected = args
    infected_files = []
    try:
        cmd = [scanner_cmd, '--no-summary', '--quiet', '--stdout']
        if not logging_enabled:
            cmd.append('--log=/dev/null')
        if delete_infected:
            cmd.append('--remove')
        elif quarantine_dir:
            cmd.append(f'--move={quarantine_dir}')
        cmd.extend(file_batch)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Procesa salida solo cuando hay archivos infectados o errores críticos
        if result.returncode == 1:
            for line in result.stdout.strip().split('\n'):
                if ': ' in line:
                    file_path, message = line.split(': ', 1)
                    if 'OK' not in message:
                        infected_files.append((file_path, message))
                        if logging_enabled and 'Permission denied' not in message:
                            logging.info(f'Archivo infectado: {file_path} - {message}')
        elif result.returncode != 0:
            error_message = result.stderr.strip()
            if error_message and 'Permission denied' not in error_message and 'File path check failure' not in error_message:
                # Filtra errores para registrar solo errores críticos con detalles
                if logging_enabled:
                    logging.error(f'Error al escanear archivos: {error_message}')
    except Exception as e:
        if logging_enabled:
            logging.error(f'Excepción al escanear archivos: {e}')
    return len(file_batch), infected_files

# Dividir archivos en lotes
def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

# Actualizar la base de datos de virus
def update_virus_database():
    try:
        subprocess.run(['freshclam', '--quiet'], check=True)
    except subprocess.CalledProcessError:
        print('Error al actualizar la base de datos de virus. Continuando con el escaneo.')

# Obtener comando de escaneo
def get_scanner_command():
    if shutil.which('clamdscan'):
        return 'clamdscan'
    elif shutil.which('clamscan'):
        return 'clamscan'
    else:
        return None

# Ejecutar escaneo en los archivos
def perform_scan(files_to_scan, quarantine_dir, batch_size, jobs, logging_enabled, delete_infected, progress_callback=None, stop_flag=None):
    scanner_cmd = get_scanner_command()
    if not scanner_cmd:
        raise FileNotFoundError('No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')

    manager = multiprocessing.Manager()
    infected_files_list = manager.list()

    pool = multiprocessing.Pool(processes=jobs)
    file_batches = list(chunker(files_to_scan, batch_size))

    scan_args = [
        (scanner_cmd, quarantine_dir, batch, logging_enabled, delete_infected)
        for batch in file_batches
    ]

    processed_files = 0
    try:
        for nfiles, infected_files in pool.imap_unordered(scan_file, scan_args):
            if stop_flag and stop_flag():
                break
            processed_files += nfiles
            infected_files_list.extend(infected_files)
            if progress_callback:
                progress_callback(nfiles)
    finally:
        pool.close()
        pool.join()

    return len(files_to_scan), processed_files, list(infected_files_list)
