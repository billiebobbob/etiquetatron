"""
Papiro - Template Store
CRUD for label templates stored as JSON files, plus rendering.
"""

import json
import os
import re
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from src.config import mm_to_px, DPI
from src.modules.designer.elements import Element


class TemplateStore:
    """Manages label templates as JSON files in a directory."""

    def __init__(self, templates_dir):
        self.templates_dir = templates_dir
        os.makedirs(self.templates_dir, exist_ok=True)

    def _template_path(self, name):
        safe_name = re.sub(r'[^\w\s\-]', '', name).strip()
        return os.path.join(self.templates_dir, f"{safe_name}.json")

    def _thumbnail_path(self, name):
        safe_name = re.sub(r'[^\w\s\-]', '', name).strip()
        return os.path.join(self.templates_dir, f".thumb_{safe_name}.png")

    # --- CRUD ---

    def list_templates(self) -> list[dict]:
        """List all saved templates with name, path, and thumbnail path."""
        templates = []
        if not os.path.exists(self.templates_dir):
            return templates
        for filename in sorted(os.listdir(self.templates_dir)):
            if filename.endswith(".json"):
                name = filename[:-5]
                path = os.path.join(self.templates_dir, filename)
                thumb = self._thumbnail_path(name)
                templates.append({
                    "name": name,
                    "path": path,
                    "thumbnail_path": thumb if os.path.exists(thumb) else None,
                })
        return templates

    def load_template(self, name) -> dict:
        """Load a template by name. Returns the full template dict."""
        path = self._template_path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template '{name}' not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_template(self, name, width_mm, height_mm, elements,
                      background="#FFFFFF"):
        """Save a template to disk and generate a thumbnail."""
        data = {
            "name": name,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "background": background,
            "elements": [e.to_dict() if hasattr(e, 'to_dict') else e
                         for e in elements],
            "saved_at": datetime.now().isoformat(),
        }
        path = self._template_path(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Generate thumbnail
        try:
            preview = self.render_preview(data, dpi=72)
            thumb = preview.copy()
            thumb.thumbnail((200, 200), Image.LANCZOS)
            thumb.save(self._thumbnail_path(name))
        except Exception:
            pass

        return path

    def delete_template(self, name):
        """Delete a template and its thumbnail."""
        path = self._template_path(name)
        if os.path.exists(path):
            os.remove(path)
        thumb = self._thumbnail_path(name)
        if os.path.exists(thumb):
            os.remove(thumb)

    def duplicate_template(self, name, new_name):
        """Duplicate a template under a new name."""
        data = self.load_template(name)
        data["name"] = new_name
        elements = [Element.from_dict(e) for e in data.get("elements", [])]
        self.save_template(
            new_name,
            data.get("width_mm", 62),
            data.get("height_mm", 29),
            elements,
            data.get("background", "#FFFFFF"),
        )

    # --- Rendering ---

    def render_preview(self, template_data, variables=None, dpi=300) -> Image.Image:
        """
        Render a template to a PIL Image with variable substitution.
        Returns the final image ready for printing.
        """
        if variables is None:
            variables = {}

        width_mm = template_data.get("width_mm", 62)
        height_mm = template_data.get("height_mm", 29)
        background = template_data.get("background", "#FFFFFF")

        width_px = int(width_mm * dpi / 25.4)
        height_px = int(height_mm * dpi / 25.4)

        img = Image.new("RGB", (width_px, height_px), background)
        draw = ImageDraw.Draw(img)

        scale = dpi / 25.4  # pixels per mm

        elements_data = template_data.get("elements", [])
        # Sort by z_index
        elements_data = sorted(elements_data, key=lambda e: e.get("z_index", 0))

        for elem_data in elements_data:
            etype = elem_data.get("type", "")
            x = elem_data.get("x_mm", 0) * scale
            y = elem_data.get("y_mm", 0) * scale
            w = elem_data.get("width_mm", 0) * scale
            h = elem_data.get("height_mm", 0) * scale

            if etype == "text":
                self._render_text(draw, elem_data, x, y, w, h, scale, variables)
            elif etype == "rect":
                self._render_rect(draw, elem_data, x, y, w, h)
            elif etype == "line":
                self._render_line(draw, elem_data, x, y, w, h)
            elif etype == "image":
                self._render_image(img, elem_data, x, y, w, h)
            elif etype == "qr":
                self._render_qr(img, elem_data, x, y, w, h, variables)

        return img

    def _substitute_vars(self, text, variables):
        """Replace {{variable}} placeholders with values."""
        def replacer(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))
        return re.sub(r'\{\{(\w+)\}\}', replacer, text)

    def _get_font(self, family, size_pt, weight="normal"):
        """Try to load a TrueType font, fall back to default."""
        try:
            # Try common system font paths
            font_names = {
                "Helvetica": ["Helvetica.ttc", "Helvetica", "Arial.ttf",
                              "arial.ttf", "DejaVuSans.ttf"],
                "Arial": ["Arial.ttf", "arial.ttf", "Helvetica.ttc",
                           "DejaVuSans.ttf"],
                "Courier": ["Courier.ttc", "Courier New.ttf",
                            "cour.ttf", "DejaVuSansMono.ttf"],
                "Times": ["Times New Roman.ttf", "times.ttf",
                          "DejaVuSerif.ttf"],
            }

            # macOS font directories
            font_dirs = [
                "/System/Library/Fonts/",
                "/System/Library/Fonts/Supplemental/",
                "/Library/Fonts/",
                os.path.expanduser("~/Library/Fonts/"),
            ]

            candidates = font_names.get(family, [family + ".ttf", family + ".ttc"])

            for font_dir in font_dirs:
                for fname in candidates:
                    fpath = os.path.join(font_dir, fname)
                    if os.path.exists(fpath):
                        return ImageFont.truetype(fpath, int(size_pt))

            # Last resort: let PIL find it
            return ImageFont.truetype(family, int(size_pt))
        except (OSError, IOError):
            try:
                return ImageFont.load_default(size=int(size_pt))
            except TypeError:
                return ImageFont.load_default()

    def _render_text(self, draw, elem, x, y, w, h, scale, variables):
        content = self._substitute_vars(elem.get("content", ""), variables)
        font_size = elem.get("font_size", 12)
        # Scale font size from points to render-space pixels
        render_size = font_size * scale / 2.835  # pt to mm ratio approx
        font = self._get_font(
            elem.get("font_family", "Helvetica"),
            render_size,
            elem.get("font_weight", "normal"),
        )
        color = elem.get("color", "#000000")
        align = elem.get("align", "left")

        # Calculate text position based on alignment
        if align == "center":
            tx = x + w / 2
            anchor = "mm"
            ty = y + h / 2
        elif align == "right":
            tx = x + w
            anchor = "rm"
            ty = y + h / 2
        else:
            tx = x
            anchor = "lm"
            ty = y + h / 2

        try:
            draw.text((tx, ty), content, fill=color, font=font, anchor=anchor)
        except (TypeError, ValueError):
            # Fallback without anchor for older Pillow
            draw.text((x, y), content, fill=color, font=font)

    def _render_rect(self, draw, elem, x, y, w, h):
        fill = elem.get("fill_color", "#FFFFFF")
        outline = elem.get("border_color", "#000000")
        border_w = elem.get("border_width", 1)
        radius = elem.get("corner_radius", 0)

        if radius > 0:
            try:
                draw.rounded_rectangle(
                    [x, y, x + w, y + h],
                    radius=radius,
                    fill=fill,
                    outline=outline,
                    width=border_w,
                )
            except AttributeError:
                draw.rectangle([x, y, x + w, y + h],
                               fill=fill, outline=outline, width=border_w)
        else:
            draw.rectangle([x, y, x + w, y + h],
                           fill=fill, outline=outline, width=border_w)

    def _render_line(self, draw, elem, x, y, w, h):
        color = elem.get("color", "#000000")
        thickness = max(1, elem.get("thickness", 1))
        orientation = elem.get("orientation", "horizontal")

        if orientation == "horizontal":
            mid_y = y + h / 2
            draw.line([(x, mid_y), (x + w, mid_y)],
                      fill=color, width=thickness)
        else:
            mid_x = x + w / 2
            draw.line([(mid_x, y), (mid_x, y + h)],
                      fill=color, width=thickness)

    def _render_image(self, img, elem, x, y, w, h):
        src = elem.get("src", "")
        if not src or not os.path.exists(src):
            # Draw placeholder
            draw = ImageDraw.Draw(img)
            draw.rectangle([x, y, x + w, y + h],
                           fill="#f0f0f0", outline="#cccccc")
            return
        try:
            source = Image.open(src)
            maintain_aspect = elem.get("maintain_aspect", True)
            target_w, target_h = int(w), int(h)

            if maintain_aspect:
                source.thumbnail((target_w, target_h), Image.LANCZOS)
                # Center within the element area
                paste_x = int(x + (w - source.width) / 2)
                paste_y = int(y + (h - source.height) / 2)
            else:
                source = source.resize((target_w, target_h), Image.LANCZOS)
                paste_x, paste_y = int(x), int(y)

            if source.mode == "RGBA":
                img.paste(source, (paste_x, paste_y), source)
            else:
                img.paste(source, (paste_x, paste_y))
        except Exception:
            draw = ImageDraw.Draw(img)
            draw.rectangle([x, y, x + w, y + h],
                           fill="#f0f0f0", outline="#cccccc")

    def _render_qr(self, img, elem, x, y, w, h, variables):
        content = self._substitute_vars(elem.get("content", ""), variables)
        size = int(min(w, h))

        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=max(1, size // 21),
                border=1,
            )
            qr.add_data(content)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((size, size), Image.NEAREST)
            # Center within element area
            paste_x = int(x + (w - size) / 2)
            paste_y = int(y + (h - size) / 2)
            img.paste(qr_img, (paste_x, paste_y))
        except ImportError:
            # qrcode package not installed — draw placeholder
            draw = ImageDraw.Draw(img)
            draw.rectangle([x, y, x + size, y + size],
                           fill="#FFFFFF", outline="#000000")
            draw.text((x + 4, y + 4), "QR", fill="#000000")
