#!/bin/bash
echo "========================================"
echo "  Construyendo EtiquetaTron"
echo "========================================"
echo

# Instalar dependencias
echo "Instalando dependencias..."
pip3 install -r requirements.txt pyinstaller

echo
echo "Creando ejecutable..."
pyinstaller --onefile --windowed --name "EtiquetaTron" --add-data "logo.png:." main.py

echo
echo "========================================"
echo "  Build completado!"
echo "  El ejecutable esta en: dist/EtiquetaTron"
echo "========================================"
