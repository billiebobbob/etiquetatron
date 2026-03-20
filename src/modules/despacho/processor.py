"""
Papiro - Despacho: Procesador de PDF
Corta etiquetas de despacho desde un PDF y genera imágenes PNG en portrait.

Impresora: Brother QL-800, cinta 62mm continua.
Orientación: PORTRAIT (width=62mm, height=152mm). NUNCA landscape.
"""

import os
import re
import fitz  # PyMuPDF
from PIL import Image

from src.config import (
    DPI,
    LABEL_FORMATS,
    PDF_LABEL_SPACING_PTS,
    PDF_LABEL_HEIGHT_PTS,
    PDF_MARGIN_TOP_PTS,
    PDF_MARGIN_SIDES_PTS,
    PDF_MAX_LABELS_PER_PAGE,
    mm_to_px,
)

# Canvas size in pixels at 300 DPI — PORTRAIT
CANVAS_WIDTH_PX = mm_to_px(LABEL_FORMATS["Despacho"]["width_mm"])    # 62mm -> 732px
CANVAS_HEIGHT_PX = mm_to_px(LABEL_FORMATS["Despacho"]["height_mm"])  # 152mm -> 1795px


def _find_labels_on_page(page):
    """
    Busca patrones 'Venta: SXXXXX' en el texto de la página.
    Retorna lista de dicts con {'venta': str, 'y_position': float}.
    """
    blocks = page.get_text("dict")["blocks"]
    labels = []

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                match = re.search(r"Venta:\s*(S\d+)", text)
                if match:
                    venta = match.group(1)
                    y_pos = span["bbox"][1]  # top-y of the text
                    labels.append({"venta": venta, "y_position": y_pos})

    return labels


def _extract_date(page):
    """
    Extrae la primera fecha DD/MM/YYYY encontrada en la página.
    """
    text = page.get_text()
    match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if match:
        return match.group(1)
    return None


def _cut_label(page, label_index, page_width_pts):
    """
    Corta una etiqueta individual del PDF según su índice en la página.

    Calcula el rectángulo de recorte usando las constantes de espaciado,
    y renderiza a un pixmap de 300 DPI.

    Returns:
        PIL.Image en modo RGB, ya recortada.
    """
    y_top = PDF_MARGIN_TOP_PTS + label_index * PDF_LABEL_SPACING_PTS
    y_bottom = y_top + PDF_LABEL_HEIGHT_PTS

    x_left = PDF_MARGIN_SIDES_PTS
    x_right = page_width_pts - PDF_MARGIN_SIDES_PTS

    clip_rect = fitz.Rect(x_left, y_top, x_right, y_bottom)

    # Renderizar con 300 DPI (factor = DPI / 72)
    zoom = DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)

    # Convertir pixmap a PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def _place_on_canvas(label_img, canvas_w=CANVAS_WIDTH_PX, canvas_h=CANVAS_HEIGHT_PX):
    """
    Coloca la imagen de la etiqueta centrada sobre un canvas blanco PORTRAIT.

    Canvas: 732 x 1795 px (62mm x 152mm @ 300 DPI).
    La etiqueta se escala para caber en el ancho del canvas, manteniendo
    la relación de aspecto, y se centra verticalmente.
    """
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")

    lw, lh = label_img.size

    # Escalar la etiqueta para que ocupe el ancho del canvas
    scale = canvas_w / lw
    new_w = canvas_w
    new_h = int(lh * scale)

    # Si la etiqueta escalada es más alta que el canvas, escalar por alto
    if new_h > canvas_h:
        scale = canvas_h / lh
        new_w = int(lw * scale)
        new_h = canvas_h

    label_resized = label_img.resize((new_w, new_h), Image.LANCZOS)

    # Centrar en el canvas
    x_offset = (canvas_w - new_w) // 2
    y_offset = (canvas_h - new_h) // 2

    canvas.paste(label_resized, (x_offset, y_offset))
    return canvas


def process_pdf(pdf_path, width_mm=62, height_mm=152):
    """
    Procesa un PDF de etiquetas de despacho.

    Abre el PDF, detecta etiquetas por patrón "Venta: SXXXXX",
    corta cada una y la coloca centrada en un canvas portrait.

    Args:
        pdf_path: Ruta al archivo PDF.
        width_mm: Ancho del canvas en mm (62 para Brother QL-800).
        height_mm: Alto del canvas en mm (152 para despacho).

    Returns:
        Tupla (labels_list, date_str) donde:
        - labels_list: Lista de dicts {'image': PIL.Image, 'venta': str}
        - date_str: Fecha extraída del PDF (DD/MM/YYYY) o None
    """
    canvas_w = mm_to_px(width_mm)
    canvas_h = mm_to_px(height_mm)

    doc = fitz.open(pdf_path)
    labels = []
    date_str = None

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_width = page.rect.width

        # Extraer fecha de la primera página que tenga una
        if date_str is None:
            date_str = _extract_date(page)

        # Buscar etiquetas en la página
        found = _find_labels_on_page(page)

        if found:
            # Ordenar por posición Y (de arriba a abajo)
            found.sort(key=lambda x: x["y_position"])

            for idx, label_info in enumerate(found):
                if idx >= PDF_MAX_LABELS_PER_PAGE:
                    break

                label_img = _cut_label(page, idx, page_width)
                canvas_img = _place_on_canvas(label_img, canvas_w, canvas_h)

                labels.append({
                    "image": canvas_img,
                    "venta": label_info["venta"],
                })
        else:
            # Si no se detectan patrones, intentar cortar por posición
            # (páginas con etiquetas pero sin texto detectado)
            for idx in range(PDF_MAX_LABELS_PER_PAGE):
                y_top = PDF_MARGIN_TOP_PTS + idx * PDF_LABEL_SPACING_PTS
                if y_top + PDF_LABEL_HEIGHT_PTS > page.rect.height:
                    break

                label_img = _cut_label(page, idx, page_width)

                # Verificar que no sea una franja vacía (casi toda blanca)
                extrema = label_img.getextrema()
                # Si todos los canales tienen min > 240, es blanco
                if all(ch[0] > 240 for ch in extrema):
                    continue

                canvas_img = _place_on_canvas(label_img, canvas_w, canvas_h)
                labels.append({
                    "image": canvas_img,
                    "venta": f"Etiqueta_{page_num + 1}_{idx + 1}",
                })

    doc.close()
    return labels, date_str


def save_labels(labels, format_name, date_str, base_dir):
    """
    Guarda todas las etiquetas como PNG en disco.

    Estructura de carpetas: base_dir/Despacho_DDMMYYYY/
    Nombre de archivo: venta_code.png

    Args:
        labels: Lista de dicts {'image': PIL.Image, 'venta': str}
        format_name: Nombre del formato (ej: "Despacho")
        date_str: Fecha DD/MM/YYYY para nombrar la carpeta
        base_dir: Directorio base donde guardar

    Returns:
        Lista de rutas absolutas de archivos guardados.
    """
    # Construir nombre de carpeta
    if date_str:
        folder_date = date_str.replace("/", "")
    else:
        folder_date = "sin_fecha"

    output_dir = os.path.join(base_dir, f"{format_name}_{folder_date}")
    os.makedirs(output_dir, exist_ok=True)

    saved_paths = []

    for label in labels:
        img = label["image"]
        venta = label["venta"]

        # Limpiar nombre de archivo
        safe_name = re.sub(r'[^\w\-]', '_', venta)
        filename = f"{safe_name}.png"
        filepath = os.path.join(output_dir, filename)

        # Guardar con metadata DPI
        img.save(filepath, "PNG", dpi=(DPI, DPI))
        saved_paths.append(filepath)

    return saved_paths
