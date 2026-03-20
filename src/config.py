"""
Papiro - Configuración global
Constantes, formatos de etiqueta, paleta de colores
"""

import sys
import os

# --- DPI & Conversión ---
DPI = 300

def mm_to_px(mm):
    return int(mm * DPI / 25.4)

def px_to_mm(px):
    return round(px * 25.4 / DPI, 2)

# --- Rutas ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_app_dir():
    """Directorio de la app para guardar config, templates, etc."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_assets_path():
    base = get_base_path()
    return os.path.join(base, 'src', 'assets')

def get_templates_path():
    path = os.path.join(get_app_dir(), 'src', 'templates')
    os.makedirs(path, exist_ok=True)
    return path

# --- Cinta Brother QL-800 ---
TAPE_WIDTH_MM = 62  # Ancho fijo de la cinta

# --- Formatos de etiqueta ---
LABEL_FORMATS = {
    "Despacho": {
        "description": "Despacho (62mm x 152mm)",
        "width_mm": TAPE_WIDTH_MM,   # ancho = ancho cinta (fijo)
        "height_mm": 152,            # largo = largo de corte
    },
    "Producto": {
        "description": "Producto (62mm x 29mm)",
        "width_mm": TAPE_WIDTH_MM,
        "height_mm": 29,
    },
}

# --- Parámetros de corte PDF (etiquetas de despacho) ---
PDF_LABEL_SPACING_PTS = 130
PDF_LABEL_HEIGHT_PTS = 120
PDF_MARGIN_TOP_PTS = 5
PDF_MARGIN_SIDES_PTS = 10
PDF_MAX_LABELS_PER_PAGE = 6

# --- Preview ---
PREVIEW_MAX_WIDTH = 520
PREVIEW_MAX_HEIGHT = 300

# --- Paleta de colores ---
BG_DARK = "#1a1a2e"
BG_CARD = "#16213e"
BG_CARD_LIGHT = "#1c2a4a"
ACCENT_BLUE = "#0f7dff"
ACCENT_GREEN = "#00c853"
ACCENT_ORANGE = "#ff6d00"
ACCENT_CYAN = "#00e5ff"
ACCENT_RED = "#ff1744"
TEXT_PRIMARY = "#e8eaf6"
TEXT_SECONDARY = "#7986cb"
TEXT_MUTED = "#455a80"
BORDER_COLOR = "#263159"

# --- App ---
APP_NAME = "Papiro"
APP_SUBTITLE = "Mawida Dispensario"
APP_VERSION = "2.0.0"
