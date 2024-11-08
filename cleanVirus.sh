#!/bin/bash

# Validar e instalar dependencias
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

    # Verificar e instalar ClamAV y clamdscan
    if ! command -v clamdscan &> /dev/null; then
        echo "Instalando ClamAV y configurando clamd..."
        if sudo apt update && sudo apt install -y clamav clamav-daemon; then
            echo "ClamAV y clamd instalados con éxito."
            # Iniciar y habilitar el servicio clamd
            sudo systemctl start clamav-daemon
            sudo systemctl enable clamav-daemon
        else
            echo "Error: No se pudo instalar ClamAV y clamd." >&2
            missing_dep=1
        fi
    fi

    # Verificar que el servicio clamd esté activo
    if ! sudo systemctl is-active --quiet clamav-daemon; then
        echo "Iniciando el servicio clamd..."
        sudo systemctl start clamav-daemon
        if ! sudo systemctl is-active --quiet clamav-daemon; then
            echo "Error: No se pudo iniciar el servicio clamd. Verifique la instalación." >&2
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

# Lista de unidades a escanear
drives=(
    "$HOME"
    "/mnt/Documentos"
    "/mnt/FASTDATA"
    "/mnt/Juegos"
    "/media/steven/E6AC99B7AC99832B"
)

# Número de trabajos paralelos
PARALLEL_JOBS=$(nproc)

# Función para escanear un directorio
scan_directory() {
    local dir="$1"
    echo "Escaneando directorio: $dir" | tee -a "$LOG_FILE"

    clamdscan --fdpass --multiscan \
        --move="$QUARANTINE_DIR" \
        --exclude-dir='^/sys' \
        --exclude-dir='^/proc' \
        --exclude-dir='^/dev' \
        --exclude-dir='^\$RECYCLE.BIN' \
        --exclude-dir='^System Volume Information' \
        "$dir" 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -ne 0 ]; then
        echo "Error: Fallo el escaneo para $dir con código $exit_code" | tee -a "$LOG_FILE"
    else
        echo "✔ Escaneo completado para $dir" | tee -a "$LOG_FILE"
    fi
}

export -f scan_directory
export QUARANTINE_DIR
export LOG_FILE

# Iniciar escaneo con GNU Parallel
echo "Iniciando escaneos con $PARALLEL_JOBS trabajos paralelos..." | tee -a "$LOG_FILE"
printf "%s\n" "${drives[@]}" | parallel -j "$PARALLEL_JOBS" scan_directory {}

echo "Análisis completo - $(date)" | tee -a "$LOG_FILE"
