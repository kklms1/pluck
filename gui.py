"""Pluck — modern desktop GUI.

Layout: left sidebar (brand monogram, engine selector, settings, plan badge)
+ main area (URL input, custom-instructions, log, results grid).
"""
from __future__ import annotations

import asyncio
import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont

from extractor import ExtractionResult, PluckExtractor
from subscription import (
    LicenseManager,
    Plan,
    UsageTracker,
    can_extract,
    clamp_max_products,
    plan_info,
)

APP_NAME = "Pluck"
APP_TAGLINE = "AI shopping extractor"

# Sleek dark palette — inspired by Linear / Raycast / ElevenLabs
COLORS = {
    "bg_primary": "#0e0e10",
    "bg_secondary": "#161618",
    "bg_tertiary": "#1f1f23",
    "accent": "#8b5cf6",          # violet
    "accent_hover": "#7c4ef0",
    "accent_soft": "#2a1f3d",
    "text_primary": "#f5f5f7",
    "text_secondary": "#9ca3af",
    "text_muted": "#6b7280",
    "border": "#2a2a30",
    "success": "#10b981",
    "error": "#ef4444",
    "warning": "#f59e0b",
}

ENGINE_OPTIONS = [
    ("local",  "Local (free, no API key)"),
    ("claude", "Claude (Anthropic)"),
    ("openai", "GPT-4o (OpenAI)"),
    ("gemini", "Gemini (Google, free tier)"),
    ("ollama", "Ollama (offline LLaVA)"),
]
ENGINE_LABEL_TO_ID = {label: eid for eid, label in ENGINE_OPTIONS}
ENGINE_ID_TO_LABEL = {eid: label for eid, label in ENGINE_OPTIONS}

ENGINE_ENV_KEY = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

THUMB_SIZE = (180, 180)


# ============================================================
#  Brand monogram icon — minimal "P" badge (rounded square + glyph)
# ============================================================
def _build_brand_icon(size: int = 36) -> ctk.CTkImage:
    scale = 4
    px = size * scale
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded square background with violet gradient feel (solid violet, sleek)
    radius = int(px * 0.28)
    draw.rounded_rectangle(
        [(0, 0), (px - 1, px - 1)],
        radius=radius,
        fill=(139, 92, 246, 255),    # violet-500
    )
    # Inner subtle highlight
    draw.rounded_rectangle(
        [(int(px * 0.06), int(px * 0.06)),
         (int(px * 0.94), int(px * 0.55))],
        radius=int(radius * 0.85),
        fill=(167, 139, 250, 60),
    )

    # "P" glyph
    glyph_color = (255, 255, 255, 255)
    font = None
    for fp in (
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Avenir Next.ttc",
    ):
        try:
            font = ImageFont.truetype(fp, int(px * 0.62))
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    text = "P"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (px - w) / 2 - bbox[0]
        y = (px - h) / 2 - bbox[1] - int(px * 0.04)
    except Exception:
        x, y = px * 0.25, px * 0.15
    draw.text((x, y), text, font=font, fill=glyph_color)

    img = img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


class PluckGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_NAME} — {APP_TAGLINE}")
        self.geometry("1320x860")
        self.minsize(1080, 700)
        self.configure(fg_color=COLORS["bg_primary"])

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.result_queue: "queue.Queue[Any]" = queue.Queue()
        self.is_running = False
        self.last_result: ExtractionResult | None = None
        self._thumb_refs: list[ctk.CTkImage] = []

        self.license_mgr = LicenseManager()
        self.usage = UsageTracker()
        self.license = self.license_mgr.load()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self._refresh_plan_badge()
        self._apply_plan_gating()
        self._on_engine_changed(ENGINE_ID_TO_LABEL["local"])

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queues)

    # ---------- Sidebar ----------
    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=0, width=300)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(30, weight=1)

        # Brand row: monogram + name
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=22, pady=(28, 4), sticky="ew")
        brand.grid_columnconfigure(1, weight=1)

        try:
            self._brand_icon = _build_brand_icon(36)
            ctk.CTkLabel(brand, image=self._brand_icon, text="").grid(
                row=0, column=0, padx=(0, 12), sticky="w",
            )
        except Exception:
            pass

        ctk.CTkLabel(
            brand, text=APP_NAME,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            sidebar, text=APP_TAGLINE,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=1, column=0, padx=24, pady=(0, 18), sticky="ew")

        # Plan badge
        self.plan_badge = ctk.CTkButton(
            sidebar, text="",
            command=self._open_subscription_dialog,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", height=44, corner_radius=10,
        )
        self.plan_badge.grid(row=2, column=0, padx=18, pady=(0, 18), sticky="ew")

        # AI Engine
        self._section_label(sidebar, "AI Engine", row=3)
        self.engine_var = ctk.StringVar(value=ENGINE_ID_TO_LABEL["local"])
        ctk.CTkOptionMenu(
            sidebar, variable=self.engine_var,
            values=[label for _, label in ENGINE_OPTIONS],
            command=self._on_engine_changed,
            fg_color=COLORS["bg_tertiary"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            height=36,
        ).grid(row=4, column=0, padx=24, pady=(0, 6), sticky="ew")

        self.engine_hint = ctk.CTkLabel(
            sidebar, text="Runs entirely on your device. No API key needed.",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["success"], anchor="w",
            wraplength=240, justify="left",
        )
        self.engine_hint.grid(row=5, column=0, padx=24, pady=(0, 14), sticky="ew")

        # API Key (hidden when local)
        self.api_label = self._section_label(sidebar, "API Key", row=6, return_widget=True)
        self.api_key_entry = ctk.CTkEntry(
            sidebar, show="●",
            placeholder_text="Optional — falls back to env var",
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=34,
        )
        self.api_key_entry.grid(row=7, column=0, padx=24, pady=(0, 14), sticky="ew")
        self._enable_clipboard(self.api_key_entry)

        # Max products (slider)
        self._section_label(sidebar, "Max Products", row=8)
        self.max_products_var = ctk.IntVar(value=20)
        slider_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        slider_row.grid(row=9, column=0, padx=24, pady=(0, 16), sticky="ew")
        slider_row.grid_columnconfigure(0, weight=1)
        self.max_products_slider = ctk.CTkSlider(
            slider_row, from_=5, to=200, number_of_steps=39,
            variable=self.max_products_var,
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            progress_color=COLORS["accent"],
            command=lambda v: self.max_products_label.configure(text=f"{int(v)}"),
        )
        self.max_products_slider.grid(row=0, column=0, sticky="ew")
        self.max_products_label = ctk.CTkLabel(
            slider_row, text="20",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"], width=40,
        )
        self.max_products_label.grid(row=0, column=1, padx=(8, 0))

        # Headless toggle
        self.headless_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            sidebar, text="Headless browser",
            variable=self.headless_var,
            progress_color=COLORS["accent"],
            text_color=COLORS["text_primary"],
        ).grid(row=10, column=0, padx=24, pady=(0, 16), sticky="w")

        # Output dir
        self._section_label(sidebar, "Output Folder", row=11)
        self.output_dir_var = ctk.StringVar(value="output")
        out_entry = ctk.CTkEntry(
            sidebar, textvariable=self.output_dir_var,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=34,
        )
        out_entry.grid(row=12, column=0, padx=24, pady=(0, 16), sticky="ew")
        self._enable_clipboard(out_entry)

        # Footer
        ctk.CTkLabel(
            sidebar, text=f"{APP_NAME} · Playwright · OCR",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
        ).grid(row=31, column=0, padx=24, pady=16, sticky="sw")

    def _section_label(self, parent, text: str, row: int, return_widget: bool = False):
        lbl = ctk.CTkLabel(
            parent, text=text.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_muted"], anchor="w",
        )
        lbl.grid(row=row, column=0, padx=24, pady=(0, 4), sticky="ew")
        if return_widget:
            return lbl
        return None

    def _on_engine_changed(self, label: str) -> None:
        eid = ENGINE_LABEL_TO_ID.get(label, "local")
        if eid == "local":
            self.engine_hint.configure(
                text="Runs entirely on your device. No API key needed.",
                text_color=COLORS["success"],
            )
            self.api_key_entry.configure(state="disabled", placeholder_text="Not required")
            self.api_key_entry.delete(0, "end")
        elif eid == "ollama":
            self.engine_hint.configure(
                text="Requires `ollama serve` running locally with a vision model (e.g. `ollama pull llava`).",
                text_color=COLORS["text_secondary"],
            )
            self.api_key_entry.configure(state="disabled", placeholder_text="Not required")
        else:
            env = ENGINE_ENV_KEY.get(eid, "")
            self.engine_hint.configure(
                text=f"Cloud engine. Provide an API key or set {env} in your environment.",
                text_color=COLORS["text_secondary"],
            )
            self.api_key_entry.configure(state="normal", placeholder_text=f"Optional — uses {env}")
            cur = self.api_key_entry.get()
            if not cur and env and (k := os.getenv(env)):
                self.api_key_entry.insert(0, k)

    # ---------- Main panel ----------
    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Extract products from any shopping page",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            header,
            text=(
                "Paste a URL — Pluck renders the page, crops product cards, and extracts "
                "name, price, discount, and any custom field you describe."
            ),
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"], anchor="w",
            wraplength=900, justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

        # URL row
        input_row = ctk.CTkFrame(main, fg_color=COLORS["bg_secondary"], corner_radius=14)
        input_row.grid(row=1, column=0, sticky="ew", padx=32, pady=(20, 8))
        input_row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Paste a shopping URL here",
            fg_color="transparent",
            border_color=COLORS["bg_secondary"],
            border_width=0,
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=14),
            height=52,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(20, 8), pady=8)
        self.url_entry.bind("<Return>", lambda _e: self._on_run_clicked())
        self._enable_clipboard(self.url_entry)

        # Paste button — explicit, in case keyboard shortcut is unfamiliar
        self.paste_button = ctk.CTkButton(
            input_row, text="Paste",
            command=self._paste_to_url,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12, weight="bold"),
            height=40, width=80, corner_radius=10,
        )
        self.paste_button.grid(row=0, column=1, padx=(0, 8), pady=8)

        self.run_button = ctk.CTkButton(
            input_row, text="Extract  →",
            command=self._on_run_clicked,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40, width=130, corner_radius=10,
        )
        self.run_button.grid(row=0, column=2, padx=(0, 12), pady=8)

        # Custom instructions
        instr_frame = ctk.CTkFrame(main, fg_color=COLORS["bg_secondary"], corner_radius=14)
        instr_frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 16))
        instr_frame.grid_columnconfigure(0, weight=1)

        instr_header = ctk.CTkFrame(instr_frame, fg_color="transparent")
        instr_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 4))
        instr_header.grid_columnconfigure(0, weight=1)
        self.instr_title = ctk.CTkLabel(
            instr_header,
            text="Custom Instructions (optional)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        )
        self.instr_title.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            instr_header,
            text="e.g. 'extract size, color, material' / 'include brand and rating'",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"], anchor="e",
        ).grid(row=0, column=1, sticky="e")

        self.instructions_text = ctk.CTkTextbox(
            instr_frame,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12),
            corner_radius=10, height=80, wrap="word",
        )
        self.instructions_text.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        self._enable_clipboard(self.instructions_text)

        # Body: log + results
        body = ctk.CTkFrame(main, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=32, pady=(0, 24))
        body.grid_columnconfigure(0, weight=1, uniform="body")
        body.grid_columnconfigure(1, weight=2, uniform="body")
        body.grid_rowconfigure(0, weight=1)

        log_panel = ctk.CTkFrame(body, fg_color=COLORS["bg_secondary"], corner_radius=14)
        log_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            log_panel, text="Progress Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=0, column=0, padx=18, pady=(16, 4), sticky="ew")

        self.status_label = ctk.CTkLabel(
            log_panel, text="● Idle",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"], anchor="w",
        )
        self.status_label.grid(row=1, column=0, padx=18, pady=(0, 8), sticky="ew")

        self.log_text = ctk.CTkTextbox(
            log_panel,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(family="Menlo", size=11),
            corner_radius=10, wrap="word",
        )
        self.log_text.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.log_text.configure(state="disabled")

        result_panel = ctk.CTkFrame(body, fg_color=COLORS["bg_secondary"], corner_radius=14)
        result_panel.grid(row=0, column=1, sticky="nsew")
        result_panel.grid_columnconfigure(0, weight=1)
        result_panel.grid_rowconfigure(2, weight=1)

        result_header = ctk.CTkFrame(result_panel, fg_color="transparent")
        result_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        result_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            result_header, text="Results",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.result_count_label = ctk.CTkLabel(
            result_header, text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        self.result_count_label.grid(row=0, column=1, sticky="e")

        actions = ctk.CTkFrame(result_panel, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 8))
        for i in range(3):
            actions.grid_columnconfigure(i, weight=1)
        self.open_folder_btn = ctk.CTkButton(
            actions, text="Open Folder", command=self._open_output_folder,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            text_color=COLORS["text_primary"], height=32, corner_radius=8, state="disabled",
        )
        self.open_folder_btn.grid(row=0, column=0, padx=4, sticky="ew")
        self.open_json_btn = ctk.CTkButton(
            actions, text="View JSON", command=lambda: self._open_file("results.json"),
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            text_color=COLORS["text_primary"], height=32, corner_radius=8, state="disabled",
        )
        self.open_json_btn.grid(row=0, column=1, padx=4, sticky="ew")
        self.open_csv_btn = ctk.CTkButton(
            actions, text="View CSV", command=lambda: self._open_file("results.csv"),
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["border"],
            text_color=COLORS["text_primary"], height=32, corner_radius=8, state="disabled",
        )
        self.open_csv_btn.grid(row=0, column=2, padx=4, sticky="ew")

        self.results_scroll = ctk.CTkScrollableFrame(
            result_panel, fg_color=COLORS["bg_tertiary"], corner_radius=10,
        )
        self.results_scroll.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.results_scroll.grid_columnconfigure((0, 1, 2), weight=1)

        self._show_empty_results()

    def _show_empty_results(self) -> None:
        for w in self.results_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.results_scroll,
            text="No results yet.\nPaste a URL above and click Extract.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"], justify="center",
        ).grid(row=0, column=0, columnspan=3, padx=40, pady=80)

    # ---------- Plan / subscription ----------
    def _refresh_plan_badge(self) -> None:
        info = plan_info(self.license.plan)
        used = self.usage.today()
        limit = info["daily_limit"]
        usage_part = f"{used} today" if limit is None else f"{used}/{limit} today"
        accent = COLORS["accent"] if self.license.plan != Plan.FREE else COLORS["text_secondary"]
        self.plan_badge.configure(
            text=f"  ●  {info['label']}   ·   {usage_part}   ›",
            text_color=accent,
        )

    def _apply_plan_gating(self) -> None:
        info = plan_info(self.license.plan)
        max_allowed = info["max_products"]
        cur = int(self.max_products_var.get())
        if cur > max_allowed:
            self.max_products_var.set(max_allowed)
            self.max_products_label.configure(text=str(max_allowed))
        self.max_products_slider.configure(to=max_allowed)
        if info["custom_instructions"]:
            self.instr_title.configure(
                text="Custom Instructions (optional)",
                text_color=COLORS["text_primary"],
            )
            self.instructions_text.configure(state="normal")
        else:
            self.instructions_text.configure(state="normal")
            self.instructions_text.delete("1.0", "end")
            self.instructions_text.configure(state="disabled")
            self.instr_title.configure(
                text="Custom Instructions — upgrade to Pro to unlock",
                text_color=COLORS["warning"],
            )

    def _open_subscription_dialog(self) -> None:
        dlg = SubscriptionDialog(self, self.license_mgr, self.license, self._on_plan_changed)
        dlg.grab_set()
        self.wait_window(dlg)

    def _on_plan_changed(self, new_license) -> None:
        self.license = new_license
        self._refresh_plan_badge()
        self._apply_plan_gating()
        self._append_log(f"Plan updated: {plan_info(self.license.plan)['label']}")

    # ---------- Clipboard / paste ----------
    def _paste_to_url(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            self._append_log("Clipboard is empty.")
            return
        text = text.strip()
        if not text:
            return
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, text)
        self.url_entry.focus_set()

    def _enable_clipboard(self, widget) -> None:
        inner = getattr(widget, "_entry", None) or getattr(widget, "_textbox", None) or widget

        def make(ev):
            def handler(_e=None):
                try:
                    inner.event_generate(ev)
                except Exception:
                    pass
                return "break"
            return handler

        bindings = [
            ("<Command-c>", "<<Copy>>"), ("<Command-C>", "<<Copy>>"),
            ("<Command-v>", "<<Paste>>"), ("<Command-V>", "<<Paste>>"),
            ("<Command-x>", "<<Cut>>"), ("<Command-X>", "<<Cut>>"),
            ("<Command-a>", "<<SelectAll>>"), ("<Command-A>", "<<SelectAll>>"),
            ("<Control-c>", "<<Copy>>"), ("<Control-v>", "<<Paste>>"),
            ("<Control-x>", "<<Cut>>"), ("<Control-a>", "<<SelectAll>>"),
        ]
        for key, ev in bindings:
            try:
                inner.bind(key, make(ev))
            except Exception:
                pass
        for btn in ("<Button-2>", "<Button-3>", "<Control-Button-1>"):
            inner.bind(btn, lambda e, w=inner: self._show_context_menu(e, w))

    def _show_context_menu(self, event, widget) -> None:
        menu = tk.Menu(
            self, tearoff=0,
            bg=COLORS["bg_tertiary"], fg=COLORS["text_primary"],
            activebackground=COLORS["accent"], activeforeground="#ffffff",
            borderwidth=0,
        )
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ---------- Run flow ----------
    def _on_run_clicked(self) -> None:
        if self.is_running:
            return
        url = self.url_entry.get().strip()
        if not url:
            self._append_log("Please paste a URL.")
            return

        ok, reason = can_extract(self.license.plan, self.usage.today())
        if not ok:
            self._append_log(f"⚠  {reason}")
            self._open_subscription_dialog()
            return

        engine = ENGINE_LABEL_TO_ID.get(self.engine_var.get(), "local")
        api_key = self.api_key_entry.get().strip() or None
        if engine in ENGINE_ENV_KEY and not api_key:
            api_key = os.getenv(ENGINE_ENV_KEY[engine])
            if not api_key:
                self._append_log(
                    f"⚠  No API key. Either paste one or switch to 'Local' engine."
                )
                return

        info = plan_info(self.license.plan)
        requested = int(self.max_products_var.get())
        max_products = clamp_max_products(self.license.plan, requested)
        if max_products < requested:
            self._append_log(f"ℹ  Capped to {max_products} products ({info['label']} plan).")

        instructions = (
            self.instructions_text.get("1.0", "end").strip()
            if info["custom_instructions"] else ""
        )

        self.is_running = True
        self.run_button.configure(state="disabled", text="Working...")
        self.status_label.configure(text="● Running", text_color=COLORS["accent"])
        self._clear_log()
        self._show_empty_results()
        self.result_count_label.configure(text="")
        for b in (self.open_folder_btn, self.open_json_btn, self.open_csv_btn):
            b.configure(state="disabled")

        cfg = {
            "url": url,
            "engine": engine,
            "api_key": api_key,
            "max_products": max_products,
            "headless": self.headless_var.get(),
            "output_dir": self.output_dir_var.get() or "output",
            "instructions": instructions or None,
        }
        threading.Thread(target=self._worker, args=(cfg,), daemon=True).start()

    def _worker(self, cfg: dict) -> None:
        def cb(msg: str) -> None:
            self.log_queue.put(msg)
        try:
            extractor = PluckExtractor(
                output_dir=Path(cfg["output_dir"]),
                max_products=cfg["max_products"],
                headless=cfg["headless"],
                engine=cfg["engine"],
                api_key=cfg["api_key"],
                progress_cb=cb,
                custom_instructions=cfg.get("instructions"),
            )
            result = asyncio.run(extractor.run(cfg["url"]))
            self.result_queue.put(("ok", result))
        except Exception as e:
            self.result_queue.put(("error", e))

    def _poll_queues(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        try:
            while True:
                kind, payload = self.result_queue.get_nowait()
                if kind == "ok":
                    self._on_extraction_done(payload)
                else:
                    self._on_extraction_error(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queues)

    def _on_extraction_done(self, result: ExtractionResult) -> None:
        self.last_result = result
        self.is_running = False
        self.run_button.configure(state="normal", text="Extract  →")
        self.status_label.configure(
            text=f"● Done — {len(result.products)} product(s)",
            text_color=COLORS["success"],
        )
        self.result_count_label.configure(text=f"{len(result.products)} products")
        for b in (self.open_folder_btn, self.open_json_btn, self.open_csv_btn):
            b.configure(state="normal")
        self.usage.increment()
        self._refresh_plan_badge()
        self._render_results(result)

    def _on_extraction_error(self, err: Exception) -> None:
        self.is_running = False
        self.run_button.configure(state="normal", text="Extract  →")
        self.status_label.configure(text="● Failed", text_color=COLORS["error"])
        self._append_log(f"Error: {err!r}")

    # ---------- Result rendering ----------
    def _render_results(self, result: ExtractionResult) -> None:
        for w in self.results_scroll.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        if not result.products:
            ctk.CTkLabel(
                self.results_scroll,
                text="No products extracted. The page may use unusual structure or "
                     "be blocked by bot detection. Check the log on the left.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                justify="center", wraplength=400,
            ).grid(row=0, column=0, columnspan=3, padx=40, pady=80)
            return

        cols = 3
        for idx, p in enumerate(result.products):
            r, c = divmod(idx, cols)
            self._render_card(self.results_scroll, r, c, p)

    def _render_card(self, parent, row: int, col: int, product) -> None:
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"], corner_radius=12)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        try:
            pil = Image.open(product.image_path)
            pil.thumbnail(THUMB_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
            self._thumb_refs.append(ctk_img)
            img_label = ctk.CTkLabel(card, image=ctk_img, text="")
        except Exception:
            img_label = ctk.CTkLabel(card, text="(no image)", text_color=COLORS["text_secondary"])
        img_label.grid(row=0, column=0, padx=10, pady=(10, 6))

        ctk.CTkLabel(
            card, text=product.name or "(unnamed)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            wraplength=200, justify="left", anchor="w",
        ).grid(row=1, column=0, padx=12, pady=(2, 0), sticky="ew")

        price_row = ctk.CTkFrame(card, fg_color="transparent")
        price_row.grid(row=2, column=0, padx=12, pady=(2, 4), sticky="ew")
        price_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            price_row, text=product.price or "-",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["accent"], anchor="w",
        ).grid(row=0, column=0, sticky="w")
        if product.discount_rate:
            ctk.CTkLabel(
                price_row, text=product.discount_rate,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["success"], anchor="e",
            ).grid(row=0, column=1, sticky="e")

        next_row = 3
        extra = getattr(product, "extra", None) or {}
        if extra:
            extra_box = ctk.CTkFrame(card, fg_color=COLORS["bg_tertiary"], corner_radius=8)
            extra_box.grid(row=next_row, column=0, padx=12, pady=(4, 6), sticky="ew")
            extra_box.grid_columnconfigure(1, weight=1)
            for i, (k, v) in enumerate(extra.items()):
                ctk.CTkLabel(
                    extra_box, text=str(k),
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=COLORS["text_secondary"], anchor="w",
                ).grid(row=i, column=0, padx=(8, 6), pady=2, sticky="w")
                ctk.CTkLabel(
                    extra_box, text=str(v),
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_primary"],
                    wraplength=140, justify="left", anchor="w",
                ).grid(row=i, column=1, padx=(0, 8), pady=2, sticky="ew")
            next_row += 1

        ctk.CTkLabel(
            card, text=f"#{product.id:03d}",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=next_row, column=0, padx=12, pady=(0, 10), sticky="w")

    # ---------- Helpers ----------
    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _open_output_folder(self) -> None:
        if not self.last_result:
            return
        self._reveal(Path(self.last_result.output_dir).resolve())

    def _open_file(self, name: str) -> None:
        if not self.last_result:
            return
        path = (Path(self.last_result.output_dir) / name).resolve()
        if path.exists():
            self._reveal(path)
        else:
            self._append_log(f"File not found: {path}")

    def _reveal(self, path: Path) -> None:
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            elif sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self._append_log(f"Failed to open: {e!r}")

    def _on_close(self) -> None:
        self.is_running = False
        self.destroy()


# ============================================================
#  Subscription dialog
# ============================================================
class SubscriptionDialog(ctk.CTkToplevel):
    def __init__(self, parent, license_mgr: LicenseManager, current_license, on_change) -> None:
        super().__init__(parent)
        self.title("Plans & Subscription")
        self.geometry("980x640")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_primary"])
        self.license_mgr = license_mgr
        self.current = current_license
        self.on_change = on_change

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="Choose your plan",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            header,
            text=(f"You're currently on the {plan_info(self.current.plan)['label']} plan."
                  + (f"  ·  Renews/expires {self.current.expires_at}"
                     if self.current.plan != Plan.FREE else "")),
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"], anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="nsew", padx=32, pady=(20, 8))
        for i in range(3):
            cards.grid_columnconfigure(i, weight=1, uniform="cards")
        cards.grid_rowconfigure(0, weight=1)

        for i, p in enumerate([Plan.FREE, Plan.PRO, Plan.TEAM]):
            self._build_card(cards, p, col=i)

        act = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=14)
        act.grid(row=2, column=0, sticky="ew", padx=32, pady=(8, 24))
        act.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            act, text="Have a license key?",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=0, column=0, padx=18, pady=(14, 0), sticky="w")
        ctk.CTkLabel(
            act,
            text="Paste your key below to activate. Format: PRO-YYYYMMDD-XXXX-XXXXXXXXXXXX",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"], anchor="w",
        ).grid(row=1, column=0, columnspan=3, padx=18, pady=(0, 8), sticky="w")

        self.key_entry = ctk.CTkEntry(
            act, placeholder_text="PRO-20271231-A1B2-c3d4e5f6789a",
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12), height=36,
        )
        self.key_entry.grid(row=2, column=0, columnspan=2, padx=(18, 8), pady=(0, 14), sticky="ew")
        self._enable_clipboard_for(self.key_entry)

        ctk.CTkButton(
            act, text="Activate", command=self._on_activate,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color="#ffffff", height=36, width=120, corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=2, column=2, padx=(0, 18), pady=(0, 14))

        self.activation_msg = ctk.CTkLabel(
            act, text="", font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"], anchor="w",
        )
        self.activation_msg.grid(row=3, column=0, columnspan=3, padx=18, pady=(0, 12), sticky="w")

    def _build_card(self, parent, plan: Plan, col: int) -> None:
        info = plan_info(plan)
        is_current = (plan == self.current.plan)
        border = COLORS["accent"] if is_current else COLORS["border"]

        card = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_secondary"],
            corner_radius=16, border_width=2, border_color=border,
        )
        card.grid(row=0, column=col, padx=8, pady=4, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        if is_current:
            ctk.CTkLabel(
                card, text="CURRENT PLAN",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=COLORS["accent"],
            ).grid(row=0, column=0, padx=20, pady=(16, 0), sticky="w")
        else:
            ctk.CTkLabel(card, text=" ", font=ctk.CTkFont(size=9))\
                .grid(row=0, column=0, padx=20, pady=(16, 0), sticky="w")

        ctk.CTkLabel(
            card, text=info["label"],
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"], anchor="w",
        ).grid(row=1, column=0, padx=20, pady=(2, 0), sticky="w")

        ctk.CTkLabel(
            card, text=info["tagline"],
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"], anchor="w",
        ).grid(row=2, column=0, padx=20, pady=(0, 12), sticky="w")

        price_row = ctk.CTkFrame(card, fg_color="transparent")
        price_row.grid(row=3, column=0, padx=20, pady=(0, 16), sticky="w")
        ctk.CTkLabel(
            price_row, text=info["price"],
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            price_row, text=f"  {info['period']}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=1, sticky="w", padx=(4, 0))

        feat = ctk.CTkFrame(card, fg_color="transparent")
        feat.grid(row=4, column=0, padx=20, pady=(0, 16), sticky="ew")
        feat.grid_columnconfigure(1, weight=1)
        for i, f in enumerate(info["features"]):
            ctk.CTkLabel(
                feat, text="✓", font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["success"],
            ).grid(row=i, column=0, padx=(0, 8), pady=2, sticky="w")
            ctk.CTkLabel(
                feat, text=f, font=ctk.CTkFont(size=12),
                text_color=COLORS["text_primary"],
                anchor="w", justify="left", wraplength=240,
            ).grid(row=i, column=1, sticky="ew", pady=2)

        if is_current:
            btn_text = "Current Plan"
            btn_state = "disabled"
            btn_cmd = lambda: None
            fg = COLORS["bg_tertiary"]
            hover = COLORS["bg_tertiary"]
        elif plan == Plan.FREE:
            btn_text = "Downgrade"
            btn_state = "normal"
            btn_cmd = self._on_downgrade
            fg = COLORS["bg_tertiary"]
            hover = COLORS["border"]
        else:
            btn_text = f"Subscribe — {info['price']}"
            btn_state = "normal"
            btn_cmd = lambda p=plan: self._on_subscribe(p)
            fg = COLORS["accent"]
            hover = COLORS["accent_hover"]

        ctk.CTkButton(
            card, text=btn_text, command=btn_cmd, state=btn_state,
            fg_color=fg, hover_color=hover,
            text_color="#ffffff" if plan != Plan.FREE and not is_current else COLORS["text_primary"],
            font=ctk.CTkFont(size=12, weight="bold"),
            height=40, corner_radius=10,
        ).grid(row=5, column=0, padx=20, pady=(8, 20), sticky="ew")

    def _on_subscribe(self, plan: Plan) -> None:
        url = plan_info(plan)["checkout_url"]
        if url:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        self.activation_msg.configure(
            text=f"Opening checkout for {plan_info(plan)['label']} in your browser. "
                 "Paste the license key you receive into the field above.",
            text_color=COLORS["text_secondary"],
        )

    def _on_downgrade(self) -> None:
        self.license_mgr.deactivate()
        new_lic = self.license_mgr.load()
        self.current = new_lic
        self.on_change(new_lic)
        self.activation_msg.configure(
            text="Switched to the Free plan.", text_color=COLORS["text_secondary"],
        )
        self.destroy()

    def _on_activate(self) -> None:
        key = self.key_entry.get().strip()
        if not key:
            self.activation_msg.configure(text="Enter a license key.", text_color=COLORS["error"])
            return
        lic = self.license_mgr.activate(key)
        if not lic:
            self.activation_msg.configure(
                text="Invalid or expired license key.", text_color=COLORS["error"],
            )
            return
        self.current = lic
        self.on_change(lic)
        self.activation_msg.configure(
            text=f"Activated {plan_info(lic.plan)['label']} — expires {lic.expires_at}.",
            text_color=COLORS["success"],
        )
        self.after(900, self.destroy)

    def _enable_clipboard_for(self, widget) -> None:
        inner = getattr(widget, "_entry", None) or widget
        for key, ev in [
            ("<Command-c>", "<<Copy>>"), ("<Command-v>", "<<Paste>>"),
            ("<Command-x>", "<<Cut>>"), ("<Command-a>", "<<SelectAll>>"),
            ("<Control-c>", "<<Copy>>"), ("<Control-v>", "<<Paste>>"),
            ("<Control-x>", "<<Cut>>"), ("<Control-a>", "<<SelectAll>>"),
        ]:
            try:
                inner.bind(key, lambda _e, e=ev: (inner.event_generate(e), "break")[1])
            except Exception:
                pass


def launch_gui() -> None:
    app = PluckGUI()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
