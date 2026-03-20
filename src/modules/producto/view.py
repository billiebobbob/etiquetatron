"""
Papiro - Vista del módulo Producto
Permite seleccionar un template, llenar datos de producto,
previsualizar la etiqueta y enviarla a imprimir.
Orientado a Brother QL-800 con cinta de 62mm.
"""

import os
import threading
import tempfile
from datetime import datetime

import customtkinter as ctk
from PIL import Image, ImageTk

from src.config import (
    BG_DARK, BG_CARD, BG_CARD_LIGHT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER_COLOR, TAPE_WIDTH_MM, DPI,
    PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT,
    get_templates_path,
)
from src.printing.printer_manager import get_printers, get_default_printer, print_image
from src.modules.producto.renderer import LabelRenderer


# ---------------------------------------------------------------------------
# Intentar importar TemplateStore — puede no existir todavia
# ---------------------------------------------------------------------------
try:
    from src.modules.designer.template_store import TemplateStore
    _HAS_TEMPLATE_STORE = True
except ImportError:
    _HAS_TEMPLATE_STORE = False
    TemplateStore = None


# ---------------------------------------------------------------------------
# Default template (fallback cuando no hay TemplateStore o no hay templates)
# ---------------------------------------------------------------------------
_DEFAULT_TEMPLATE = {
    "name": "Producto Básico",
    "width_mm": TAPE_WIDTH_MM,
    "height_mm": 29,
    "background": "#FFFFFF",
    "elements": [
        {
            "type": "text",
            "text": "{{producto}}",
            "x": 2, "y": 1.5,
            "font_size": 14, "bold": True,
            "color": "#000000",
            "max_width": 58,
            "alignment": "center",
        },
        {
            "type": "line",
            "x1": 2, "y1": 8.5,
            "x2": 60, "y2": 8.5,
            "color": "#CCCCCC", "width": 1,
        },
        {
            "type": "text",
            "text": "Cepa: {{cepa}}",
            "x": 2, "y": 10,
            "font_size": 9,
            "color": "#333333",
            "max_width": 28,
        },
        {
            "type": "text",
            "text": "Peso: {{peso}}",
            "x": 32, "y": 10,
            "font_size": 9,
            "color": "#333333",
            "max_width": 28,
        },
        {
            "type": "text",
            "text": "Paciente: {{nombre_paciente}}",
            "x": 2, "y": 16,
            "font_size": 8,
            "color": "#555555",
            "max_width": 58,
        },
        {
            "type": "text",
            "text": "Fecha: {{fecha}}",
            "x": 2, "y": 22,
            "font_size": 8,
            "color": "#555555",
            "max_width": 58,
        },
    ],
}


# ---------------------------------------------------------------------------
# ProductoView
# ---------------------------------------------------------------------------

class ProductoView(ctk.CTkFrame):
    """Vista principal del módulo Producto."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.renderer = LabelRenderer()
        self.template_store = TemplateStore(get_templates_path()) if _HAS_TEMPLATE_STORE else None
        self.templates = {}          # name -> template_data
        self.current_image = None    # PIL full-res render
        self.preview_photo = None    # ImageTk para el canvas
        self._debounce_id = None     # after() id para debounce

        self._build_ui()
        self._load_templates()
        self._load_printers()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Top bar: template selector
        self._build_top_bar()

        # Main content: preview (left) + form (right)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.content.grid_columnconfigure(0, weight=3, minsize=300)
        self.content.grid_columnconfigure(1, weight=2, minsize=280)
        self.content.grid_rowconfigure(0, weight=1)

        self._build_preview_panel()
        self._build_form_panel()

    def _build_top_bar(self):
        bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8, height=50)
        bar.pack(fill="x", padx=10, pady=(10, 5))
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="Template:", text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(15, 5))

        self.template_var = ctk.StringVar(value="")
        self.template_dropdown = ctk.CTkComboBox(
            bar, variable=self.template_var,
            values=["(cargando...)"],
            width=240, height=32,
            fg_color=BG_CARD_LIGHT, border_color=BORDER_COLOR,
            button_color=ACCENT_BLUE, button_hover_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
            dropdown_hover_color=BG_CARD_LIGHT,
            command=self._on_template_change,
        )
        self.template_dropdown.pack(side="left", padx=5)

        ctk.CTkButton(
            bar, text="Refresh", width=80, height=32,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_COLOR,
            command=self._load_templates,
        ).pack(side="left", padx=5)

    def _build_preview_panel(self):
        left = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            left, text="Vista Previa", text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        ).pack(pady=(10, 0))

        # Preview canvas area
        self.preview_frame = ctk.CTkFrame(left, fg_color=BG_CARD_LIGHT, corner_radius=6)
        self.preview_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.preview_label = ctk.CTkLabel(
            self.preview_frame, text="Seleccione un template y\npresione Vista Previa",
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=13),
        )
        self.preview_label.pack(expand=True)

        # Bottom bar inside preview: printer + actions
        bottom = ctk.CTkFrame(left, fg_color="transparent")
        bottom.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(
            bottom, text="Impresora:", text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        self.printer_var = ctk.StringVar(value="")
        self.printer_dropdown = ctk.CTkComboBox(
            bottom, variable=self.printer_var,
            values=["(buscando...)"],
            width=180, height=30,
            fg_color=BG_CARD_LIGHT, border_color=BORDER_COLOR,
            button_color=ACCENT_BLUE, button_hover_color=ACCENT_BLUE,
            text_color=TEXT_PRIMARY,
            dropdown_fg_color=BG_CARD, dropdown_text_color=TEXT_PRIMARY,
            dropdown_hover_color=BG_CARD_LIGHT,
        )
        self.printer_dropdown.pack(side="left", padx=(5, 10))

        self.btn_print = ctk.CTkButton(
            bottom, text="Imprimir", width=90, height=32,
            fg_color=ACCENT_GREEN, hover_color="#00a844",
            text_color="#FFFFFF", font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_print,
        )
        self.btn_print.pack(side="left", padx=(0, 5))

        self.btn_save = ctk.CTkButton(
            bottom, text="Guardar", width=80, height=32,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_COLOR,
            command=self._on_save,
        )
        self.btn_save.pack(side="left")

    def _build_form_panel(self):
        right = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            right, text="Datos de Etiqueta", text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(15, 10))

        form = ctk.CTkFrame(right, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)

        # --- Field entries ---
        self.entries = {}
        fields = [
            ("producto", "Producto", ""),
            ("cepa", "Cepa", ""),
            ("peso", "Peso", ""),
            ("nombre_paciente", "Paciente", ""),
            ("fecha", "Fecha", datetime.now().strftime("%d/%m/%Y")),
        ]

        for key, label_text, default in fields:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row, text=f"{label_text}:", width=80, anchor="e",
                text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=13),
            ).pack(side="left")

            entry = ctk.CTkEntry(
                row, height=32,
                fg_color=BG_CARD_LIGHT, border_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
                font=ctk.CTkFont(size=13),
            )
            entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
            if default:
                entry.insert(0, default)

            # Debounced auto-preview on key release
            entry.bind("<KeyRelease>", self._on_field_change)

            self.entries[key] = entry

        # Peso suffix hint
        peso_hint = ctk.CTkLabel(
            form, text="(ej: 5g, 3.5g, 1oz)",
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=11),
        )
        peso_hint.pack(anchor="e", pady=(0, 5))

        # --- Cantidad spinner ---
        cant_row = ctk.CTkFrame(form, fg_color="transparent")
        cant_row.pack(fill="x", pady=(10, 5))

        ctk.CTkLabel(
            cant_row, text="Cantidad:", width=80, anchor="e",
            text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=13),
        ).pack(side="left")

        spinner_frame = ctk.CTkFrame(cant_row, fg_color="transparent")
        spinner_frame.pack(side="left", padx=(8, 0))

        self.cantidad_var = ctk.StringVar(value="1")

        ctk.CTkButton(
            spinner_frame, text="-", width=32, height=32,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
            command=self._decrement_qty,
        ).pack(side="left")

        self.qty_entry = ctk.CTkEntry(
            spinner_frame, textvariable=self.cantidad_var,
            width=50, height=32, justify="center",
            fg_color=BG_CARD_LIGHT, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=ctk.CTkFont(size=13),
        )
        self.qty_entry.pack(side="left", padx=3)

        ctk.CTkButton(
            spinner_frame, text="+", width=32, height=32,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
            command=self._increment_qty,
        ).pack(side="left")

        # --- Vista Previa button ---
        self.btn_preview = ctk.CTkButton(
            form, text="Vista Previa", height=38,
            fg_color=ACCENT_BLUE, hover_color="#0b6ad4",
            text_color="#FFFFFF", font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_preview,
        )
        self.btn_preview.pack(fill="x", pady=(20, 5))

        # Status label
        self.status_label = ctk.CTkLabel(
            right, text="", text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.status_label.pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Template loading
    # ------------------------------------------------------------------

    def _load_templates(self):
        """Carga templates desde TemplateStore (si existe) + default."""
        self.templates = {"Producto Básico": _DEFAULT_TEMPLATE}

        if self.template_store is not None:
            try:
                store_templates = self.template_store.list_templates()
                for t in store_templates:
                    tdata = self.template_store.load_template(t)
                    if tdata:
                        self.templates[t] = tdata
            except Exception:
                pass

        names = list(self.templates.keys())
        self.template_dropdown.configure(values=names)
        if names:
            self.template_var.set(names[0])

    def _on_template_change(self, choice):
        """Cuando se cambia el template seleccionado."""
        self._on_preview()

    # ------------------------------------------------------------------
    # Printer loading
    # ------------------------------------------------------------------

    def _load_printers(self):
        """Detecta impresoras en un thread."""
        def _detect():
            printers = get_printers()
            default = get_default_printer()
            self.after(0, lambda: self._set_printers(printers, default))

        threading.Thread(target=_detect, daemon=True).start()

    def _set_printers(self, printers, default):
        if not printers:
            printers = ["(no se encontraron)"]
        self.printer_dropdown.configure(values=printers)
        if default and default in printers:
            self.printer_var.set(default)
        elif printers:
            self.printer_var.set(printers[0])

    # ------------------------------------------------------------------
    # Variable collection
    # ------------------------------------------------------------------

    def _get_variables(self):
        """Obtiene los valores actuales del formulario."""
        variables = {}
        for key, entry in self.entries.items():
            variables[key] = entry.get().strip()
        return variables

    def _get_current_template(self):
        """Devuelve el template_data actualmente seleccionado."""
        name = self.template_var.get()
        return self.templates.get(name, _DEFAULT_TEMPLATE)

    # ------------------------------------------------------------------
    # Cantidad spinner
    # ------------------------------------------------------------------

    def _get_cantidad(self):
        try:
            val = int(self.cantidad_var.get())
            return max(1, min(99, val))
        except (ValueError, TypeError):
            return 1

    def _increment_qty(self):
        val = self._get_cantidad()
        if val < 99:
            self.cantidad_var.set(str(val + 1))

    def _decrement_qty(self):
        val = self._get_cantidad()
        if val > 1:
            self.cantidad_var.set(str(val - 1))

    # ------------------------------------------------------------------
    # Debounced auto-preview
    # ------------------------------------------------------------------

    def _on_field_change(self, event=None):
        """Programa un preview con debounce de 500ms."""
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(500, self._on_preview)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_preview(self):
        """Renderiza la etiqueta y muestra el preview."""
        template = self._get_current_template()
        variables = self._get_variables()

        self.status_label.configure(text="Renderizando...", text_color=TEXT_MUTED)
        self.btn_preview.configure(state="disabled")

        def _render():
            try:
                full, preview = self.renderer.render_preview(
                    template, variables,
                    max_width=PREVIEW_MAX_WIDTH,
                    max_height=PREVIEW_MAX_HEIGHT,
                )
                self.after(0, lambda: self._show_preview(full, preview))
            except Exception as e:
                self.after(0, lambda: self._show_error(f"Error: {e}"))

        threading.Thread(target=_render, daemon=True).start()

    def _show_preview(self, full_image, preview_image):
        """Muestra la imagen renderizada en el panel de preview."""
        self.current_image = full_image
        self.preview_photo = ImageTk.PhotoImage(preview_image)

        self.preview_label.configure(
            image=self.preview_photo,
            text="",
        )
        self.btn_preview.configure(state="normal")
        self.status_label.configure(
            text=f"Etiqueta: {full_image.size[0]}x{full_image.size[1]}px @ {DPI}dpi",
            text_color=ACCENT_GREEN,
        )

    def _show_error(self, msg):
        self.btn_preview.configure(state="normal")
        self.status_label.configure(text=msg, text_color=ACCENT_RED)

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------

    def _on_print(self):
        """Imprime la etiqueta renderizada (cantidad copias)."""
        if self.current_image is None:
            self.status_label.configure(
                text="Primero genere una vista previa", text_color=ACCENT_ORANGE,
            )
            return

        printer = self.printer_var.get()
        if not printer or printer.startswith("("):
            self.status_label.configure(
                text="Seleccione una impresora", text_color=ACCENT_ORANGE,
            )
            return

        cantidad = self._get_cantidad()
        self.btn_print.configure(state="disabled")
        self.status_label.configure(
            text=f"Imprimiendo {cantidad} copia(s)...", text_color=TEXT_MUTED,
        )

        def _do_print():
            try:
                # Guardar imagen temporal
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                self.current_image.save(tmp.name, dpi=(DPI, DPI))
                tmp.close()

                template = self._get_current_template()
                height_mm = template.get("height_mm", 29)

                for i in range(cantidad):
                    result = print_image(
                        tmp.name,
                        printer_name=printer,
                        width_mm=TAPE_WIDTH_MM,
                        height_mm=height_mm,
                    )

                # Limpiar archivo temporal
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass

                self.after(0, lambda: self._print_done(cantidad))
            except Exception as e:
                self.after(0, lambda: self._print_error(str(e)))

        threading.Thread(target=_do_print, daemon=True).start()

    def _print_done(self, cantidad):
        self.btn_print.configure(state="normal")
        self.status_label.configure(
            text=f"{cantidad} copia(s) enviada(s) a imprimir",
            text_color=ACCENT_GREEN,
        )

    def _print_error(self, msg):
        self.btn_print.configure(state="normal")
        self.status_label.configure(
            text=f"Error al imprimir: {msg}", text_color=ACCENT_RED,
        )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self):
        """Guarda la imagen renderizada en disco."""
        if self.current_image is None:
            self.status_label.configure(
                text="Primero genere una vista previa", text_color=ACCENT_ORANGE,
            )
            return

        try:
            from tkinter import filedialog
        except ImportError:
            self.status_label.configure(
                text="No se pudo abrir el diálogo de guardado", text_color=ACCENT_RED,
            )
            return

        variables = self._get_variables()
        default_name = variables.get("producto", "etiqueta").replace(" ", "_")
        default_name = f"{default_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        filepath = filedialog.asksaveasfilename(
            title="Guardar etiqueta",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("BMP", "*.bmp"),
                ("Todos", "*.*"),
            ],
        )

        if not filepath:
            return

        def _do_save():
            try:
                self.current_image.save(filepath, dpi=(DPI, DPI))
                self.after(0, lambda: self.status_label.configure(
                    text=f"Guardado: {os.path.basename(filepath)}",
                    text_color=ACCENT_GREEN,
                ))
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(
                    text=f"Error al guardar: {e}", text_color=ACCENT_RED,
                ))

        threading.Thread(target=_do_save, daemon=True).start()
