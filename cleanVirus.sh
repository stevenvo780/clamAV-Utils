#!/bin/bash

# Descripción:
# Este script escanea los directorios especificados en busca de virus usando ClamAV,
# aprovechando múltiples hilos y mostrando barras de progreso para cada directorio.

# Requisitos:
# - ClamAV instalado
# - GNU Parallel instalado
# - Usuario con permisos de lectura en los directorios a escanear

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

    # Terminar el script si faltan dependencias
    if (( missing_dep  )); then
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

# Lista de unidades a escanear
drives=(
    "$HOME"
    #"/mnt/Documentos"
    #"/mnt/FASTDATA"
    #"/mnt/Juegos"
    #"/media/steven/E6AC99B7AC99832B"
)

# Número de trabajos paralelos (ajustable)
PARALLEL_JOBS=$(nproc)

# Función para mostrar barra de progreso
show_progress() {
    local current=$1
    local total=$2
    local dir_name="$3"
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))

    printf "\r[%s] %s%% Escaneando: %s" \
        "$(printf '#%.0s' $(seq 1 $filled))$(printf ' %.0s' $(seq 1 $empty))" \
        "$percent" \
        "$dir_name"
}

# Función para contar archivos en un directorio
count_files() {
    local dir="$1"
    local exclude_dirs=(
        "/sys"
        "/proc"
        "/dev"
        "\$RECYCLE.BIN"
        "System Volume Information"
    )

    # Construir patrón de exclusión para find
    local exclude_pattern=""
    for ex_dir in "${exclude_dirs[@]}"; do
        exclude_pattern+=" -path \"$dir/$ex_dir\" -prune -o"
    done

    # Contar el número total de archivos
    eval find "$dir" $exclude_pattern -type f -print0 | \
        xargs -0 -n1 echo &>/dev/null | wc -l
}

# Función para escanear un directorio
scan_directory() {
    local dir="$1"
    local total_files="$2"
    local current_file=0

    # Excluir directorios problemáticos
    local exclude_dirs=(
        "/sys"
        "/proc"
        "/dev"
        "\$RECYCLE.BIN"
        "System Volume Information"
    )

    # Construir patrón de exclusión para find
    local exclude_pattern=""
    for ex_dir in "${exclude_dirs[@]}"; do
        exclude_pattern+=" -path \"$dir/$ex_dir\" -prune -o"
    done

    if [ "$total_files" -eq 0 ]; then
        echo "No se encontraron archivos en $dir para escanear."
        return
    fi

    echo "Escaneando directorio: $dir" | tee -a "$LOG_FILE"

    # Escanear archivos individualmente y actualizar la barra de progreso
    eval find "$dir" $exclude_pattern -type f -print0 | \
        xargs -0 -n1 -P1 -I{} bash -c '
            file="$1"
            dir="$2"
            QUARANTINE_DIR="$3"
            LOG_FILE="$4"
            total_files="$5"
            current_file="$6"

            clamscan --no-summary --move="$QUARANTINE_DIR" "$file" &>/dev/null

            # Actualizar contador y barra de progreso
            current_file=$(($current_file + 1))
            show_progress "$current_file" "$total_files" "$dir"
        ' _ {} "$dir" "$QUARANTINE_DIR" "$LOG_FILE" "$total_files" "$current_file"

    echo ""  # Nueva línea después de la barra de progreso

    echo "✔ Escaneo completado para $dir" | tee -a "$LOG_FILE"
}

export -f scan_directory
export -f show_progress
export -f count_files
export QUARANTINE_DIR
export LOG_FILE

# Función para contar y luego escanear un directorio
count_and_scan() {
    local dir="$1"

    # Contar archivos en paralelo
    total_files=$(count_files "$dir" &)

    # Esperar a que termine el conteo
    wait $!

    # Iniciar el escaneo del directorio
    scan_directory "$dir" "$total_files"
}

export -f count_and_scan

# Iniciar conteo y escaneo con GNU Parallel
echo "Iniciando conteo y escaneo con $PARALLEL_JOBS trabajos paralelos..." | tee -a "$LOG_FILE"
parallel -j "$PARALLEL_JOBS" count_and_scan ::: "${drives[@]}"

echo "Análisis completo - $(date)" | tee -a "$LOG_FILE"
