@echo off
echo ========================================
echo   Construyendo Papiro.exe
echo ========================================
echo.

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt pyinstaller

echo.
echo Creando ejecutable...
pyinstaller --onefile --windowed --name "Papiro" --icon "src/assets/icon.ico" ^
    --add-data "src/assets/logo.png;src/assets" ^
    --add-data "src/assets/icon.ico;src/assets" ^
    --add-data "src/assets/icon.png;src/assets" ^
    --add-data "src/templates;src/templates" ^
    --collect-all customtkinter ^
    --hidden-import PIL ^
    --hidden-import PIL._tkinter_finder ^
    main.py

echo.
echo ========================================
echo   Build completado!
echo   El ejecutable esta en: dist\Papiro.exe
echo ========================================
pause
