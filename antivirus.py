#!/usr/bin/env python3

import os
import sys
import subprocess
import multiprocessing
from tqdm import tqdm
import argparse
import shutil
import logging
from functools import partial

nucleosLibres = 6

def get_files_to_scan(directory, exclude_dirs):
    files_to_scan = []
    for root, dirs, files in os.walk(directory, topdown=True):
        # Excluir directorios
        dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) not in exclude_dirs]
        for file in files:
            file_path = os.path.join(root, file)
            # Verificar permisos de lectura
            if os.access(file_path, os.R_OK):
                files_to_scan.append(file_path)
            else:
                logging.warning(f'Permiso denegado: {file_path}')
    return files_to_scan

def scan_file(quarantine_dir, result_list, file_path):
    try:
        cmd = ['clamscan', '--no-summary', '--stdout']
        if quarantine_dir:
            cmd.append(f'--move={quarantine_dir}')
        cmd.append(file_path)
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode == 1:
            # Virus encontrado
            result_list.append((file_path, result.stdout.strip()))
        elif result.returncode == 0:
            # Sin virus
            pass
        else:
            # Error en el escaneo
            logging.error(f'Error al escanear {file_path}: {result.stderr.strip()}')
    except Exception as e:
        logging.error(f'Excepción al escanear {file_path}: {e}')

def main():
    parser = argparse.ArgumentParser(description='Escanea directorios con ClamAV.')
    parser.add_argument('directories', nargs='+', help='Directorios a escanear')
    parser.add_argument('-j', '--jobs', type=int, default=max(1, multiprocessing.cpu_count() - nucleosLibres),
                        help='Número de trabajos en paralelo (por defecto: CPUs - 1)')
    parser.add_argument('--exclude-dirs', nargs='*', default=['/proc', '/sys', '/dev', '/run', '/tmp', '/var/lib', '/var/run'],
                        help='Directorios a excluir del escaneo')
    parser.add_argument('--quarantine-dir', help='Directorio para mover archivos infectados')
    parser.add_argument('--log-file', default='clamav_scan.log', help='Archivo de log (por defecto: clamav_scan.log)')
    args = parser.parse_args()

    # Configurar logging
    logging.basicConfig(filename=args.log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Verificar si clamscan está instalado
    if not shutil.which('clamscan'):
        logging.error('clamscan no encontrado. Por favor, instala ClamAV.')
        print('Error: clamscan no encontrado. Por favor, instala ClamAV.')
        sys.exit(1)

    # Crear directorio de cuarentena si se especifica
    if args.quarantine_dir:
        quarantine_dir = os.path.abspath(args.quarantine_dir)
        os.makedirs(quarantine_dir, exist_ok=True)
    else:
        quarantine_dir = None

    # Recopilar todos los archivos a escanear
    files_to_scan = []
    exclude_dirs = [os.path.abspath(d) for d in args.exclude_dirs]
    for directory in args.directories:
        directory = os.path.abspath(directory)
        if not os.path.exists(directory):
            logging.warning(f'Directorio no encontrado: {directory}')
            print(f'Advertencia: Directorio no encontrado: {directory}')
            continue
        logging.info(f'Obteniendo archivos de {directory}')
        files = get_files_to_scan(directory, exclude_dirs)
        files_to_scan.extend(files)

    total_files = len(files_to_scan)
    if total_files == 0:
        logging.info('No se encontraron archivos para escanear.')
        print('No se encontraron archivos para escanear.')
        sys.exit(0)

    print(f'Total de archivos a escanear: {total_files}')
    logging.info(f'Total de archivos a escanear: {total_files}')

    # Lista para almacenar archivos infectados
    manager = multiprocessing.Manager()
    infected_files = manager.list()

    # Preparar función parcial para el escaneo
    scan_func = partial(scan_file, quarantine_dir, infected_files)

    # Crear un pool de procesos
    pool = multiprocessing.Pool(processes=args.jobs)

    # Escanear archivos con barra de progreso
    try:
        with tqdm(total=total_files, desc='Escaneando archivos', unit='archivo') as pbar:
            for _ in pool.imap_unordered(scan_func, files_to_scan):
                pbar.update()
    except KeyboardInterrupt:
        print('\nEscaneo interrumpido por el usuario.')
        logging.warning('Escaneo interrumpido por el usuario.')
        pool.terminate()
        pool.join()
        sys.exit(1)
    finally:
        pool.close()
        pool.join()

    # Mostrar resultados
    print(f'\nAnálisis completo. Total de archivos escaneados: {total_files}')
    logging.info(f'Análisis completo. Total de archivos escaneados: {total_files}')
    print(f'Total de archivos infectados: {len(infected_files)}')
    logging.info(f'Total de archivos infectados: {len(infected_files)}')
    if infected_files:
        print('Archivos infectados:')
        for file_path, output in infected_files:
            print(f'- {file_path}')
            print(f'  {output}')
            logging.info(f'Archivo infectado: {file_path}')
            logging.info(f'Detalles: {output}')

if __name__ == '__main__':
    main()
