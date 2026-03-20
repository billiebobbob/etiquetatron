"""
Papiro - Despacho: Vista (UI)
Interfaz CustomTkinter para cargar PDFs, previsualizar y imprimir etiquetas de despacho.
"""

import os
import threading
import tempfile
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageTk

from src.config import (
    BG_DARK, BG_CARD, BG_CARD_LIGHT,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_CYAN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER_COLOR,
    DPI, LABEL_FORMATS,
)
from src.printing.printer_manager import (
    get_printers, get_default_printer, print_image, open_printer_config,
)
from src.modules.despacho.processor import process_pdf, save_labels


# Preview constraints
PREVIEW_AREA_WIDTH = 350
PREVIEW_AREA_HEIGHT = 700


class DespachoView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.labels = []         # List of {'image': PIL.Image, 'venta': str}
        self.date_str = None
        self.current_index = 0
        self.pdf_path = None
        self._preview_photo = None  # Keep reference to prevent GC

        self._build_ui()
        self._refresh_printers()
        self._bind_keys()

    # ------------------------------------------------------------------ #
    #  UI Construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # --- Left panel: Preview ---
        self._build_preview_panel()

        # --- Right panel: Controls ---
        self._build_controls_panel()

    def _build_preview_panel(self):
        preview_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        # Title bar
        title_bar = ctk.CTkFrame(preview_frame, fg_color="transparent")
        title_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        title_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            title_bar, text="Vista previa",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        self.lbl_counter = ctk.CTkLabel(
            title_bar, text="0 / 0",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECONDARY
        )
        self.lbl_counter.grid(row=0, column=2, sticky="e")

        # Venta label
        self.lbl_venta = ctk.CTkLabel(
            preview_frame, text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT_CYAN
        )
        self.lbl_venta.grid(row=1, column=0, sticky="n", padx=16, pady=(8, 0))

        # Preview canvas area
        canvas_frame = ctk.CTkFrame(preview_frame, fg_color=BG_CARD_LIGHT, corner_radius=8)
        canvas_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            canvas_frame, text="Cargar un PDF para\nver las etiquetas",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED
        )
        self.preview_label.grid(row=0, column=0, padx=16, pady=16)

        # Navigation arrows
        nav_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
        nav_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        nav_frame.grid_columnconfigure(1, weight=1)

        self.btn_prev = ctk.CTkButton(
            nav_frame, text="\u25C0  Anterior", width=120,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            command=self._prev_label, state="disabled"
        )
        self.btn_prev.grid(row=0, column=0, sticky="w")

        self.btn_next = ctk.CTkButton(
            nav_frame, text="Siguiente  \u25B6", width=120,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            command=self._next_label, state="disabled"
        )
        self.btn_next.grid(row=0, column=2, sticky="e")

    def _build_controls_panel(self):
        ctrl = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12, width=280)
        ctrl.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        ctrl.grid_columnconfigure(0, weight=1)

        # --- Load PDF ---
        ctk.CTkLabel(
            ctrl, text="Archivo",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        self.btn_load = ctk.CTkButton(
            ctrl, text="Cargar PDF", height=38,
            fg_color=ACCENT_BLUE, hover_color="#0b5fcc",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_load_pdf
        )
        self.btn_load.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))

        self.lbl_file = ctk.CTkLabel(
            ctrl, text="Ningun archivo cargado",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED, wraplength=240
        )
        self.lbl_file.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

        # Separator
        ctk.CTkFrame(ctrl, fg_color=BORDER_COLOR, height=1).grid(
            row=3, column=0, sticky="ew", padx=16, pady=4
        )

        # --- Printer selector ---
        ctk.CTkLabel(
            ctrl, text="Impresora",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY
        ).grid(row=4, column=0, sticky="w", padx=16, pady=(12, 4))

        printer_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        printer_row.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 4))
        printer_row.grid_columnconfigure(0, weight=1)

        self.printer_var = ctk.StringVar(value="")
        self.cmb_printer = ctk.CTkComboBox(
            printer_row, variable=self.printer_var,
            values=[], state="readonly",
            fg_color=BG_CARD_LIGHT, border_color=BORDER_COLOR,
            button_color=ACCENT_BLUE, button_hover_color="#0b5fcc",
            dropdown_fg_color=BG_CARD_LIGHT,
            text_color=TEXT_PRIMARY
        )
        self.cmb_printer.grid(row=0, column=0, sticky="ew")

        btn_refresh_printer = ctk.CTkButton(
            printer_row, text="\u21BB", width=36,
            fg_color=BG_CARD_LIGHT, hover_color=BORDER_COLOR,
            text_color=TEXT_SECONDARY,
            command=self._refresh_printers
        )
        btn_refresh_printer.grid(row=0, column=1, sticky="e", padx=(4, 0))

        btn_config_printer = ctk.CTkButton(
            ctrl, text="Configurar impresora", height=30,
            fg_color="transparent", hover_color=BG_CARD_LIGHT,
            text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(size=11),
            command=self._on_printer_config
        )
        btn_config_printer.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 12))

        # Separator
        ctk.CTkFrame(ctrl, fg_color=BORDER_COLOR, height=1).grid(
            row=7, column=0, sticky="ew", padx=16, pady=4
        )

        # --- Action buttons ---
        ctk.CTkLabel(
            ctrl, text="Acciones",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY
        ).grid(row=8, column=0, sticky="w", padx=16, pady=(12, 4))

        self.btn_save = ctk.CTkButton(
            ctrl, text="Guardar", height=36,
            fg_color=ACCENT_GREEN, hover_color="#00a344",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_save, state="disabled"
        )
        self.btn_save.grid(row=9, column=0, sticky="ew", padx=16, pady=(0, 4))

        self.btn_print_one = ctk.CTkButton(
            ctrl, text="Imprimir", height=36,
            fg_color=ACCENT_ORANGE, hover_color="#cc5700",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_print_one, state="disabled"
        )
        self.btn_print_one.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 4))

        self.btn_print_all = ctk.CTkButton(
            ctrl, text="Imprimir Todas", height=36,
            fg_color=ACCENT_BLUE, hover_color="#0b5fcc",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_print_all, state="disabled"
        )
        self.btn_print_all.grid(row=11, column=0, sticky="ew", padx=16, pady=(0, 12))

        # Separator
        ctk.CTkFrame(ctrl, fg_color=BORDER_COLOR, height=1).grid(
            row=12, column=0, sticky="ew", padx=16, pady=4
        )

        # --- Progress bar ---
        self.progress = ctk.CTkProgressBar(
            ctrl, fg_color=BG_CARD_LIGHT, progress_color=ACCENT_BLUE,
            height=6
        )
        self.progress.grid(row=13, column=0, sticky="ew", padx=16, pady=(12, 4))
        self.progress.set(0)

        # --- Log area ---
        ctk.CTkLabel(
            ctrl, text="Registro",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY
        ).grid(row=14, column=0, sticky="w", padx=16, pady=(8, 4))

        self.log_box = ctk.CTkTextbox(
            ctrl, height=160,
            fg_color=BG_CARD_LIGHT, text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=11),
            border_width=1, border_color=BORDER_COLOR,
            state="disabled"
        )
        self.log_box.grid(row=15, column=0, sticky="nsew", padx=16, pady=(0, 16))
        ctrl.grid_rowconfigure(15, weight=1)

    # ------------------------------------------------------------------ #
    #  Key bindings
    # ------------------------------------------------------------------ #
    def _bind_keys(self):
        # Bind at the top-level window to catch arrow keys
        top = self.winfo_toplevel()
        top.bind("<Left>", lambda e: self._prev_label())
        top.bind("<Right>", lambda e: self._next_label())

    # ------------------------------------------------------------------ #
    #  Logging
    # ------------------------------------------------------------------ #
    def _log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  Printer helpers
    # ------------------------------------------------------------------ #
    def _refresh_printers(self):
        printers = get_printers()
        default = get_default_printer()

        if printers:
            self.cmb_printer.configure(values=printers)
            if default and default in printers:
                self.printer_var.set(default)
            else:
                self.printer_var.set(printers[0])
        else:
            self.cmb_printer.configure(values=["(ninguna)"])
            self.printer_var.set("(ninguna)")

    def _on_printer_config(self):
        printer = self.printer_var.get()
        if printer and printer != "(ninguna)":
            try:
                open_printer_config(printer)
            except RuntimeError as e:
                self._log(f"Error: {e}")

    # ------------------------------------------------------------------ #
    #  Preview navigation
    # ------------------------------------------------------------------ #
    def _update_preview(self):
        if not self.labels:
            self.preview_label.configure(
                image=None,
                text="Cargar un PDF para\nver las etiquetas"
            )
            self.lbl_counter.configure(text="0 / 0")
            self.lbl_venta.configure(text="")
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            return

        idx = self.current_index
        total = len(self.labels)
        label_data = self.labels[idx]

        # Counter and venta
        self.lbl_counter.configure(text=f"{idx + 1} / {total}")
        self.lbl_venta.configure(text=label_data["venta"])

        # Navigation state
        self.btn_prev.configure(state="normal" if idx > 0 else "disabled")
        self.btn_next.configure(state="normal" if idx < total - 1 else "disabled")

        # Generate thumbnail preserving aspect ratio
        img = label_data["image"]
        img_w, img_h = img.size

        # Fit within preview area
        scale = min(PREVIEW_AREA_WIDTH / img_w, PREVIEW_AREA_HEIGHT / img_h)
        thumb_w = max(1, int(img_w * scale))
        thumb_h = max(1, int(img_h * scale))

        thumb = img.resize((thumb_w, thumb_h), Image.LANCZOS)
        self._preview_photo = ctk.CTkImage(light_image=thumb, size=(thumb_w, thumb_h))

        self.preview_label.configure(image=self._preview_photo, text="")

    def _prev_label(self):
        if self.labels and self.current_index > 0:
            self.current_index -= 1
            self._update_preview()

    def _next_label(self):
        if self.labels and self.current_index < len(self.labels) - 1:
            self.current_index += 1
            self._update_preview()

    # ------------------------------------------------------------------ #
    #  Load PDF
    # ------------------------------------------------------------------ #
    def _on_load_pdf(self):
        path = filedialog.askopenfilename(
            title="Seleccionar PDF de despacho",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if not path:
            return

        self.pdf_path = path
        self.lbl_file.configure(text=os.path.basename(path))
        self._log(f"Cargando: {os.path.basename(path)}")
        self.progress.set(0)

        # Disable buttons during load
        self._set_actions_state("disabled")
        self.btn_load.configure(state="disabled")

        threading.Thread(target=self._load_pdf_thread, daemon=True).start()

    def _load_pdf_thread(self):
        try:
            fmt = LABEL_FORMATS["Despacho"]
            labels, date_str = process_pdf(
                self.pdf_path,
                width_mm=fmt["width_mm"],
                height_mm=fmt["height_mm"],
            )

            self.after(0, lambda: self._on_pdf_loaded(labels, date_str))

        except Exception as e:
            self.after(0, lambda: self._on_pdf_error(str(e)))

    def _on_pdf_loaded(self, labels, date_str):
        self.labels = labels
        self.date_str = date_str
        self.current_index = 0

        self.btn_load.configure(state="normal")
        self.progress.set(1)

        if labels:
            self._set_actions_state("normal")
            self._log(f"Se encontraron {len(labels)} etiquetas")
            if date_str:
                self._log(f"Fecha: {date_str}")
        else:
            self._set_actions_state("disabled")
            self._log("No se encontraron etiquetas en el PDF")

        self._update_preview()

    def _on_pdf_error(self, error_msg):
        self.btn_load.configure(state="normal")
        self._log(f"Error al cargar PDF: {error_msg}")
        self._set_actions_state("disabled")
        self.labels = []
        self._update_preview()

    # ------------------------------------------------------------------ #
    #  Save
    # ------------------------------------------------------------------ #
    def _on_save(self):
        if not self.labels:
            return

        dest_dir = filedialog.askdirectory(title="Seleccionar carpeta destino")
        if not dest_dir:
            return

        self._log("Guardando etiquetas...")
        self._set_actions_state("disabled")

        threading.Thread(
            target=self._save_thread, args=(dest_dir,), daemon=True
        ).start()

    def _save_thread(self, dest_dir):
        try:
            paths = save_labels(
                self.labels, "Despacho", self.date_str, dest_dir
            )
            self.after(0, lambda: self._on_save_done(paths))
        except Exception as e:
            self.after(0, lambda: self._on_save_error(str(e)))

    def _on_save_done(self, paths):
        self._set_actions_state("normal")
        self.progress.set(1)
        self._log(f"Guardadas {len(paths)} etiquetas")
        if paths:
            self._log(f"En: {os.path.dirname(paths[0])}")

    def _on_save_error(self, error_msg):
        self._set_actions_state("normal")
        self._log(f"Error al guardar: {error_msg}")

    # ------------------------------------------------------------------ #
    #  Print single
    # ------------------------------------------------------------------ #
    def _on_print_one(self):
        if not self.labels:
            return

        printer = self.printer_var.get()
        if not printer or printer == "(ninguna)":
            self._log("No hay impresora seleccionada")
            return

        idx = self.current_index
        self._log(f"Imprimiendo {self.labels[idx]['venta']}...")
        self._set_actions_state("disabled")

        threading.Thread(
            target=self._print_single_thread,
            args=(idx, printer),
            daemon=True
        ).start()

    def _print_single_thread(self, idx, printer):
        label = None
        try:
            label = self.labels[idx]
            fmt = LABEL_FORMATS["Despacho"]

            # Save to temp file
            tmp = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix=f"papiro_{label['venta']}_"
            )
            tmp_path = tmp.name
            tmp.close()

            label["image"].save(tmp_path, "PNG", dpi=(DPI, DPI))

            result = print_image(
                tmp_path, printer_name=printer,
                width_mm=fmt["width_mm"], height_mm=fmt["height_mm"]
            )

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            if result and result.returncode == 0:
                self.after(0, lambda: self._print_done(label["venta"]))
            else:
                stderr = result.stderr if result else "Sin respuesta"
                self.after(0, lambda: self._print_error(label["venta"], stderr))

        except Exception as e:
            venta = label["venta"] if label else f"Etiqueta #{idx}"
            err_msg = str(e)
            self.after(0, lambda: self._print_error(venta, err_msg))

    def _print_done(self, venta):
        self._set_actions_state("normal")
        self._log(f"Impreso: {venta}")

    def _print_error(self, venta, error_msg):
        self._set_actions_state("normal")
        self._log(f"Error imprimiendo {venta}: {error_msg}")

    # ------------------------------------------------------------------ #
    #  Print all
    # ------------------------------------------------------------------ #
    def _on_print_all(self):
        if not self.labels:
            return

        printer = self.printer_var.get()
        if not printer or printer == "(ninguna)":
            self._log("No hay impresora seleccionada")
            return

        total = len(self.labels)
        self._log(f"Imprimiendo {total} etiquetas...")
        self._set_actions_state("disabled")
        self.progress.set(0)

        threading.Thread(
            target=self._print_all_thread,
            args=(printer,),
            daemon=True
        ).start()

    def _print_all_thread(self, printer):
        total = len(self.labels)
        fmt = LABEL_FORMATS["Despacho"]
        errors = []

        for i, label in enumerate(self.labels):
            try:
                # Save to temp file
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False, prefix=f"papiro_{label['venta']}_"
                )
                tmp_path = tmp.name
                tmp.close()

                label["image"].save(tmp_path, "PNG", dpi=(DPI, DPI))

                result = print_image(
                    tmp_path, printer_name=printer,
                    width_mm=fmt["width_mm"], height_mm=fmt["height_mm"]
                )

                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

                if result and result.returncode != 0:
                    errors.append(label["venta"])

                # Update progress
                progress = (i + 1) / total
                venta = label["venta"]
                self.after(0, lambda p=progress, v=venta: self._print_all_progress(p, v))

            except Exception as e:
                errors.append(label["venta"])
                self.after(0, lambda v=label["venta"], err=str(e): self._log(
                    f"Error en {v}: {err}"
                ))

        self.after(0, lambda: self._print_all_done(total, errors))

    def _print_all_progress(self, progress, venta):
        self.progress.set(progress)
        self._log(f"Impreso: {venta}")

    def _print_all_done(self, total, errors):
        self._set_actions_state("normal")
        self.progress.set(1)
        if errors:
            self._log(f"Completado con {len(errors)} error(es) de {total}")
        else:
            self._log(f"Todas las {total} etiquetas impresas correctamente")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _set_actions_state(self, state):
        self.btn_save.configure(state=state)
        self.btn_print_one.configure(state=state)
        self.btn_print_all.configure(state=state)
