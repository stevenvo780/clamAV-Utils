#!/bin/bash

# Descripción:
# Este script escanea los directorios especificados en busca de virus usando ClamAV,
# aprovechando múltiples hilos y mostrando barras de progreso para cada directorio.

# Requisitos:
# - ClamAV instalado
# - GNU Parallel instalado
# - Usuario con permisos de lectura en los directorios a escanear
# - pv instalado (para mostrar el progreso)

# Función para mostrar el uso del script
usage() {
    echo "Uso: $0 [opciones] directorio1 directorio2 ..."
    echo "Opciones:"
    echo "  -h, --help    Muestra esta ayuda y termina."
    exit 1
}

# Verificar si se ha solicitado ayuda
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
fi

# Verificar si se han proporcionado directorios
if [ $# -lt 1 ]; then
    echo "Error: Debes proporcionar al menos un directorio para escanear."
    usage
fi

# Lista de unidades a escanear
drives=("$@")

# Función para validar e instalar dependencias
install_dependencies() {
    local missing_dep=0

    # Verificar e instalar parallel
    if ! command -v parallel &> /dev/null; then
        echo "Instalando GNU Parallel..."
        if sudo apt update && sudo apt install -y parallel; then
            echo "GNU Parallel instalado con éxito."
        else
            echo "Error: No se pudo instalar GNU Parallel." >&2
            missing_dep=1
        fi
    fi

    # Verificar e instalar ClamAV
    if ! command -v clamscan &> /dev/null; then
        echo "Instalando ClamAV..."
        if sudo apt update && sudo apt install -y clamav; then
            echo "ClamAV instalado con éxito."
            # Actualizar las definiciones de virus
            sudo freshclam
        else
            echo "Error: No se pudo instalar ClamAV." >&2
            missing_dep=1
        fi
    fi

    # Verificar e instalar pv
    if ! command -v pv &> /dev/null; then
        echo "Instalando pv..."
        if sudo apt update && sudo apt install -y pv; then
            echo "pv instalado con éxito."
        else
            echo "Error: No se pudo instalar pv." >&2
            missing_dep=1
        fi
    fi

    # Terminar el script si faltan dependencias
    if (( missing_dep )); then
        echo "Error: No se pueden satisfacer todas las dependencias. Saliendo..." >&2
        exit 1
    fi
}

# Ejecutar la función de instalación de dependencias
install_dependencies

# Crear una carpeta de cuarentena con permisos restringidos
QUARANTINE_DIR="$HOME/quarantine"
if ! mkdir -p "$QUARANTINE_DIR"; then
    echo "Error: No se pudo crear el directorio de cuarentena en $QUARANTINE_DIR" >&2
    exit 1
fi
chmod 700 "$QUARANTINE_DIR"

# Archivo de log general
LOG_FILE="$HOME/clamav_scan.log"
echo "Iniciando análisis de virus - $(date)" > "$LOG_FILE"

# Número de trabajos paralelos (ajustable)
PARALLEL_JOBS=$(nproc)

# Función para escanear un directorio
scan_directory() {
    local dir="$1"

    # Excluir directorios problemáticos
    local exclude_dirs=(
        "/sys"
        "/proc"
        "/dev"
        "\$RECYCLE.BIN"
        "System Volume Information"
    )

    # Construir patrón de exclusión para find
    local exclude_expr=""
    for ex_dir in "${exclude_dirs[@]}"; do
        exclude_expr+=" -path \"$dir/$ex_dir\" -prune -o"
    done

    echo "Escaneando directorio: $dir" | tee -a "$LOG_FILE"

    # Generar lista de archivos
    local file_list="/tmp/file_list_$(echo "$dir" | md5sum | cut -d' ' -f1).txt"
    eval find "$dir" $exclude_expr -type f > "$file_list"

    local total_files
    total_files=$(wc -l < "$file_list")
    if [ "$total_files" -eq 0 ]; then
        echo "No se encontraron archivos en $dir para escanear."
        rm -f "$file_list"
        return
    fi

    # Escanear archivos en paralelo usando pv para mostrar progreso
    cat "$file_list" | pv -l -s "$total_files" | \
    parallel -P "$PARALLEL_JOBS" --no-notice \
    'clamscan --no-summary --move="$QUARANTINE_DIR" "{}" &>/dev/null'

    rm -f "$file_list"

    echo ""  # Nueva línea después de la barra de progreso

    echo "✔ Escaneo completado para $dir" | tee -a "$LOG_FILE"
}

export -f scan_directory
export QUARANTINE_DIR
export LOG_FILE
export PARALLEL_JOBS

# Iniciar escaneo con GNU Parallel
echo "Iniciando escaneos con $PARALLEL_JOBS trabajos paralelos..." | tee -a "$LOG_FILE"
parallel -j "$PARALLEL_JOBS" scan_directory ::: "${drives[@]}"

echo "Análisis completo - $(date)" | tee -a "$LOG_FILE"
