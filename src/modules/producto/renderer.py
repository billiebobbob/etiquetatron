"""
Papiro - Renderer de etiquetas de producto
Renderiza una etiqueta a partir de un template + datos variables.
Orientado a Brother QL-800 con cinta de 62mm.
"""

import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

from src.config import DPI, TAPE_WIDTH_MM, mm_to_px


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

# Directorios de fuentes por plataforma
_FONT_DIRS = {
    "darwin": [
        "/System/Library/Fonts",
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
    ],
    "win32": [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    ],
    "linux": [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.expanduser("~/.fonts"),
        os.path.expanduser("~/.local/share/fonts"),
    ],
}


def _font_search_dirs():
    """Devuelve la lista de directorios de fuentes para la plataforma actual."""
    for key, dirs in _FONT_DIRS.items():
        if sys.platform.startswith(key) or sys.platform == key:
            return dirs
    return _FONT_DIRS.get("linux", [])


def get_available_fonts():
    """
    Returns list of font names available on the system.
    Scans platform-specific font directories for .ttf/.otf files.
    """
    fonts = set()
    for font_dir in _font_search_dirs():
        if not os.path.isdir(font_dir):
            continue
        for root, _dirs, files in os.walk(font_dir):
            for f in files:
                if f.lower().endswith((".ttf", ".otf")):
                    name = os.path.splitext(f)[0]
                    fonts.add(name)
    return sorted(fonts)


def _resolve_font(name, size, bold=False, italic=False):
    """
    Intenta cargar una fuente por nombre y tamaño.
    Busca en los directorios del sistema; si no la encuentra, devuelve la default.
    """
    if not name:
        return ImageFont.load_default()

    # Variantes a probar
    suffixes = []
    if bold and italic:
        suffixes += ["BoldItalic", "Bold Italic", "-BoldItalic", "BI"]
    if bold:
        suffixes += ["Bold", "-Bold", "B"]
    if italic:
        suffixes += ["Italic", "-Italic", "I"]
    suffixes.append("")  # sin sufijo

    candidates = []
    for suffix in suffixes:
        if suffix:
            candidates.append(f"{name}-{suffix}")
            candidates.append(f"{name}{suffix}")
        else:
            candidates.append(name)

    for font_dir in _font_search_dirs():
        if not os.path.isdir(font_dir):
            continue
        for root, _dirs, files in os.walk(font_dir):
            for candidate in candidates:
                for ext in (".ttf", ".otf"):
                    fname = candidate + ext
                    if fname in files:
                        try:
                            return ImageFont.truetype(os.path.join(root, fname), size)
                        except Exception:
                            pass

    # Fallback: intentar truetype directo (puede funcionar si el OS lo resuelve)
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        pass

    # Ultimo recurso
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Variable substitution
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _substitute(text, variables):
    """Reemplaza {{variable}} con valores del diccionario."""
    def _repl(m):
        key = m.group(1)
        return str(variables.get(key, m.group(0)))
    return _VAR_RE.sub(_repl, text)


# ---------------------------------------------------------------------------
# Element renderers
# ---------------------------------------------------------------------------

def _render_text(draw, elem, variables, dpi):
    """Renderiza un TextElement."""
    text = _substitute(elem.get("text", ""), variables)
    x = mm_to_px(elem.get("x", 0))
    y = mm_to_px(elem.get("y", 0))
    font_size = elem.get("font_size", 12)
    font_name = elem.get("font", "")
    bold = elem.get("bold", False)
    italic = elem.get("italic", False)
    color = elem.get("color", "#000000")
    alignment = elem.get("alignment", "left")
    max_width = mm_to_px(elem.get("max_width", 0)) if elem.get("max_width") else None

    # Escalar tamanio de fuente al DPI
    font_size_px = int(font_size * dpi / 72)
    font = _resolve_font(font_name, font_size_px, bold=bold, italic=italic)

    if max_width and max_width > 0:
        # Word wrap
        lines = _wrap_text(draw, text, font, max_width)
    else:
        lines = text.split("\n")

    line_spacing = int(font_size_px * 1.3)

    for i, line in enumerate(lines):
        lx = x
        if alignment in ("center", "centre") and max_width:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            lx = x + (max_width - tw) // 2
        elif alignment == "right" and max_width:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            lx = x + max_width - tw

        draw.text((lx, y + i * line_spacing), line, fill=color, font=font)


def _wrap_text(draw, text, font, max_width):
    """Divide el texto en lineas que quepan en max_width pixeles."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _render_image(canvas, elem, dpi):
    """Renderiza un ImageElement — carga y pega una imagen."""
    path = elem.get("path", "")
    if not path or not os.path.isfile(path):
        return

    x = mm_to_px(elem.get("x", 0))
    y = mm_to_px(elem.get("y", 0))
    w = mm_to_px(elem.get("width", 10))
    h = mm_to_px(elem.get("height", 10))

    try:
        img = Image.open(path)
        # Respetar aspect ratio
        if elem.get("keep_aspect", True):
            img.thumbnail((w, h), Image.LANCZOS)
        else:
            img = img.resize((w, h), Image.LANCZOS)

        if img.mode == "RGBA":
            canvas.paste(img, (x, y), img)
        else:
            canvas.paste(img, (x, y))
    except Exception:
        pass


def _render_rect(draw, elem, dpi):
    """Renderiza un RectElement — rectangulo con fill, borde y bordes redondeados."""
    x = mm_to_px(elem.get("x", 0))
    y = mm_to_px(elem.get("y", 0))
    w = mm_to_px(elem.get("width", 10))
    h = mm_to_px(elem.get("height", 10))
    fill = elem.get("fill", None)
    outline = elem.get("border_color", None)
    border_w = elem.get("border_width", 1)
    radius = mm_to_px(elem.get("corner_radius", 0)) if elem.get("corner_radius") else 0

    if radius > 0:
        draw.rounded_rectangle(
            [x, y, x + w, y + h],
            radius=radius,
            fill=fill,
            outline=outline,
            width=border_w,
        )
    else:
        draw.rectangle(
            [x, y, x + w, y + h],
            fill=fill,
            outline=outline,
            width=border_w,
        )


def _render_line(draw, elem, dpi):
    """Renderiza un LineElement."""
    x1 = mm_to_px(elem.get("x1", 0))
    y1 = mm_to_px(elem.get("y1", 0))
    x2 = mm_to_px(elem.get("x2", 0))
    y2 = mm_to_px(elem.get("y2", 0))
    color = elem.get("color", "#000000")
    width = elem.get("width", 1)
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)


def _render_qr(canvas, elem, variables, dpi):
    """Renderiza un QRElement — genera un QR code y lo pega."""
    try:
        import qrcode
    except ImportError:
        # qrcode library not installed, draw placeholder
        draw = ImageDraw.Draw(canvas)
        x = mm_to_px(elem.get("x", 0))
        y = mm_to_px(elem.get("y", 0))
        s = mm_to_px(elem.get("size", 10))
        draw.rectangle([x, y, x + s, y + s], outline="#999999", width=1)
        draw.text((x + 4, y + 4), "QR", fill="#999999")
        return

    data = _substitute(elem.get("data", ""), variables)
    x = mm_to_px(elem.get("x", 0))
    y = mm_to_px(elem.get("y", 0))
    size = mm_to_px(elem.get("size", 10))

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((size, size), Image.LANCZOS)
    canvas.paste(qr_img, (x, y))


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_ELEMENT_RENDERERS = {
    "text": "text",
    "image": "image",
    "rect": "rect",
    "rectangle": "rect",
    "line": "line",
    "qr": "qr",
    "qrcode": "qr",
}


# ---------------------------------------------------------------------------
# LabelRenderer
# ---------------------------------------------------------------------------

class LabelRenderer:
    """
    Renderiza una etiqueta de producto a partir de un template + datos.
    """

    def render(self, template_data, variables, dpi=DPI):
        """
        Render a template with variable substitution.

        Args:
            template_data: dict with keys:
                - width_mm (float): ancho en mm (normalmente 62)
                - height_mm (float): alto en mm
                - background (str|None): color de fondo o None para blanco
                - elements (list[dict]): lista de elementos a renderizar
            variables: dict con valores para sustituir, por ejemplo:
                {"producto": "Candy Cake", "nombre_paciente": "Juan",
                 "fecha": "20/03/2026", "peso": "5g", "cepa": "Indica"}

        Returns:
            PIL.Image en portrait (width=62mm, height=template height)
            con metadata DPI configurada.
        """
        width_mm = template_data.get("width_mm", TAPE_WIDTH_MM)
        height_mm = template_data.get("height_mm", 29)
        background = template_data.get("background", "#FFFFFF")

        width_px = mm_to_px(width_mm)
        height_px = mm_to_px(height_mm)

        # Crear canvas
        canvas = Image.new("RGB", (width_px, height_px), background or "#FFFFFF")
        draw = ImageDraw.Draw(canvas)

        # Procesar elementos
        elements = template_data.get("elements", [])
        for elem in elements:
            etype = _ELEMENT_RENDERERS.get(elem.get("type", "").lower())
            if etype == "text":
                _render_text(draw, elem, variables, dpi)
            elif etype == "image":
                _render_image(canvas, elem, dpi)
                draw = ImageDraw.Draw(canvas)  # refresh after paste
            elif etype == "rect":
                _render_rect(draw, elem, dpi)
            elif etype == "line":
                _render_line(draw, elem, dpi)
            elif etype == "qr":
                _render_qr(canvas, elem, variables, dpi)
                draw = ImageDraw.Draw(canvas)  # refresh after paste

        # Setear DPI metadata
        canvas.info["dpi"] = (dpi, dpi)

        return canvas

    def render_preview(self, template_data, variables, max_width=520, max_height=300, dpi=DPI):
        """
        Renderiza y escala para preview en UI.
        Devuelve (full_image, preview_image).
        """
        full = self.render(template_data, variables, dpi=dpi)

        # Escalar para preview manteniendo aspecto
        w, h = full.size
        scale = min(max_width / w, max_height / h, 1.0)
        preview_w = max(1, int(w * scale))
        preview_h = max(1, int(h * scale))
        preview = full.resize((preview_w, preview_h), Image.LANCZOS)

        return full, preview
