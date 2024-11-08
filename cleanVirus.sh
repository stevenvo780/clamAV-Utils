#!/bin/bash

# Crear una carpeta de cuarentena con permisos restringidos
QUARANTINE_DIR="/home/$USER/quarantine"
mkdir -p "$QUARANTINE_DIR"
chmod 700 "$QUARANTINE_DIR"

# Archivo de log general
LOG_FILE="/home/$USER/clamav_scan.log"
echo "Iniciando análisis de virus - $(date)" > "$LOG_FILE"

# Función para escanear una unidad
scan_drive() {
    local drive_path="$1"
    local temp_log="/tmp/clamav_scan_$(basename "$drive_path").log"
    echo "Escaneando unidad: $drive_path" | tee -a "$LOG_FILE"
    sudo clamscan -r --move="$QUARANTINE_DIR" --log="$temp_log" "$drive_path"
    cat "$temp_log" >> "$LOG_FILE"
    rm "$temp_log"
}

# Lista de unidades a escanear
#drives=("/mnt/Biblioteca" "/mnt/DataExternal" "/mnt/Documentos" "/mnt/FASTDATA" "/mnt/Juegos" "/mnt/Windows")
drives=("/home")

# Ejecutar el escaneo en cada unidad
for drive in "${drives[@]}"; do
    scan_drive "$drive" &
done

# Esperar a que todos los escaneos finalicen
wait

echo "Análisis completo - $(date)" | tee -a "$LOG_FILE"
