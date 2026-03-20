"""
Papiro - Label Designer Canvas Engine
Interactive canvas with drag & drop, snap guides, and element manipulation.
"""

import tkinter as tk
from tkinter import simpledialog
from src.modules.designer.elements import (
    Element, TextElement, ImageElement, RectElement, LineElement, QRElement
)


class DesignerCanvas:
    """Interactive label designer canvas with snap guides."""

    SCALE = 10  # pixels per mm
    GRID_STEP_MM = 2
    SNAP_THRESHOLD_PX = 5
    HANDLE_SIZE = 6
    MARGIN_MM = 2  # snap margin from edges

    def __init__(self, parent_frame, width_mm=62, height_mm=29):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.elements: list[Element] = []
        self.selected_element: Element | None = None
        self.on_element_selected = None  # callback(element_or_None)

        # Drag state
        self._drag_data = None
        self._resize_data = None
        self._placement_class = None  # element class awaiting placement click

        # Canvas dimensions in pixels (add padding around label)
        self._pad = 30  # padding around the label area
        canvas_w = int(self.width_mm * self.SCALE + self._pad * 2)
        canvas_h = int(self.height_mm * self.SCALE + self._pad * 2)

        self.canvas = tk.Canvas(
            parent_frame,
            width=canvas_w,
            height=canvas_h,
            bg="#2a2a3e",
            highlightthickness=0,
        )
        self.canvas.pack(expand=True, fill="both")

        # Bind events
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Delete>", self._on_delete)
        self.canvas.bind("<BackSpace>", self._on_delete)
        self.canvas.bind("<Button-2>", self._on_right_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.focus_set()

        self._redraw()

    # --- Coordinate conversion ---

    def _mm_to_canvas(self, x_mm, y_mm):
        """Convert mm coords to canvas pixel coords."""
        return (
            self._pad + x_mm * self.SCALE,
            self._pad + y_mm * self.SCALE,
        )

    def _canvas_to_mm(self, cx, cy):
        """Convert canvas pixel coords to mm coords."""
        return (
            (cx - self._pad) / self.SCALE,
            (cy - self._pad) / self.SCALE,
        )

    # --- Drawing ---

    def _redraw(self):
        """Full redraw of the canvas."""
        self.canvas.delete("all")
        self._draw_label_background()
        self._draw_grid()
        self._draw_elements()
        if self.selected_element:
            self._draw_selection(self.selected_element)

    def _draw_label_background(self):
        """Draw the white label area."""
        x0, y0 = self._mm_to_canvas(0, 0)
        x1, y1 = self._mm_to_canvas(self.width_mm, self.height_mm)
        # Drop shadow
        self.canvas.create_rectangle(
            x0 + 3, y0 + 3, x1 + 3, y1 + 3,
            fill="#111122", outline="", tags="bg"
        )
        # Label
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#FFFFFF", outline="#444466", width=1, tags="bg"
        )

    def _draw_grid(self):
        """Draw subtle grid dots every GRID_STEP_MM."""
        for gx in self._frange(0, self.width_mm, self.GRID_STEP_MM):
            for gy in self._frange(0, self.height_mm, self.GRID_STEP_MM):
                cx, cy = self._mm_to_canvas(gx, gy)
                self.canvas.create_oval(
                    cx - 0.5, cy - 0.5, cx + 0.5, cy + 0.5,
                    fill="#cccccc", outline="", tags="grid"
                )

    def _draw_elements(self):
        """Draw all elements sorted by z_index."""
        sorted_elems = sorted(self.elements, key=lambda e: e.z_index)
        for elem in sorted_elems:
            self._draw_element(elem)

    def _draw_element(self, elem):
        """Draw a single element on the canvas."""
        x0, y0 = self._mm_to_canvas(elem.x_mm, elem.y_mm)
        x1, y1 = self._mm_to_canvas(
            elem.x_mm + elem.width_mm,
            elem.y_mm + elem.height_mm
        )
        tag = f"elem_{elem.id}"

        if isinstance(elem, TextElement):
            self._draw_text_element(elem, x0, y0, x1, y1, tag)
        elif isinstance(elem, ImageElement):
            self._draw_image_element(elem, x0, y0, x1, y1, tag)
        elif isinstance(elem, RectElement):
            self._draw_rect_element(elem, x0, y0, x1, y1, tag)
        elif isinstance(elem, LineElement):
            self._draw_line_element(elem, x0, y0, x1, y1, tag)
        elif isinstance(elem, QRElement):
            self._draw_qr_element(elem, x0, y0, x1, y1, tag)

    def _draw_text_element(self, elem, x0, y0, x1, y1, tag):
        # Background for visibility
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="", outline="#dddddd", dash=(2, 2), tags=tag
        )
        # Text
        anchor_map = {"left": "w", "center": "center", "right": "e"}
        anchor = anchor_map.get(elem.align, "w")
        if elem.align == "left":
            tx = x0 + 2
        elif elem.align == "right":
            tx = x1 - 2
        else:
            tx = (x0 + x1) / 2
        ty = (y0 + y1) / 2

        font_weight = "bold" if elem.font_weight == "bold" else "normal"
        font_spec = (elem.font_family, max(8, int(elem.font_size * self.SCALE / 10)), font_weight)

        display_text = elem.content
        # Truncate if too long for canvas display
        if len(display_text) > 40:
            display_text = display_text[:37] + "..."

        self.canvas.create_text(
            tx, ty,
            text=display_text,
            font=font_spec,
            fill=elem.color,
            anchor=anchor,
            tags=tag,
            width=max(1, x1 - x0 - 4),
        )

    def _draw_image_element(self, elem, x0, y0, x1, y1, tag):
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#f0f0f0", outline="#999999", tags=tag
        )
        # Image icon placeholder
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.canvas.create_text(
            cx, cy,
            text="IMG" if not elem.src else elem.src.split("/")[-1][:10],
            font=("Helvetica", 9),
            fill="#666666",
            tags=tag,
        )

    def _draw_rect_element(self, elem, x0, y0, x1, y1, tag):
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill=elem.fill_color,
            outline=elem.border_color,
            width=elem.border_width,
            tags=tag,
        )

    def _draw_line_element(self, elem, x0, y0, x1, y1, tag):
        if elem.orientation == "horizontal":
            mid_y = (y0 + y1) / 2
            self.canvas.create_line(
                x0, mid_y, x1, mid_y,
                fill=elem.color,
                width=max(1, elem.thickness),
                tags=tag,
            )
        else:
            mid_x = (x0 + x1) / 2
            self.canvas.create_line(
                mid_x, y0, mid_x, y1,
                fill=elem.color,
                width=max(1, elem.thickness),
                tags=tag,
            )

    def _draw_qr_element(self, elem, x0, y0, x1, y1, tag):
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#FFFFFF", outline="#000000", width=1, tags=tag
        )
        # QR placeholder pattern
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        size = min(x1 - x0, y1 - y0)
        s = size * 0.3
        # Corner squares (simplified QR look)
        for ox, oy in [(-s, -s), (s, -s), (-s, s)]:
            self.canvas.create_rectangle(
                cx + ox - 3, cy + oy - 3,
                cx + ox + 3, cy + oy + 3,
                fill="#000000", outline="", tags=tag
            )
        self.canvas.create_text(
            cx, cy + s * 0.5,
            text="QR", font=("Helvetica", 7), fill="#888888", tags=tag
        )

    def _draw_selection(self, elem):
        """Draw selection border and resize handles."""
        x0, y0 = self._mm_to_canvas(elem.x_mm, elem.y_mm)
        x1, y1 = self._mm_to_canvas(
            elem.x_mm + elem.width_mm,
            elem.y_mm + elem.height_mm
        )
        # Selection border
        self.canvas.create_rectangle(
            x0 - 1, y0 - 1, x1 + 1, y1 + 1,
            outline="#0f7dff", width=2, dash=(4, 2), tags="selection"
        )
        # Resize handles at corners
        hs = self.HANDLE_SIZE
        for hx, hy in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
            self.canvas.create_rectangle(
                hx - hs / 2, hy - hs / 2,
                hx + hs / 2, hy + hs / 2,
                fill="#0f7dff", outline="#FFFFFF", width=1, tags="handle"
            )

    def _draw_snap_guides(self, guides):
        """Draw cyan snap guide lines."""
        self.canvas.delete("snap_guide")
        for guide in guides:
            gtype, pos = guide
            if gtype == "vertical":
                cx = self._pad + pos * self.SCALE
                self.canvas.create_line(
                    cx, self._pad,
                    cx, self._pad + self.height_mm * self.SCALE,
                    fill="#00e5ff", dash=(4, 4), width=1, tags="snap_guide"
                )
            elif gtype == "horizontal":
                cy = self._pad + pos * self.SCALE
                self.canvas.create_line(
                    self._pad, cy,
                    self._pad + self.width_mm * self.SCALE, cy,
                    fill="#00e5ff", dash=(4, 4), width=1, tags="snap_guide"
                )

    # --- Snap logic ---

    def _compute_snap(self, elem, tentative_x, tentative_y):
        """
        Compute snapped position and active guides for an element.
        Returns (snapped_x_mm, snapped_y_mm, guides_list).
        """
        snap_px = self.SNAP_THRESHOLD_PX / self.SCALE  # threshold in mm
        guides = []

        ex_left = tentative_x
        ex_right = tentative_x + elem.width_mm
        ex_cx = tentative_x + elem.width_mm / 2
        ey_top = tentative_y
        ey_bottom = tentative_y + elem.height_mm
        ey_cy = tentative_y + elem.height_mm / 2

        snapped_x = tentative_x
        snapped_y = tentative_y
        best_dx = snap_px + 1
        best_dy = snap_px + 1

        # -- Vertical snap targets (x positions) --
        v_targets = [
            0,                          # left edge
            self.MARGIN_MM,             # left margin
            self.width_mm / 2,          # center
            self.width_mm - self.MARGIN_MM,  # right margin
            self.width_mm,              # right edge
        ]
        # Add other elements' edges and centers
        for other in self.elements:
            if other.id == elem.id:
                continue
            v_targets.extend([
                other.x_mm,
                other.x_mm + other.width_mm / 2,
                other.x_mm + other.width_mm,
            ])

        # Check left, center, right of dragged elem against targets
        for target in v_targets:
            for edge, offset in [(ex_left, 0), (ex_cx, elem.width_mm / 2),
                                 (ex_right, elem.width_mm)]:
                dx = abs(edge - target)
                if dx < snap_px and dx < best_dx:
                    best_dx = dx
                    snapped_x = target - offset
                    guides.append(("vertical", target))

        # -- Horizontal snap targets (y positions) --
        h_targets = [
            0,
            self.MARGIN_MM,
            self.height_mm / 2,
            self.height_mm - self.MARGIN_MM,
            self.height_mm,
        ]
        for other in self.elements:
            if other.id == elem.id:
                continue
            h_targets.extend([
                other.y_mm,
                other.y_mm + other.height_mm / 2,
                other.y_mm + other.height_mm,
            ])

        for target in h_targets:
            for edge, offset in [(ey_top, 0), (ey_cy, elem.height_mm / 2),
                                 (ey_bottom, elem.height_mm)]:
                dy = abs(edge - target)
                if dy < snap_px and dy < best_dy:
                    best_dy = dy
                    snapped_y = target - offset
                    guides.append(("horizontal", target))

        return snapped_x, snapped_y, guides

    # --- Event handlers ---

    def _on_click(self, event):
        # If in placement mode, place a new element
        if self._placement_class:
            mx, my = self._canvas_to_mm(event.x, event.y)
            # Clamp to label area
            if 0 <= mx <= self.width_mm and 0 <= my <= self.height_mm:
                elem = self._placement_class(x_mm=mx, y_mm=my)
                # Clamp so element stays within label
                elem.x_mm = min(elem.x_mm, self.width_mm - elem.width_mm)
                elem.y_mm = min(elem.y_mm, self.height_mm - elem.height_mm)
                elem.x_mm = max(0, elem.x_mm)
                elem.y_mm = max(0, elem.y_mm)
                self.add_element(elem)
                self._select_element(elem)
            self._placement_class = None
            self.canvas.config(cursor="")
            return

        # Check resize handles first
        if self.selected_element:
            handle = self._hit_handle(event.x, event.y, self.selected_element)
            if handle:
                self._resize_data = {
                    "handle": handle,
                    "start_x": event.x,
                    "start_y": event.y,
                    "orig_x": self.selected_element.x_mm,
                    "orig_y": self.selected_element.y_mm,
                    "orig_w": self.selected_element.width_mm,
                    "orig_h": self.selected_element.height_mm,
                }
                return

        # Check if clicking on an element (top-most first)
        clicked = self._element_at(event.x, event.y)
        if clicked:
            self._select_element(clicked)
            self._drag_data = {
                "start_x": event.x,
                "start_y": event.y,
                "orig_x_mm": clicked.x_mm,
                "orig_y_mm": clicked.y_mm,
            }
        else:
            self._select_element(None)

    def _on_drag(self, event):
        # Resize
        if self._resize_data and self.selected_element:
            self._handle_resize(event)
            return

        # Drag move
        if self._drag_data and self.selected_element:
            dx_px = event.x - self._drag_data["start_x"]
            dy_px = event.y - self._drag_data["start_y"]
            new_x = self._drag_data["orig_x_mm"] + dx_px / self.SCALE
            new_y = self._drag_data["orig_y_mm"] + dy_px / self.SCALE

            # Snap
            snapped_x, snapped_y, guides = self._compute_snap(
                self.selected_element, new_x, new_y
            )

            self.selected_element.x_mm = snapped_x
            self.selected_element.y_mm = snapped_y

            self._redraw()
            self._draw_snap_guides(guides)

            if self.on_element_selected:
                self.on_element_selected(self.selected_element)

    def _on_release(self, event):
        self._drag_data = None
        self._resize_data = None
        self.canvas.delete("snap_guide")
        self._redraw()

    def _on_double_click(self, event):
        elem = self._element_at(event.x, event.y)
        if isinstance(elem, TextElement):
            new_text = simpledialog.askstring(
                "Editar texto",
                "Contenido:",
                initialvalue=elem.content,
                parent=self.canvas.winfo_toplevel(),
            )
            if new_text is not None:
                elem.content = new_text
                self._redraw()
                if self.on_element_selected:
                    self.on_element_selected(elem)

    def _on_delete(self, event):
        if self.selected_element:
            self.remove_element(self.selected_element)
            self._select_element(None)

    def _on_right_click(self, event):
        elem = self._element_at(event.x, event.y)
        if not elem:
            return
        self._select_element(elem)

        menu = tk.Menu(self.canvas, tearoff=0)
        menu.add_command(label="Duplicar", command=lambda: self._ctx_duplicate(elem))
        menu.add_command(label="Eliminar", command=lambda: self._ctx_delete(elem))
        menu.add_separator()
        menu.add_command(label="Traer al frente", command=lambda: self._ctx_bring_front(elem))
        menu.add_command(label="Enviar atrás", command=lambda: self._ctx_send_back(elem))
        menu.tk_popup(event.x_root, event.y_root)

    def _on_resize(self, event):
        """Handle canvas widget resize."""
        self._redraw()

    # --- Context menu actions ---

    def _ctx_duplicate(self, elem):
        new_elem = elem.duplicate()
        self.add_element(new_elem)
        self._select_element(new_elem)

    def _ctx_delete(self, elem):
        self.remove_element(elem)
        self._select_element(None)

    def _ctx_bring_front(self, elem):
        max_z = max((e.z_index for e in self.elements), default=0)
        elem.z_index = max_z + 1
        self._redraw()

    def _ctx_send_back(self, elem):
        min_z = min((e.z_index for e in self.elements), default=0)
        elem.z_index = min_z - 1
        self._redraw()

    # --- Resize handling ---

    def _handle_resize(self, event):
        rd = self._resize_data
        elem = self.selected_element
        handle = rd["handle"]

        dx_mm = (event.x - rd["start_x"]) / self.SCALE
        dy_mm = (event.y - rd["start_y"]) / self.SCALE

        ox, oy, ow, oh = rd["orig_x"], rd["orig_y"], rd["orig_w"], rd["orig_h"]
        min_size = 2  # minimum 2mm

        if handle == "br":
            elem.width_mm = max(min_size, ow + dx_mm)
            elem.height_mm = max(min_size, oh + dy_mm)
        elif handle == "bl":
            new_w = max(min_size, ow - dx_mm)
            elem.x_mm = ox + ow - new_w
            elem.width_mm = new_w
            elem.height_mm = max(min_size, oh + dy_mm)
        elif handle == "tr":
            elem.width_mm = max(min_size, ow + dx_mm)
            new_h = max(min_size, oh - dy_mm)
            elem.y_mm = oy + oh - new_h
            elem.height_mm = new_h
        elif handle == "tl":
            new_w = max(min_size, ow - dx_mm)
            new_h = max(min_size, oh - dy_mm)
            elem.x_mm = ox + ow - new_w
            elem.y_mm = oy + oh - new_h
            elem.width_mm = new_w
            elem.height_mm = new_h

        # Keep QR square
        if isinstance(elem, QRElement):
            s = max(elem.width_mm, elem.height_mm)
            elem.width_mm = s
            elem.height_mm = s

        self._redraw()
        if self.on_element_selected:
            self.on_element_selected(elem)

    def _hit_handle(self, cx, cy, elem):
        """Check if click hits a resize handle. Returns handle id or None."""
        x0, y0 = self._mm_to_canvas(elem.x_mm, elem.y_mm)
        x1, y1 = self._mm_to_canvas(
            elem.x_mm + elem.width_mm,
            elem.y_mm + elem.height_mm
        )
        hs = self.HANDLE_SIZE
        handles = {
            "tl": (x0, y0), "tr": (x1, y0),
            "bl": (x0, y1), "br": (x1, y1),
        }
        for hid, (hx, hy) in handles.items():
            if abs(cx - hx) <= hs and abs(cy - hy) <= hs:
                return hid
        return None

    # --- Hit testing ---

    def _element_at(self, cx, cy):
        """Find top-most element at canvas coordinates."""
        mx, my = self._canvas_to_mm(cx, cy)
        # Search in reverse z_index order (top first)
        sorted_elems = sorted(self.elements, key=lambda e: e.z_index, reverse=True)
        for elem in sorted_elems:
            if elem.contains_point_mm(mx, my):
                return elem
        return None

    # --- Selection ---

    def _select_element(self, elem):
        if self.selected_element:
            self.selected_element.selected = False
        self.selected_element = elem
        if elem:
            elem.selected = True
        self._redraw()
        if self.on_element_selected:
            self.on_element_selected(elem)

    # --- Public API ---

    def add_element(self, elem):
        """Add an element to the canvas."""
        if not any(e.id == elem.id for e in self.elements):
            max_z = max((e.z_index for e in self.elements), default=0)
            elem.z_index = max_z + 1
            self.elements.append(elem)
        self._redraw()

    def remove_element(self, elem):
        """Remove an element from the canvas."""
        self.elements = [e for e in self.elements if e.id != elem.id]
        if self.selected_element and self.selected_element.id == elem.id:
            self.selected_element = None
        self._redraw()

    def get_elements(self):
        """Return all elements."""
        return list(self.elements)

    def clear(self):
        """Remove all elements."""
        self.elements.clear()
        self.selected_element = None
        self._redraw()

    def set_label_size(self, width_mm, height_mm):
        """Update label dimensions and redraw."""
        self.width_mm = width_mm
        self.height_mm = height_mm
        canvas_w = int(self.width_mm * self.SCALE + self._pad * 2)
        canvas_h = int(self.height_mm * self.SCALE + self._pad * 2)
        self.canvas.config(width=canvas_w, height=canvas_h)
        self._redraw()

    def start_placement(self, element_class):
        """Enter placement mode: next click on canvas creates an element."""
        self._placement_class = element_class
        self.canvas.config(cursor="crosshair")

    def update_element(self, elem):
        """Re-render after external property change."""
        self._redraw()

    def load_elements(self, elements):
        """Replace all elements with a new list."""
        self.elements = list(elements)
        self.selected_element = None
        self._redraw()

    # --- Utility ---

    @staticmethod
    def _frange(start, stop, step):
        vals = []
        v = start
        while v <= stop + 0.001:
            vals.append(round(v, 2))
            v += step
        return vals
