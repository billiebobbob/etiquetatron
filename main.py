"""
Papiro - Sistema de etiquetas para Mawida Dispensario
Entry point
"""

import sys
import os

# Asegurar que el directorio raíz esté en el path
if getattr(sys, 'frozen', False):
    # PyInstaller: _MEIPASS es el directorio temporal
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.app import run

if __name__ == "__main__":
    run()
