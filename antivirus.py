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

nucleosLibres = 1

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

def scan_file(scanner_cmd, quarantine_dir, result_list, file_batch):
    try:
        cmd = [scanner_cmd, '--no-summary', '--stdout']
        if quarantine_dir:
            cmd.append(f'--move={quarantine_dir}')
        cmd.extend(file_batch)
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode == 1:
            # Virus encontrado
            # Parsear la salida para encontrar archivos infectados
            for line in result.stdout.strip().split('\n'):
                if ': ' in line:
                    file_path, message = line.split(': ', 1)
                    if 'OK' not in message:
                        result_list.append((file_path, message))
        elif result.returncode == 0:
            # Sin virus
            pass
        else:
            # Error en el escaneo
            logging.error(f'Error al escanear archivos {file_batch}: {result.stderr.strip()}')
    except Exception as e:
        logging.error(f'Excepción al escanear archivos {file_batch}: {e}')
    return len(file_batch)

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def main():
    parser = argparse.ArgumentParser(description='Escanea directorios con ClamAV.')
    parser.add_argument('directories', nargs='+', help='Directorios a escanear')
    parser.add_argument('-j', '--jobs', type=int, default=max(1, multiprocessing.cpu_count() - nucleosLibres),
                        help='Número de trabajos en paralelo (por defecto: CPUs - 1)')
    parser.add_argument('--exclude-dirs', nargs='*', default=['/proc', '/sys', '/dev', '/run', '/tmp', '/var/lib', '/var/run'],
                        help='Directorios a excluir del escaneo')
    parser.add_argument('--quarantine-dir', help='Directorio para mover archivos infectados')
    parser.add_argument('--log-file', default='clamav_scan.log', help='Archivo de log (por defecto: clamav_scan.log)')
    parser.add_argument('--batch-size', type=int, default=100, help='Número de archivos por lote para el escaneo (por defecto: 100)')
    args = parser.parse_args()

    # Configurar logging
    logging.basicConfig(filename=args.log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Verificar si clamdscan o clamscan están instalados
    if shutil.which('clamdscan'):
        scanner_cmd = 'clamdscan'
    elif shutil.which('clamscan'):
        scanner_cmd = 'clamscan'
    else:
        logging.error('No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')
        print('Error: No se encontró clamdscan ni clamscan. Por favor, instala ClamAV.')
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

    # Dividir los archivos en lotes
    batch_size = args.batch_size
    file_batches = list(chunker(files_to_scan, batch_size))

    # Lista para almacenar archivos infectados
    manager = multiprocessing.Manager()
    infected_files = manager.list()

    # Preparar función parcial para el escaneo
    scan_func = partial(scan_file, scanner_cmd, quarantine_dir, infected_files)

    # Crear un pool de procesos
    pool = multiprocessing.Pool(processes=args.jobs)

    # Escanear archivos con barra de progreso
    try:
        with tqdm(total=total_files, desc='Escaneando archivos', unit='archivo') as pbar:
            for nfiles in pool.imap_unordered(scan_func, file_batches):
                pbar.update(nfiles)
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
