@echo off
echo ========================================
echo   Construyendo EtiquetaTron.exe
echo ========================================
echo.

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt pyinstaller

echo.
echo Creando ejecutable...
pyinstaller --onefile --windowed --name "EtiquetaTron" --add-data "logo.png;." main.py

echo.
echo ========================================
echo   Build completado!
echo   El ejecutable esta en: dist\EtiquetaTron.exe
echo ========================================
pause
