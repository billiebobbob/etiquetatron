"""
Papiro - Label Designer View
Main UI for the drag & drop label template editor.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser

import customtkinter as ctk
from PIL import Image, ImageTk

from src.config import (
    BG_DARK, BG_CARD, BG_CARD_LIGHT, ACCENT_BLUE, ACCENT_GREEN,
    ACCENT_ORANGE, ACCENT_CYAN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER_COLOR,
    TAPE_WIDTH_MM, get_templates_path,
)
from src.modules.designer.canvas_engine import DesignerCanvas
from src.modules.designer.elements import (
    TextElement, ImageElement, RectElement, LineElement, QRElement,
    TEMPLATE_VARIABLES,
)
from src.modules.designer.template_store import TemplateStore


class DesignerView(ctk.CTkFrame):
    """Label Designer — drag & drop editor for product label templates."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.store = TemplateStore(get_templates_path())
        self.designer_canvas = None
        self._current_template_name = ""
        self._gallery_images = []  # keep references to avoid GC

        self._build_ui()
        self._refresh_gallery()

    # ------------------------------------------------------------------ #
    #  UI Construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # Main vertical layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()
        self._build_main_area()
        self._build_gallery()

    # --- Toolbar ---

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color=BG_CARD, height=48,
                               corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        toolbar.grid_columnconfigure(10, weight=1)

        # Element buttons
        btn_style = {
            "height": 32, "width": 80, "corner_radius": 6,
            "font": ("Helvetica", 12), "fg_color": BG_CARD_LIGHT,
            "hover_color": ACCENT_BLUE, "text_color": TEXT_PRIMARY,
        }

        elements = [
            ("Texto", TextElement),
            ("Imagen", ImageElement),
            ("Rect", RectElement),
            ("Línea", LineElement),
            ("QR", QRElement),
        ]

        for i, (label, elem_cls) in enumerate(elements):
            btn = ctk.CTkButton(
                toolbar, text=label,
                command=lambda c=elem_cls: self._start_placement(c),
                **btn_style,
            )
            btn.grid(row=0, column=i, padx=(8 if i == 0 else 2, 2), pady=8)

        # Separator
        sep = ctk.CTkFrame(toolbar, fg_color=BORDER_COLOR, width=2)
        sep.grid(row=0, column=5, padx=8, pady=6, sticky="ns")

        # Template name
        ctk.CTkLabel(toolbar, text="Plantilla:", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 12)).grid(row=0, column=6, padx=(8, 4), pady=8)
        self._name_entry = ctk.CTkEntry(
            toolbar, width=160, height=32,
            fg_color=BG_DARK, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text="Nombre...",
        )
        self._name_entry.grid(row=0, column=7, padx=2, pady=8)

        # Action buttons
        action_style = {
            "height": 32, "width": 70, "corner_radius": 6,
            "font": ("Helvetica", 12, "bold"),
        }

        ctk.CTkButton(
            toolbar, text="Guardar", fg_color=ACCENT_GREEN,
            hover_color="#00a344", text_color="#FFFFFF",
            command=self._save_template, **action_style,
        ).grid(row=0, column=8, padx=2, pady=8)

        ctk.CTkButton(
            toolbar, text="Nuevo", fg_color=ACCENT_BLUE,
            hover_color="#0b5cbf", text_color="#FFFFFF",
            command=self._new_template, **action_style,
        ).grid(row=0, column=9, padx=2, pady=8)

        ctk.CTkButton(
            toolbar, text="Vista previa", fg_color=ACCENT_ORANGE,
            hover_color="#cc5700", text_color="#FFFFFF",
            command=self._show_preview, width=100, height=32,
            corner_radius=6, font=("Helvetica", 12, "bold"),
        ).grid(row=0, column=11, padx=(2, 8), pady=8)

    # --- Main area: canvas + properties ---

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)

        # Canvas frame
        canvas_frame = ctk.CTkFrame(main, fg_color=BG_DARK, corner_radius=8)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Label dimensions row
        dims_frame = ctk.CTkFrame(canvas_frame, fg_color="transparent")
        dims_frame.pack(fill="x", padx=8, pady=(8, 0))

        ctk.CTkLabel(dims_frame, text="Ancho:", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11)).pack(side="left", padx=(0, 4))
        self._width_label = ctk.CTkLabel(
            dims_frame, text=f"{TAPE_WIDTH_MM}mm (fijo)",
            text_color=TEXT_MUTED, font=("Helvetica", 11),
        )
        self._width_label.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(dims_frame, text="Alto:", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11)).pack(side="left", padx=(0, 4))
        self._height_entry = ctk.CTkEntry(
            dims_frame, width=60, height=26,
            fg_color=BG_CARD, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
        )
        self._height_entry.pack(side="left", padx=(0, 4))
        self._height_entry.insert(0, "29")
        ctk.CTkLabel(dims_frame, text="mm", text_color=TEXT_MUTED,
                     font=("Helvetica", 11)).pack(side="left")

        ctk.CTkButton(
            dims_frame, text="Aplicar", width=60, height=26,
            fg_color=BG_CARD_LIGHT, hover_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY, font=("Helvetica", 11),
            command=self._apply_dimensions,
        ).pack(side="left", padx=(8, 0))

        # Canvas container (tk.Frame because DesignerCanvas uses tk.Canvas)
        self._canvas_container = tk.Frame(canvas_frame, bg="#1a1a2e")
        self._canvas_container.pack(expand=True, fill="both", padx=8, pady=8)

        self.designer_canvas = DesignerCanvas(
            self._canvas_container,
            width_mm=TAPE_WIDTH_MM,
            height_mm=29,
        )
        self.designer_canvas.on_element_selected = self._on_element_selected

        # Properties panel
        self._build_properties_panel(main)

    # --- Properties panel ---

    def _build_properties_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color=BG_CARD, width=260,
                             corner_radius=8)
        panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        panel.grid_propagate(False)

        self._props_panel = panel

        header = ctk.CTkLabel(
            panel, text="Propiedades", font=("Helvetica", 14, "bold"),
            text_color=TEXT_PRIMARY,
        )
        header.pack(fill="x", padx=12, pady=(12, 4))

        self._props_hint = ctk.CTkLabel(
            panel, text="Selecciona un elemento\nen el canvas",
            text_color=TEXT_MUTED, font=("Helvetica", 11),
        )
        self._props_hint.pack(expand=True)

        # Scrollable area for properties
        self._props_scroll = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", width=236,
        )
        self._props_scroll.pack(fill="both", expand=True, padx=4, pady=4)
        self._props_scroll.pack_forget()  # hidden initially

        self._prop_widgets = {}

    def _on_element_selected(self, elem):
        """Callback when an element is selected/deselected on canvas."""
        # Clear existing property widgets
        for widget in self._props_scroll.winfo_children():
            widget.destroy()
        self._prop_widgets.clear()

        if elem is None:
            self._props_scroll.pack_forget()
            self._props_hint.pack(expand=True)
            return

        self._props_hint.pack_forget()
        self._props_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Position fields (all elements)
        self._add_prop_row("X (mm)", "x_mm", elem.x_mm, elem)
        self._add_prop_row("Y (mm)", "y_mm", elem.y_mm, elem)
        self._add_prop_row("Ancho (mm)", "width_mm", elem.width_mm, elem)
        self._add_prop_row("Alto (mm)", "height_mm", elem.height_mm, elem)

        # Type-specific fields
        if isinstance(elem, TextElement):
            self._add_text_props(elem)
        elif isinstance(elem, ImageElement):
            self._add_image_props(elem)
        elif isinstance(elem, RectElement):
            self._add_rect_props(elem)
        elif isinstance(elem, LineElement):
            self._add_line_props(elem)
        elif isinstance(elem, QRElement):
            self._add_qr_props(elem)

        # Delete button
        ctk.CTkButton(
            self._props_scroll, text="Eliminar elemento",
            fg_color=ACCENT_RED, hover_color="#cc1133",
            text_color="#FFFFFF", font=("Helvetica", 12, "bold"),
            height=32, command=lambda: self._delete_selected(elem),
        ).pack(fill="x", padx=8, pady=(16, 8))

    def _add_prop_row(self, label, attr, value, elem):
        """Add a numeric property row."""
        frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(frame, text=label, text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11), width=80, anchor="w"
                     ).pack(side="left")

        entry = ctk.CTkEntry(
            frame, width=80, height=26,
            fg_color=BG_DARK, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
        )
        entry.pack(side="right")
        entry.insert(0, str(round(value, 2)))
        entry.bind("<Return>", lambda e, a=attr, el=elem, en=entry:
                    self._update_num_prop(el, a, en))
        entry.bind("<FocusOut>", lambda e, a=attr, el=elem, en=entry:
                    self._update_num_prop(el, a, en))

        self._prop_widgets[attr] = entry

    def _add_text_props(self, elem):
        """Add text-specific property fields."""
        # Content
        frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(frame, text="Contenido", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11)).pack(anchor="w")

        content_entry = ctk.CTkEntry(
            frame, height=28, fg_color=BG_DARK,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
        )
        content_entry.pack(fill="x", pady=(2, 0))
        content_entry.insert(0, elem.content)
        content_entry.bind("<Return>", lambda e: self._update_text_content(
            elem, content_entry))
        content_entry.bind("<FocusOut>", lambda e: self._update_text_content(
            elem, content_entry))
        self._prop_widgets["content"] = content_entry

        # Variable helper dropdown
        var_frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        var_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(var_frame, text="Insertar variable:",
                     text_color=TEXT_MUTED, font=("Helvetica", 10)
                     ).pack(side="left")

        var_options = [v[0] for v in TEMPLATE_VARIABLES]
        var_dropdown = ctk.CTkOptionMenu(
            var_frame, values=var_options, width=140, height=26,
            fg_color=BG_CARD_LIGHT, button_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY, font=("Helvetica", 10),
            command=lambda v: self._insert_variable(v, content_entry, elem),
        )
        var_dropdown.pack(side="right")
        var_dropdown.set("{{producto}}")

        # Font family
        font_frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        font_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(font_frame, text="Fuente", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11), width=80, anchor="w"
                     ).pack(side="left")

        font_options = ["Helvetica", "Arial", "Courier", "Times"]
        font_menu = ctk.CTkOptionMenu(
            font_frame, values=font_options, width=120, height=26,
            fg_color=BG_CARD_LIGHT, button_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            command=lambda v: self._update_str_prop(elem, "font_family", v),
        )
        font_menu.pack(side="right")
        font_menu.set(elem.font_family)

        # Font size
        self._add_prop_row("Tamaño", "font_size", elem.font_size, elem)

        # Font weight
        weight_frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        weight_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(weight_frame, text="Peso", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11), width=80, anchor="w"
                     ).pack(side="left")

        weight_menu = ctk.CTkOptionMenu(
            weight_frame, values=["normal", "bold"], width=120, height=26,
            fg_color=BG_CARD_LIGHT, button_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            command=lambda v: self._update_str_prop(elem, "font_weight", v),
        )
        weight_menu.pack(side="right")
        weight_menu.set(elem.font_weight)

        # Align
        align_frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        align_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(align_frame, text="Alinear", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11), width=80, anchor="w"
                     ).pack(side="left")

        align_menu = ctk.CTkOptionMenu(
            align_frame, values=["left", "center", "right"],
            width=120, height=26,
            fg_color=BG_CARD_LIGHT, button_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            command=lambda v: self._update_str_prop(elem, "align", v),
        )
        align_menu.pack(side="right")
        align_menu.set(elem.align)

        # Color
        self._add_color_row("Color", "color", elem.color, elem)

    def _add_image_props(self, elem):
        """Add image-specific property fields."""
        frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(frame, text="Archivo", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11)).pack(anchor="w")

        src_frame = ctk.CTkFrame(frame, fg_color="transparent")
        src_frame.pack(fill="x", pady=2)

        src_entry = ctk.CTkEntry(
            src_frame, height=26, fg_color=BG_DARK,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
        )
        src_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        src_entry.insert(0, elem.src)
        src_entry.bind("<Return>", lambda e: self._update_image_src(
            elem, src_entry))

        ctk.CTkButton(
            src_frame, text="...", width=30, height=26,
            fg_color=BG_CARD_LIGHT, hover_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            command=lambda: self._browse_image(elem, src_entry),
        ).pack(side="right")

        # Maintain aspect
        aspect_var = ctk.BooleanVar(value=elem.maintain_aspect)
        ctk.CTkCheckBox(
            self._props_scroll, text="Mantener proporción",
            text_color=TEXT_SECONDARY, font=("Helvetica", 11),
            variable=aspect_var,
            fg_color=BG_CARD_LIGHT, hover_color=ACCENT_BLUE,
            command=lambda: self._update_bool_prop(
                elem, "maintain_aspect", aspect_var.get()),
        ).pack(fill="x", padx=8, pady=4)

    def _add_rect_props(self, elem):
        """Add rect-specific property fields."""
        self._add_color_row("Relleno", "fill_color", elem.fill_color, elem)
        self._add_color_row("Borde", "border_color", elem.border_color, elem)
        self._add_prop_row("Grosor borde", "border_width",
                           elem.border_width, elem)
        self._add_prop_row("Radio esquina", "corner_radius",
                           elem.corner_radius, elem)

    def _add_line_props(self, elem):
        """Add line-specific property fields."""
        self._add_color_row("Color", "color", elem.color, elem)
        self._add_prop_row("Grosor", "thickness", elem.thickness, elem)

        orient_frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        orient_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(orient_frame, text="Orientación",
                     text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11), width=80, anchor="w"
                     ).pack(side="left")

        orient_menu = ctk.CTkOptionMenu(
            orient_frame, values=["horizontal", "vertical"],
            width=120, height=26,
            fg_color=BG_CARD_LIGHT, button_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            command=lambda v: self._update_str_prop(elem, "orientation", v),
        )
        orient_menu.pack(side="right")
        orient_menu.set(elem.orientation)

    def _add_qr_props(self, elem):
        """Add QR-specific property fields."""
        frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(frame, text="Contenido QR", text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11)).pack(anchor="w")

        content_entry = ctk.CTkEntry(
            frame, height=28, fg_color=BG_DARK,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
        )
        content_entry.pack(fill="x", pady=(2, 0))
        content_entry.insert(0, elem.content)
        content_entry.bind("<Return>", lambda e: self._update_qr_content(
            elem, content_entry))
        content_entry.bind("<FocusOut>", lambda e: self._update_qr_content(
            elem, content_entry))

        # Variable helper
        var_frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        var_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(var_frame, text="Insertar variable:",
                     text_color=TEXT_MUTED, font=("Helvetica", 10)
                     ).pack(side="left")

        var_options = [v[0] for v in TEMPLATE_VARIABLES]
        var_dropdown = ctk.CTkOptionMenu(
            var_frame, values=var_options, width=140, height=26,
            fg_color=BG_CARD_LIGHT, button_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY, font=("Helvetica", 10),
            command=lambda v: self._insert_variable(v, content_entry, elem,
                                                     attr="content"),
        )
        var_dropdown.pack(side="right")
        var_dropdown.set("{{producto}}")

    def _add_color_row(self, label, attr, current_color, elem):
        """Add a color picker row."""
        frame = ctk.CTkFrame(self._props_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(frame, text=label, text_color=TEXT_SECONDARY,
                     font=("Helvetica", 11), width=80, anchor="w"
                     ).pack(side="left")

        color_btn = ctk.CTkButton(
            frame, text=current_color, width=100, height=26,
            fg_color=current_color, hover_color=current_color,
            text_color=self._contrast_text(current_color),
            font=("Helvetica", 10),
            command=lambda: self._pick_color(elem, attr, color_btn),
        )
        color_btn.pack(side="right")

    # ------------------------------------------------------------------ #
    #  Property update callbacks                                           #
    # ------------------------------------------------------------------ #

    def _update_num_prop(self, elem, attr, entry):
        try:
            val = float(entry.get())
            setattr(elem, attr, val)
            self.designer_canvas.update_element(elem)
        except ValueError:
            pass

    def _update_str_prop(self, elem, attr, value):
        setattr(elem, attr, value)
        self.designer_canvas.update_element(elem)

    def _update_bool_prop(self, elem, attr, value):
        setattr(elem, attr, value)
        self.designer_canvas.update_element(elem)

    def _update_text_content(self, elem, entry):
        elem.content = entry.get()
        self.designer_canvas.update_element(elem)

    def _update_qr_content(self, elem, entry):
        elem.content = entry.get()
        self.designer_canvas.update_element(elem)

    def _update_image_src(self, elem, entry):
        elem.src = entry.get()
        self.designer_canvas.update_element(elem)

    def _insert_variable(self, var, entry, elem, attr="content"):
        current = entry.get()
        try:
            cursor_pos = entry.index(tk.INSERT)
        except (AttributeError, tk.TclError):
            cursor_pos = len(current)
        new_text = current[:cursor_pos] + var + current[cursor_pos:]
        entry.delete(0, "end")
        entry.insert(0, new_text)
        setattr(elem, attr if attr else "content", new_text)
        self.designer_canvas.update_element(elem)

    def _pick_color(self, elem, attr, btn):
        color = colorchooser.askcolor(
            color=getattr(elem, attr, "#000000"),
            title="Elegir color",
        )
        if color[1]:
            setattr(elem, attr, color[1])
            btn.configure(
                text=color[1],
                fg_color=color[1],
                hover_color=color[1],
                text_color=self._contrast_text(color[1]),
            )
            self.designer_canvas.update_element(elem)

    def _browse_image(self, elem, entry):
        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("Todos", "*.*"),
            ],
        )
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)
            elem.src = path
            self.designer_canvas.update_element(elem)

    def _delete_selected(self, elem):
        self.designer_canvas.remove_element(elem)
        self._on_element_selected(None)

    # ------------------------------------------------------------------ #
    #  Canvas / toolbar actions                                            #
    # ------------------------------------------------------------------ #

    def _start_placement(self, elem_class):
        """Start element placement mode on the canvas."""
        self.designer_canvas.start_placement(elem_class)

    def _apply_dimensions(self):
        """Update label height from entry."""
        try:
            h = float(self._height_entry.get())
            if h < 10:
                h = 10
            if h > 500:
                h = 500
            self.designer_canvas.set_label_size(TAPE_WIDTH_MM, h)
        except ValueError:
            pass

    # ------------------------------------------------------------------ #
    #  Template operations                                                 #
    # ------------------------------------------------------------------ #

    def _save_template(self):
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showwarning("Papiro", "Ingresa un nombre para la plantilla.")
            return

        elements = self.designer_canvas.get_elements()
        self.store.save_template(
            name,
            self.designer_canvas.width_mm,
            self.designer_canvas.height_mm,
            elements,
        )
        self._current_template_name = name
        self._refresh_gallery()
        messagebox.showinfo("Papiro", f"Plantilla '{name}' guardada.")

    def _new_template(self):
        self.designer_canvas.clear()
        self._name_entry.delete(0, "end")
        self._height_entry.delete(0, "end")
        self._height_entry.insert(0, "29")
        self.designer_canvas.set_label_size(TAPE_WIDTH_MM, 29)
        self._current_template_name = ""
        self._on_element_selected(None)

    def _load_template(self, name):
        try:
            data = self.store.load_template(name)
        except FileNotFoundError:
            messagebox.showerror("Papiro", f"Plantilla '{name}' no encontrada.")
            return

        self._current_template_name = name
        self._name_entry.delete(0, "end")
        self._name_entry.insert(0, name)

        width = data.get("width_mm", TAPE_WIDTH_MM)
        height = data.get("height_mm", 29)
        self._height_entry.delete(0, "end")
        self._height_entry.insert(0, str(height))
        self.designer_canvas.set_label_size(width, height)

        from src.modules.designer.elements import Element
        elements = [Element.from_dict(e) for e in data.get("elements", [])]
        self.designer_canvas.load_elements(elements)
        self._on_element_selected(None)

    def _show_preview(self):
        """Render and display a preview with sample data."""
        elements = self.designer_canvas.get_elements()
        if not elements:
            messagebox.showinfo("Papiro", "El canvas está vacío.")
            return

        template_data = {
            "width_mm": self.designer_canvas.width_mm,
            "height_mm": self.designer_canvas.height_mm,
            "background": "#FFFFFF",
            "elements": [e.to_dict() for e in elements],
        }

        # Sample variables for preview
        sample_vars = {
            "producto": "Cannabis Sativa 10g",
            "nombre_paciente": "Juan Pérez",
            "fecha": "20/03/2026",
            "peso": "10g",
            "cepa": "Blue Dream",
            "lote": "LOT-2026-042",
            "thc": "18.5%",
            "cbd": "0.3%",
        }

        try:
            img = self.store.render_preview(template_data, sample_vars, dpi=150)
        except Exception as exc:
            messagebox.showerror("Papiro", f"Error al renderizar:\n{exc}")
            return

        # Show in a new window
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("Vista previa — Papiro")
        preview_win.configure(fg_color=BG_DARK)
        preview_win.geometry("700x500")
        preview_win.transient(self.winfo_toplevel())

        ctk.CTkLabel(
            preview_win, text="Vista previa (datos de ejemplo)",
            font=("Helvetica", 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(pady=(12, 4))

        # Scale to fit
        max_w, max_h = 650, 400
        ratio = min(max_w / img.width, max_h / img.height, 1.0)
        display = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.LANCZOS,
        )

        try:
            ctk_img = ctk.CTkImage(light_image=display, dark_image=display,
                                   size=(display.width, display.height))
            img_label = ctk.CTkLabel(preview_win, text="", image=ctk_img)
            img_label._ctk_img = ctk_img  # prevent GC
        except (AttributeError, TypeError):
            tk_img = ImageTk.PhotoImage(display)
            img_label = ctk.CTkLabel(preview_win, text="", image=tk_img)
            img_label.image = tk_img  # prevent GC
        img_label.pack(expand=True, pady=8)

        ctk.CTkButton(
            preview_win, text="Cerrar", width=100, height=32,
            fg_color=ACCENT_BLUE, hover_color="#0b5cbf",
            text_color="#FFFFFF",
            command=preview_win.destroy,
        ).pack(pady=(0, 12))

    # ------------------------------------------------------------------ #
    #  Gallery                                                             #
    # ------------------------------------------------------------------ #

    def _build_gallery(self):
        gallery_frame = ctk.CTkFrame(self, fg_color=BG_CARD, height=120,
                                     corner_radius=8)
        gallery_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        gallery_frame.grid_propagate(False)

        header_frame = ctk.CTkFrame(gallery_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            header_frame, text="Plantillas guardadas",
            font=("Helvetica", 12, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header_frame, text="Eliminar", width=70, height=24,
            fg_color=ACCENT_RED, hover_color="#cc1133",
            text_color="#FFFFFF", font=("Helvetica", 10),
            command=self._delete_selected_template,
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            header_frame, text="Duplicar", width=70, height=24,
            fg_color=BG_CARD_LIGHT, hover_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY, font=("Helvetica", 10),
            command=self._duplicate_selected_template,
        ).pack(side="right")

        self._gallery_scroll = ctk.CTkScrollableFrame(
            gallery_frame, fg_color="transparent",
            orientation="horizontal", height=70,
        )
        self._gallery_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _refresh_gallery(self):
        """Reload template thumbnails in the gallery."""
        for widget in self._gallery_scroll.winfo_children():
            widget.destroy()
        self._gallery_images.clear()

        templates = self.store.list_templates()
        if not templates:
            ctk.CTkLabel(
                self._gallery_scroll, text="Sin plantillas guardadas",
                text_color=TEXT_MUTED, font=("Helvetica", 11),
            ).pack(side="left", padx=8)
            return

        for tmpl in templates:
            name = tmpl["name"]
            btn_frame = ctk.CTkFrame(self._gallery_scroll,
                                     fg_color=BG_CARD_LIGHT,
                                     corner_radius=6, width=120, height=60)
            btn_frame.pack(side="left", padx=4, pady=2)
            try:
                btn_frame.pack_propagate(False)
            except (AttributeError, TypeError):
                pass

            # Try to show thumbnail
            if tmpl.get("thumbnail_path"):
                try:
                    thumb_img = Image.open(tmpl["thumbnail_path"])
                    thumb_img.thumbnail((110, 40), Image.LANCZOS)
                    try:
                        ctk_thumb = ctk.CTkImage(
                            light_image=thumb_img, dark_image=thumb_img,
                            size=(thumb_img.width, thumb_img.height))
                        self._gallery_images.append(ctk_thumb)
                        thumb_label = ctk.CTkLabel(btn_frame, text="",
                                                   image=ctk_thumb)
                    except (AttributeError, TypeError):
                        tk_thumb = ImageTk.PhotoImage(thumb_img)
                        self._gallery_images.append(tk_thumb)
                        thumb_label = ctk.CTkLabel(btn_frame, text="",
                                                   image=tk_thumb)
                    thumb_label.pack(expand=True)
                    thumb_label.bind("<Button-1>",
                                    lambda e, n=name: self._load_template(n))
                except Exception:
                    pass

            name_label = ctk.CTkLabel(
                btn_frame, text=name[:15],
                text_color=TEXT_PRIMARY, font=("Helvetica", 9),
            )
            name_label.pack(pady=(0, 2))
            name_label.bind("<Button-1>",
                            lambda e, n=name: self._load_template(n))
            btn_frame.bind("<Button-1>",
                           lambda e, n=name: self._load_template(n))

    def _delete_selected_template(self):
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showwarning("Papiro",
                                   "Ingresa el nombre de la plantilla a eliminar.")
            return
        if messagebox.askyesno("Papiro",
                               f"¿Eliminar plantilla '{name}'?"):
            self.store.delete_template(name)
            self._refresh_gallery()
            self._new_template()

    def _duplicate_selected_template(self):
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showwarning("Papiro",
                                   "Ingresa el nombre de la plantilla a duplicar.")
            return
        new_name = f"{name} (copia)"
        try:
            self.store.duplicate_template(name, new_name)
            self._refresh_gallery()
            messagebox.showinfo("Papiro",
                                f"Plantilla duplicada como '{new_name}'.")
        except FileNotFoundError:
            messagebox.showerror("Papiro",
                                 f"Plantilla '{name}' no encontrada.")

    # ------------------------------------------------------------------ #
    #  Utilities                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _contrast_text(hex_color):
        """Return black or white text color for readability on given bg."""
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except (ValueError, IndexError):
            return "#FFFFFF"
