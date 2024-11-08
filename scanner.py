# scanner.py

import os
import subprocess
import multiprocessing
from tqdm import tqdm
import logging
import shutil

def get_files_to_scan(directory, exclude_dirs):
    files_to_scan = []
    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) not in exclude_dirs]
        for file in files:
            file_path = os.path.join(root, file)
            if os.access(file_path, os.R_OK):
                files_to_scan.append(file_path)
            else:
                logging.warning(f'Permiso denegado: {file_path}')
    return files_to_scan

def scan_file(scanner_cmd, quarantine_dir, result_list, file_batch):
    try:
        cmd = [scanner_cmd, '--no-summary', '--stdout', '--log=/dev/null']
        if quarantine_dir:
            cmd.append(f'--move={quarantine_dir}')
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
        elif result.returncode != 0:
            logging.error(f'Error al escanear archivos {file_batch}: {result.stderr.strip()}')
    except Exception as e:
        logging.error(f'Excepción al escanear archivos {file_batch}: {e}')
    return len(file_batch)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def update_virus_database():
    try:
        subprocess.run(['freshclam'], check=True)
        logging.info('Base de datos de virus actualizada correctamente.')
    except subprocess.CalledProcessError as e:
        logging.error(f'Error al actualizar la base de datos de virus: {e}')
        print('Error al actualizar la base de datos de virus. Continuando con el escaneo.')
