"""
Papiro - Label Designer Elements
Draggable element types for the label canvas editor.
"""

import uuid
import copy


class Element:
    """Base class for all canvas elements."""

    element_type = "base"

    def __init__(self, x_mm=0, y_mm=0, width_mm=20, height_mm=10):
        self.id = str(uuid.uuid4())[:8]
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.selected = False
        self.z_index = 0

    def to_dict(self):
        return {
            "type": self.element_type,
            "id": self.id,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "z_index": self.z_index,
        }

    @classmethod
    def from_dict(cls, data):
        element_type = data.get("type", "base")
        type_map = {
            "text": TextElement,
            "image": ImageElement,
            "rect": RectElement,
            "line": LineElement,
            "qr": QRElement,
        }
        klass = type_map.get(element_type, cls)
        obj = klass.__new__(klass)
        obj._load_base(data)
        obj._load_specific(data)
        return obj

    def _load_base(self, data):
        self.id = data.get("id", str(uuid.uuid4())[:8])
        self.x_mm = data.get("x_mm", 0)
        self.y_mm = data.get("y_mm", 0)
        self.width_mm = data.get("width_mm", 20)
        self.height_mm = data.get("height_mm", 10)
        self.z_index = data.get("z_index", 0)
        self.selected = False

    def _load_specific(self, data):
        """Override in subclasses to load type-specific fields."""
        pass

    def duplicate(self):
        """Create a copy with a new id, offset slightly."""
        d = self.to_dict()
        d["id"] = str(uuid.uuid4())[:8]
        d["x_mm"] = d["x_mm"] + 2
        d["y_mm"] = d["y_mm"] + 2
        return Element.from_dict(d)

    def contains_point_mm(self, px_mm, py_mm):
        return (self.x_mm <= px_mm <= self.x_mm + self.width_mm and
                self.y_mm <= py_mm <= self.y_mm + self.height_mm)


class TextElement(Element):
    """Text element with variable support (e.g. {{producto}})."""

    element_type = "text"

    def __init__(self, x_mm=0, y_mm=0, width_mm=30, height_mm=6,
                 content="Texto", font_family="Helvetica", font_size=12,
                 font_weight="normal", color="#000000", align="left"):
        super().__init__(x_mm, y_mm, width_mm, height_mm)
        self.content = content
        self.font_family = font_family
        self.font_size = font_size
        self.font_weight = font_weight  # "bold" or "normal"
        self.color = color
        self.align = align  # "left", "center", "right"

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "content": self.content,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "color": self.color,
            "align": self.align,
        })
        return d

    def _load_specific(self, data):
        self.content = data.get("content", "Texto")
        self.font_family = data.get("font_family", "Helvetica")
        self.font_size = data.get("font_size", 12)
        self.font_weight = data.get("font_weight", "normal")
        self.color = data.get("color", "#000000")
        self.align = data.get("align", "left")


class ImageElement(Element):
    """Image element loaded from file path."""

    element_type = "image"

    def __init__(self, x_mm=0, y_mm=0, width_mm=15, height_mm=15,
                 src="", maintain_aspect=True):
        super().__init__(x_mm, y_mm, width_mm, height_mm)
        self.src = src
        self.maintain_aspect = maintain_aspect

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "src": self.src,
            "maintain_aspect": self.maintain_aspect,
        })
        return d

    def _load_specific(self, data):
        self.src = data.get("src", "")
        self.maintain_aspect = data.get("maintain_aspect", True)


class RectElement(Element):
    """Rectangle / box element."""

    element_type = "rect"

    def __init__(self, x_mm=0, y_mm=0, width_mm=20, height_mm=10,
                 fill_color="#FFFFFF", border_color="#000000",
                 border_width=1, corner_radius=0):
        super().__init__(x_mm, y_mm, width_mm, height_mm)
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width
        self.corner_radius = corner_radius

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "fill_color": self.fill_color,
            "border_color": self.border_color,
            "border_width": self.border_width,
            "corner_radius": self.corner_radius,
        })
        return d

    def _load_specific(self, data):
        self.fill_color = data.get("fill_color", "#FFFFFF")
        self.border_color = data.get("border_color", "#000000")
        self.border_width = data.get("border_width", 1)
        self.corner_radius = data.get("corner_radius", 0)


class LineElement(Element):
    """Horizontal or vertical line element."""

    element_type = "line"

    def __init__(self, x_mm=0, y_mm=0, width_mm=20, height_mm=0.5,
                 color="#000000", thickness=1, orientation="horizontal"):
        super().__init__(x_mm, y_mm, width_mm, height_mm)
        self.color = color
        self.thickness = thickness
        self.orientation = orientation  # "horizontal" or "vertical"

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "color": self.color,
            "thickness": self.thickness,
            "orientation": self.orientation,
        })
        return d

    def _load_specific(self, data):
        self.color = data.get("color", "#000000")
        self.thickness = data.get("thickness", 1)
        self.orientation = data.get("orientation", "horizontal")


class QRElement(Element):
    """QR code element with variable support."""

    element_type = "qr"

    def __init__(self, x_mm=0, y_mm=0, width_mm=15, height_mm=15,
                 content="{{producto}} - {{fecha}}"):
        super().__init__(x_mm, y_mm, width_mm, height_mm)
        self.content = content
        # Keep it square
        self.height_mm = self.width_mm

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "content": self.content,
        })
        return d

    def _load_specific(self, data):
        self.content = data.get("content", "{{producto}}")

    @property
    def size_mm(self):
        return self.width_mm


# Available template variables
TEMPLATE_VARIABLES = [
    ("{{producto}}", "Nombre del producto"),
    ("{{nombre_paciente}}", "Nombre del paciente"),
    ("{{fecha}}", "Fecha actual"),
    ("{{peso}}", "Peso / cantidad"),
    ("{{cepa}}", "Cepa / variedad"),
    ("{{lote}}", "Número de lote"),
    ("{{thc}}", "Contenido THC"),
    ("{{cbd}}", "Contenido CBD"),
]
