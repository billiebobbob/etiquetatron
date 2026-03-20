"""
Papiro - Gestor de impresión
Detección de impresoras y envío a imprimir (macOS, Windows, Linux)
FIX: Imagen se genera en portrait (62w x Hmm), NO se rota. Se envía tal cual.
"""

import sys
import os
import subprocess
import tempfile
from PIL import Image

from src.config import DPI, TAPE_WIDTH_MM


def get_printers():
    """Detecta impresoras disponibles en el sistema."""
    printers = []
    try:
        if sys.platform == 'darwin' or sys.platform.startswith('linux'):
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.strip().split('\n'):
                if line.startswith('printer '):
                    printers.append(line.split()[1])
        elif sys.platform == 'win32':
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-Printer | Select-Object -ExpandProperty Name'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split('\n'):
                name = line.strip()
                if name:
                    printers.append(name)
    except Exception:
        pass
    return printers


def get_default_printer():
    """Obtiene la impresora por defecto del sistema."""
    try:
        if sys.platform == 'darwin' or sys.platform.startswith('linux'):
            result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.strip().split('\n'):
                if 'default' in line.lower() and ':' in line:
                    return line.split(':')[-1].strip()
        elif sys.platform == 'win32':
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '(Get-WmiObject -Query "SELECT * FROM Win32_Printer WHERE Default=$true").Name'],
                capture_output=True, text=True, timeout=5
            )
            name = result.stdout.strip()
            if name:
                return name
    except Exception:
        pass
    return None


def print_image(filepath, printer_name=None, width_mm=TAPE_WIDTH_MM, height_mm=None):
    """
    Imprime una imagen en la impresora seleccionada.

    La imagen DEBE venir en portrait: width=62mm (ancho cinta), height=largo etiqueta.
    NO se rota. Se envía tal cual al driver.

    Args:
        filepath: Ruta al archivo PNG
        printer_name: Nombre de la impresora
        width_mm: Ancho de cinta (62mm para Brother QL-800)
        height_mm: Largo de corte. Si None, se calcula del DPI de la imagen.
    """
    if sys.platform in ('darwin',) or sys.platform.startswith('linux'):
        return _print_cups(filepath, printer_name, width_mm, height_mm)
    elif sys.platform == 'win32':
        return _print_windows(filepath, printer_name, width_mm, height_mm)
    else:
        return subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="", stderr=f"Unsupported platform: {sys.platform}"
        )


def _print_cups(filepath, printer_name, width_mm, height_mm):
    """Imprime via CUPS (macOS/Linux). Sin rotación."""
    img = Image.open(filepath)
    w_px, h_px = img.size

    # Calcular largo de corte si no se especificó
    if height_mm is None:
        height_mm = round(h_px * 25.4 / DPI)

    cmd = ['lp']
    if printer_name:
        cmd.extend(['-d', printer_name])

    # Tamaño de papel custom: ancho=cinta, alto=largo de corte
    cmd.extend(['-o', f'media=Custom.{width_mm}x{height_mm}mm'])
    cmd.extend(['-o', 'fit-to-page'])
    cmd.append(filepath)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result


def _print_windows(filepath, printer_name, width_mm, height_mm):
    """
    Imprime en Windows via PowerShell/.NET.
    Crea PaperSize custom desde las dimensiones de la imagen.
    La imagen ya viene en portrait, no se rota.
    """
    fp = filepath.replace('\\', '/')
    pn = (printer_name or "").replace("'", "''").replace('"', '`"')

    ps_script = f'''
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$bitmap = [System.Drawing.Image]::FromFile("{fp}")

$pd = New-Object System.Drawing.Printing.PrintDocument
$pd.PrinterSettings.PrinterName = "{pn}"

# Calcular tamaño exacto desde la imagen (en centesimas de pulgada)
$wHundredths = [int]($bitmap.Width / $bitmap.HorizontalResolution * 100)
$hHundredths = [int]($bitmap.Height / $bitmap.VerticalResolution * 100)
$customSize = New-Object System.Drawing.Printing.PaperSize("Papiro", $wHundredths, $hHundredths)
$pd.DefaultPageSettings.PaperSize = $customSize
$pd.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
$pd.DefaultPageSettings.Landscape = $false

$pd.add_PrintPage({{
    param($sender, $e)
    $destRect = New-Object System.Drawing.RectangleF(0, 0, $e.PageBounds.Width, $e.PageBounds.Height)
    $e.Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $e.Graphics.DrawImage($bitmap, $destRect)
}})

$pd.Print()
$bitmap.Dispose()
$pd.Dispose()
Write-Output "OK"
'''
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=30
        )
        return result
    except Exception as e:
        try:
            os.startfile(filepath, 'print')
            return subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout="Sent via os.startfile", stderr=""
            )
        except Exception:
            pass
        return subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="", stderr=str(e)
        )


def open_printer_config(printer_name):
    """Abre la ventana de configuración de la impresora."""
    try:
        if sys.platform == 'win32':
            subprocess.Popen(['rundll32', 'printui.dll,PrintUIEntry', '/e', '/n', printer_name])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-b', 'com.apple.systempreferences',
                              '/System/Library/PreferencePanes/PrintAndFax.prefPane'])
        else:
            subprocess.Popen(['xdg-open', 'system-config-printer'])
    except Exception as e:
        raise RuntimeError(f"Error abriendo config: {e}")
