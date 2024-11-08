import os
import subprocess
import multiprocessing
import logging
import shutil

def get_files_to_scan(directories, exclude_dirs):
    exclude_dirs = [os.path.abspath(d) for d in exclude_dirs]
    files_to_scan = []
    for directory in directories:
        for root, dirs, files in os.walk(directory, topdown=True):
            dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) not in exclude_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                if os.access(file_path, os.R_OK):
                    files_to_scan.append(file_path)
                else:
                    logging.warning(f'Permiso denegado: {file_path}')
    return files_to_scan

def scan_file(args):
    scanner_cmd, quarantine_dir, result_list, file_batch, logging_enabled = args
    try:
        cmd = [scanner_cmd, '--no-summary', '--stdout']
        if quarantine_dir:
            cmd.append(f'--move={quarantine_dir}')
        if not logging_enabled:
            cmd.append('--log=/dev/null')
        cmd.extend(file_batch)
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode == 1:
            for line in result.stdout.strip().split('\n'):
                if ': ' in line:
                    file_path, message = line.split(': ', 1)
                    if 'OK' not in message:
                        result_list.append((file_path, message))
        elif result.returncode != 0 and logging_enabled:
            logging.error(f'Error al escanear archivos: {result.stderr.strip()}')
    except Exception as e:
        if logging_enabled:
            logging.error(f'Excepción al escanear archivos: {e}')
    return len(file_batch)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def update_virus_database():
    try:
        subprocess.run(['freshclam', '--quiet'], check=True)
    except subprocess.CalledProcessError:
        print('Error al actualizar la base de datos de virus. Continuando con el escaneo.')

def get_scanner_command():
    if shutil.which('clamdscan'):
        return 'clamdscan'
    elif shutil.which('clamscan'):
        return 'clamscan'
    else:
        return None

def perform_scan(files_to_scan, quarantine_dir, batch_size, jobs, logging_enabled, progress_callback=None):
    scanner_cmd = get_scanner_command()
    if not scanner_cmd:
        raise FileNotFoundError('No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')

    if quarantine_dir:
        quarantine_dir = os.path.abspath(quarantine_dir)
        os.makedirs(quarantine_dir, exist_ok=True)

    if logging_enabled:
        logging.info('Iniciando escaneo de archivos...')
    total_files = len(files_to_scan)
    if total_files == 0:
        return 0, [], []

    manager = multiprocessing.Manager()
    infected_files = manager.list()

    pool = multiprocessing.Pool(processes=jobs)
    file_batches = list(chunker(files_to_scan, batch_size))

    scan_args = [(scanner_cmd, quarantine_dir, infected_files, batch, logging_enabled) for batch in file_batches]

    processed_files = 0
    try:
        for nfiles in pool.imap_unordered(scan_file, scan_args):
            processed_files += nfiles
            if progress_callback:
                progress_callback(nfiles)  # Actualiza el progreso
    finally:
        pool.close()
        pool.join()

    return total_files, processed_files, list(infected_files)
