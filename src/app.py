"""
Papiro - Aplicación principal
Ventana con navegación por tabs: Despacho, Producto, Diseñador
"""

import customtkinter as ctk
from PIL import Image, ImageTk
import os
import sys

from src.config import (
    BG_DARK, BG_CARD, BG_CARD_LIGHT, BORDER_COLOR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_CYAN,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    APP_NAME, APP_SUBTITLE, APP_VERSION,
    get_assets_path,
)


class PapiroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("900x700")
        self.resizable(True, True)
        self.minsize(800, 600)
        self.configure(fg_color=BG_DARK)

        ctk.set_appearance_mode("dark")

        self._set_icon()
        self._create_layout()
        self._center_window()

    def _set_icon(self):
        try:
            import tkinter as tk
            assets = get_assets_path()
            if sys.platform == 'win32':
                ico_path = os.path.join(assets, 'icon.ico')
                if os.path.exists(ico_path):
                    self.iconbitmap(ico_path)
            else:
                png_path = os.path.join(assets, 'icon.png')
                if os.path.exists(png_path):
                    img = Image.open(png_path)
                    img = img.resize((32, 32), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.iconphoto(True, photo)
                    self._icon_photo = photo  # prevent garbage collection
        except Exception:
            pass

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _load_logo(self):
        try:
            logo_path = os.path.join(get_assets_path(), 'logo.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                max_w = 32
                ratio = max_w / img.width
                new_h = int(img.height * ratio)
                img = img.resize((max_w, new_h), Image.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(max_w, new_h))
        except Exception:
            pass
        return None

    def _create_layout(self):
        # === HEADER ===
        header = ctk.CTkFrame(self, height=50, fg_color=BG_CARD, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=16)

        # Logo + Title
        logo = self._load_logo()
        if logo:
            ctk.CTkLabel(header_inner, image=logo, text="").pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            header_inner, text=APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            header_inner, text=f"  {APP_SUBTITLE}",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED
        ).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(
            header_inner, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=9),
            text_color=TEXT_MUTED
        ).pack(side="right")

        # === TAB BAR ===
        tab_bar = ctk.CTkFrame(self, height=40, fg_color=BG_CARD_LIGHT, corner_radius=0)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        self.tab_buttons = {}
        self.tab_frames = {}
        self.active_tab = None

        tabs_config = [
            ("Despacho", ACCENT_BLUE, "Etiquetas de envio desde PDF"),
            ("Producto", ACCENT_GREEN, "Etiquetas de producto"),
            ("Diseñador", ACCENT_ORANGE, "Diseñar templates de etiquetas"),
        ]

        tab_btn_frame = ctk.CTkFrame(tab_bar, fg_color="transparent")
        tab_btn_frame.pack(side="left", padx=12, pady=4)

        for tab_name, color, tooltip in tabs_config:
            btn = ctk.CTkButton(
                tab_btn_frame,
                text=tab_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=120, height=30, corner_radius=6,
                fg_color="transparent",
                text_color=TEXT_SECONDARY,
                hover_color=BG_CARD,
                command=lambda t=tab_name: self._switch_tab(t)
            )
            btn.pack(side="left", padx=2)
            self.tab_buttons[tab_name] = (btn, color)

        # === CONTENT AREA ===
        self.content_frame = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.content_frame.pack(fill="both", expand=True)

        # Lazy-load tabs
        self._loaded_tabs = {}
        self._switch_tab("Despacho")

    def _switch_tab(self, tab_name):
        if self.active_tab == tab_name:
            return

        # Update button styles
        for name, (btn, color) in self.tab_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=color, text_color="#ffffff" if name != "Producto" else "#0a0a0a")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY)

        # Hide current tab
        if self.active_tab and self.active_tab in self._loaded_tabs:
            self._loaded_tabs[self.active_tab].pack_forget()

        # Load or show tab
        if tab_name not in self._loaded_tabs:
            self._loaded_tabs[tab_name] = self._create_tab(tab_name)

        self._loaded_tabs[tab_name].pack(fill="both", expand=True, padx=12, pady=8)
        self.active_tab = tab_name

    def _create_tab(self, tab_name):
        if tab_name == "Despacho":
            from src.modules.despacho.view import DespachoView
            return DespachoView(self.content_frame)
        elif tab_name == "Producto":
            from src.modules.producto.view import ProductoView
            return ProductoView(self.content_frame)
        elif tab_name == "Diseñador":
            from src.modules.designer.view import DesignerView
            return DesignerView(self.content_frame)
        else:
            # Fallback: return an empty frame to prevent crash
            return ctk.CTkFrame(self.content_frame, fg_color="transparent")


def run():
    app = PapiroApp()
    app.mainloop()
