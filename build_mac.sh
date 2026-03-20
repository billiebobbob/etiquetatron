#!/bin/bash
echo "========================================"
echo "  Construyendo Papiro"
echo "========================================"
echo

# Instalar dependencias
echo "Instalando dependencias..."
pip3 install -r requirements.txt pyinstaller

echo
echo "Creando ejecutable..."
pyinstaller --onefile --windowed --name "Papiro" \
    --add-data "src/assets/logo.png:src/assets" \
    --add-data "src/assets/icon.ico:src/assets" \
    --add-data "src/assets/icon.png:src/assets" \
    --add-data "src/templates:src/templates" \
    --collect-all customtkinter \
    --hidden-import PIL \
    --hidden-import PIL._tkinter_finder \
    main.py

echo
echo "========================================"
echo "  Build completado!"
echo "  El ejecutable esta en: dist/Papiro"
echo "========================================"
