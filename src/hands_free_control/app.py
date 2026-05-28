# ============================================================
# app.py - Desktop product shell for hands-free control
# ============================================================

from __future__ import annotations

import os
import webbrowser
from importlib.util import find_spec
import tkinter as tk
from tkinter import messagebox, ttk

import cv2

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from hands_free_control.camera import camera_capture
from hands_free_control.config import AppConfig, DEFAULT_CUSTOM_GESTURE_MAPPING, DEFAULT_PROFILE_NAME, config, state
from hands_free_control.hand_tracker import hand_tracker
from hands_free_control.launcher import VoiceListener, _sync_screen_size
from hands_free_control import __product_name__, __version__
from hands_free_control.logger import log


APP_NAME = __product_name__
APP_VERSION = __version__
PREVIEW_SIZE = (760, 520)
ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "app-icon.ico")
SUPPORT_EMAIL = "x75labs@gmail.com"
CUSTOM_GESTURE_ROWS = (
    ("Pinch", "pinch"),
    ("Double pinch", "double_pinch"),
    ("Hold pinch", "pinch_hold"),
    ("Select hold", "select_hold"),
    ("Two fingers up", "scroll_up"),
    ("Two fingers down", "scroll_down"),
    ("Three fingers right", "swipe_right"),
    ("Three fingers left", "swipe_left"),
    ("Four fingers", "task_view"),
    ("Zoom out", "zoom_out"),
    ("Zoom in", "zoom_in"),
)
PROFILE_SETTING_KEYS = (
    "cursor_sensitivity",
    "click_threshold",
    "selection_hold_ms",
    "scroll_motion_multiplier",
    "scroll_speed_multiplier",
)
COLORS = {
    "bg": "#f5f7fb",
    "surface": "#ffffff",
    "surface_alt": "#f9fafb",
    "line": "#d9dee8",
    "text": "#111827",
    "muted": "#667085",
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "accent": "#2563eb",
    "accent_soft": "#eaf1ff",
    "danger": "#b42318",
    "preview": "#0f172a",
    "success": "#047857",
    "success_soft": "#ecfdf3",
    "warning": "#b54708",
    "warning_soft": "#fffaeb",
}

FONTS = {
    "title": ("Segoe UI Variable Display", 24, "bold"),
    "hero": ("Segoe UI", 13, "bold"),
    "section": ("Segoe UI", 11, "bold"),
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "button": ("Segoe UI", 10, "bold"),
}


def _available_voice_engines():
    engines = ["google"]
    if find_spec("whisper") is not None:
        engines.append("whisper")
    if find_spec("vosk") is not None:
        engines.append("vosk")
    return tuple(engines)


class CalibrationWizard(tk.Toplevel):
    """Full-screen interactive cursor mapping calibration wizard."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("X75 MotionOS Calibration Wizard")
        self.attributes("-fullscreen", True)
        self.configure(bg="#0b0f19")
        self.focus_force()

        self.steps = [
            ("Top-Left Corner", "Hold your hand at the TOP-LEFT limit of your comfortable camera view.", 0.1, 0.1),
            ("Top-Right Corner", "Hold your hand at the TOP-RIGHT limit of your comfortable camera view.", 0.9, 0.1),
            ("Bottom-Right Corner", "Hold your hand at the BOTTOM-RIGHT limit of your comfortable camera view.", 0.9, 0.9),
            ("Bottom-Left Corner", "Hold your hand at the BOTTOM-LEFT limit of your comfortable camera view.", 0.1, 0.9)
        ]
        self.current_step = 0
        self.captured_points = []
        self.countdown_val = 3
        self.countdown_timer = None

        self._build_ui()
        self.bind("<space>", lambda e: self.capture_point())
        self.bind("<Escape>", lambda e: self.close_wizard())
        
        # Start coordinate polling
        self.after(30, self._tick)
        # Start first step after window initialization
        self.after(500, self._run_step)

    def _build_ui(self):
        self.canvas = tk.Canvas(self, bg="#0b0f19", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Large instruction headers
        self.title_lbl = tk.Label(self.canvas, text="Calibration starting...", font=("Segoe UI", 28, "bold"), fg="#ffffff", bg="#0b0f19")
        self.title_lbl.place(relx=0.5, rely=0.35, anchor="center")

        self.desc_lbl = tk.Label(self.canvas, text="Please stand or sit comfortably in front of your camera.", font=("Segoe UI", 16), fg="#94a3b8", bg="#0b0f19", wraplength=800, justify="center")
        self.desc_lbl.place(relx=0.5, rely=0.45, anchor="center")

        self.countdown_lbl = tk.Label(self.canvas, text="3", font=("Segoe UI Variable Display", 96, "bold"), fg="#3b82f6", bg="#0b0f19")
        self.countdown_lbl.place(relx=0.5, rely=0.6, anchor="center")

        # Instructions / Help
        self.help_lbl = tk.Label(self.canvas, text="Hold index finger still to trigger countdown. Press SPACE to capture immediately. ESC to cancel.", font=("Segoe UI", 12), fg="#64748b", bg="#0b0f19")
        self.help_lbl.place(relx=0.5, rely=0.9, anchor="center")

        # Hand Status Label
        self.status_lbl = tk.Label(self.canvas, text="Waiting for hand...", font=("Segoe UI", 14, "bold"), fg="#f59e0b", bg="#0b0f19")
        self.status_lbl.place(relx=0.5, rely=0.75, anchor="center")

        # Markers
        # Target marker (red rings)
        self.target_marker = self.canvas.create_oval(-100, -100, -100, -100, outline="#ef4444", width=3)
        self.target_marker_inner = self.canvas.create_oval(-100, -100, -100, -100, fill="#ef4444", width=0)

        # Hand cursor marker (green tracking dot)
        self.hand_marker = self.canvas.create_oval(-100, -100, -100, -100, outline="#10b981", width=3, state="hidden")

    def _tick(self):
        if not self.winfo_exists():
            return

        hand_detected = state.get("hand_detected")
        finger_pos = state.get("finger_pos")

        if hand_detected and finger_pos:
            x, y = finger_pos
            w = self.winfo_width()
            h = self.winfo_height()
            if w > 1 and h > 1:
                # scale normalized coordinate to screen size
                cx = x * w
                cy = y * h
                self.canvas.coords(self.hand_marker, cx - 12, cy - 12, cx + 12, cy + 12)
                self.canvas.itemconfigure(self.hand_marker, state="normal")
                self.status_lbl.configure(text="Hand Tracked", fg="#10b981")
        else:
            self.canvas.itemconfigure(self.hand_marker, state="hidden")
            self.status_lbl.configure(text="No hand detected. Raise your hand in front of the camera.", fg="#f59e0b")

        self.after(30, self._tick)

    def _run_step(self):
        if not self.winfo_exists():
            return
        if self.current_step >= len(self.steps):
            self.finish_calibration()
            return

        name, desc, tx_pct, ty_pct = self.steps[self.current_step]
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1: w = self.winfo_screenwidth()
        if h <= 1: h = self.winfo_screenheight()

        tx = tx_pct * w
        ty = ty_pct * h

        self.canvas.coords(self.target_marker, tx - 30, ty - 30, tx + 30, ty + 30)
        self.canvas.coords(self.target_marker_inner, tx - 10, ty - 10, tx + 10, ty + 10)

        self.title_lbl.configure(text=f"Calibrating step {self.current_step + 1} of 4: {name}")
        self.desc_lbl.configure(text=desc)

        self.countdown_val = 3
        self.countdown_lbl.configure(text=str(self.countdown_val), fg="#3b82f6")

        if self.countdown_timer:
            self.after_cancel(self.countdown_timer)
        self.countdown_timer = self.after(1000, self.start_countdown)

    def start_countdown(self):
        if not self.winfo_exists():
            return

        hand_detected = state.get("hand_detected")
        if hand_detected:
            self.countdown_val -= 1
            if self.countdown_val <= 0:
                self.capture_point()
                return
            self.countdown_lbl.configure(text=str(self.countdown_val), fg="#3b82f6")
        else:
            self.countdown_lbl.configure(text="Hold Hand Up", fg="#ef4444")
            self.countdown_val = 3 # Reset countdown if hand is lost

        self.countdown_timer = self.after(1000, self.start_countdown)

    def capture_point(self):
        finger_pos = state.get("finger_pos")
        if not finger_pos:
            self.status_lbl.configure(text="Failed to capture! Make sure hand is detected.", fg="#ef4444")
            return

        self.captured_points.append(finger_pos)
        self.current_step += 1
        
        # Short visual success flash
        self.canvas.configure(bg="#064e3b")
        self.after(150, lambda: self.canvas.configure(bg="#0b0f19"))

        self._run_step()

    def finish_calibration(self):
        if len(self.captured_points) < 4:
            messagebox.showerror("Calibration Failed", "Failed to capture all 4 calibration points.")
            self.close_wizard()
            return

        tl, tr, br, bl = self.captured_points
        
        # Calculate boundaries
        x_min = (tl[0] + bl[0]) / 2.0
        x_max = (tr[0] + br[0]) / 2.0
        y_min = (tl[1] + tr[1]) / 2.0
        y_max = (bl[1] + br[1]) / 2.0

        if (x_max - x_min > 0.1) and (y_max - y_min > 0.1):
            config.map_x_min = round(max(0.0, min(1.0, x_min)), 3)
            config.map_x_max = round(max(0.0, min(1.0, x_max)), 3)
            config.map_y_min = round(max(0.0, min(1.0, y_min)), 3)
            config.map_y_max = round(max(0.0, min(1.0, y_max)), 3)
            config.save()
            
            log.info(f"Calibration successful: X=[{config.map_x_min:.3f}, {config.map_x_max:.3f}], Y=[{config.map_y_min:.3f}, {config.map_y_max:.3f}]")
            messagebox.showinfo("Calibration Successful", f"Calibration saved successfully!\n\nX limits: {config.map_x_min} - {config.map_x_max}\nY limits: {config.map_y_min} - {config.map_y_max}")
        else:
            log.error("Calibration error: Captured boundaries were too small or invalid.")
            messagebox.showerror("Calibration Error", "Captured workspace boundaries are too narrow. Please try calibrating again with wider movements.")

        self.close_wizard()

    def close_wizard(self):
        if self.countdown_timer:
            try:
                self.after_cancel(self.countdown_timer)
            except Exception:
                pass
        self.app.status_text.set("Calibration wizard closed.")
        self.destroy()


class HandsFreeApp(tk.Tk):
    """Beta desktop shell around the tracking engine."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        if os.path.exists(ICON_PATH):
            self.iconbitmap(ICON_PATH)
        self.minsize(1120, 700)
        self.geometry("1240x780")
        self.configure(bg=COLORS["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.voice_listener = VoiceListener()
        self._running = False
        self._preview_image = None
        self.voice_engines = _available_voice_engines()

        self._build_variables()
        self._ensure_profiles()
        self._build_styles()
        self._build_ui()
        self.after(33, self._update_preview)
        self.after(250, self._update_status)

    def _build_variables(self):
        self.gestures_enabled = tk.BooleanVar(value=config.gestures_enabled)
        self.voice_enabled = tk.BooleanVar(value=config.voice_enabled)
        self.wake_word_mode = tk.BooleanVar(value=config.wake_word_mode)
        self.dangerous_voice = tk.BooleanVar(value=config.dangerous_voice_commands_enabled)
        self.voice_engine = tk.StringVar(value=config.voice_engine)
        self.wake_word = tk.StringVar(value=config.wake_word)
        self.camera_index = tk.IntVar(value=config.camera_index)
        self.cursor_sensitivity = tk.DoubleVar(value=config.cursor_sensitivity)
        self.click_threshold = tk.DoubleVar(value=config.click_threshold)
        self.selection_hold_ms = tk.IntVar(value=config.selection_hold_ms)
        self.scroll_multiplier = tk.DoubleVar(value=config.scroll_motion_multiplier)
        self.scroll_speed_boost = tk.DoubleVar(value=config.scroll_speed_multiplier)
        self.status_text = tk.StringVar(value="Ready. Start when your camera and microphone are available.")
        self.custom_gesture_actions = {
            gesture_key: tk.StringVar(value=self._custom_action_for(gesture_key))
            for _label, gesture_key in CUSTOM_GESTURE_ROWS
        }
        self.profile_name = tk.StringVar(value=config.active_profile or DEFAULT_PROFILE_NAME)
        self.new_profile_name = tk.StringVar(value="")

    def _build_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(".", font=FONTS["body"], background=COLORS["bg"], foreground=COLORS["text"])
        self.style.configure("Shell.TFrame", background=COLORS["bg"])
        self.style.configure("Card.TFrame", background=COLORS["surface"], relief="flat")
        self.style.configure("Preview.TFrame", background=COLORS["preview"], relief="flat")
        self.style.configure("Toolbar.TFrame", background=COLORS["surface"])
        self.style.configure("TabBody.TFrame", background=COLORS["surface"])

        self.style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONTS["title"])
        self.style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=FONTS["body"])
        self.style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["section"])
        self.style.configure("Body.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["body"])
        self.style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=FONTS["small"])
        self.style.configure("Hint.TLabel", background=COLORS["surface"], foreground=COLORS["accent"], font=("Segoe UI", 11, "bold"))
        self.style.configure("Badge.TLabel", background=COLORS["accent_soft"], foreground=COLORS["accent"], font=("Segoe UI", 9, "bold"), padding=(10, 5))
        self.style.configure("Preview.TLabel", background=COLORS["preview"], foreground="#d8dee9", font=("Segoe UI", 11))
        self.style.configure("Status.TLabel", background=COLORS["surface_alt"], foreground=COLORS["text"], font=FONTS["small"], padding=(12, 7))
        self.style.configure("Accent.Status.TLabel", background=COLORS["accent_soft"], foreground=COLORS["accent"], font=FONTS["small"], padding=(12, 7))
        self.style.configure("Success.Status.TLabel", background=COLORS["success_soft"], foreground=COLORS["success"], font=FONTS["small"], padding=(12, 7))
        self.style.configure("Warning.Status.TLabel", background=COLORS["warning_soft"], foreground=COLORS["warning"], font=FONTS["small"], padding=(12, 7))

        self.style.configure("Primary.TButton", font=FONTS["button"], background=COLORS["primary"], foreground="#ffffff", borderwidth=0, focusthickness=0, padding=(18, 10))
        self.style.map("Primary.TButton", background=[("active", COLORS["primary_hover"]), ("pressed", COLORS["primary_hover"])])
        self.style.configure("Hero.TButton", font=FONTS["hero"], background=COLORS["primary"], foreground="#ffffff", borderwidth=0, focusthickness=0, padding=(22, 18))
        self.style.map("Hero.TButton", background=[("active", COLORS["primary_hover"]), ("pressed", COLORS["primary_hover"])])
        self.style.configure("Secondary.TButton", font=FONTS["button"], background="#eef2f7", foreground=COLORS["text"], borderwidth=0, focusthickness=0, padding=(18, 10))
        self.style.map("Secondary.TButton", background=[("active", "#e2e8f0"), ("pressed", "#d8dee8")])
        self.style.configure("Icon.TButton", font=("Segoe UI", 11, "bold"), background="#eef2f7", foreground=COLORS["text"], borderwidth=0, focusthickness=0, padding=(10, 7))
        self.style.map("Icon.TButton", background=[("active", "#e2e8f0"), ("pressed", "#d8dee8")])

        self.style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["body"], padding=(0, 5))
        self.style.map("TCheckbutton", background=[("active", COLORS["surface"])])
        self.style.configure("TEntry", fieldbackground="#ffffff", bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"], padding=(8, 6))
        self.style.configure("TCombobox", fieldbackground="#ffffff", bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"], padding=(8, 6))
        self.style.configure("TSpinbox", fieldbackground="#ffffff", bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"])
        self.style.configure("Horizontal.TScale", background=COLORS["surface"], troughcolor="#e8edf4")
        self.style.configure("TNotebook", background=COLORS["surface"], borderwidth=0, tabmargins=(0, 0, 0, 12))
        self.style.configure("TNotebook.Tab", background="#eef2f7", foreground=COLORS["muted"], font=FONTS["button"], padding=(16, 8))
        self.style.map("TNotebook.Tab", background=[("selected", COLORS["primary"]), ("active", "#e2e8f0")], foreground=[("selected", "#ffffff"), ("active", COLORS["text"])])
        self.style.configure("TSeparator", background=COLORS["line"])
        self.style.configure("Vertical.TScrollbar", background="#d8dee8", troughcolor=COLORS["surface"], borderwidth=0, arrowcolor=COLORS["muted"])

    def _build_ui(self):
        outer = ttk.Frame(self, padding=24, style="Shell.TFrame")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(1, weight=1)

        header = ttk.Frame(outer, style="Shell.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"{APP_VERSION}  |  Hands-free desktop control", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(header, text="?", command=self._show_how_to_use, style="Icon.TButton").grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 10))
        ttk.Label(header, textvariable=self.status_text, style="Status.TLabel").grid(row=0, column=2, rowspan=2, sticky="e")

        preview_frame = ttk.Frame(outer, padding=14, style="Card.TFrame")
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        preview_frame.rowconfigure(1, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        ttk.Label(preview_frame, text="Live Preview", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))

        preview_surface = ttk.Frame(preview_frame, padding=1, style="Preview.TFrame")
        preview_surface.grid(row=1, column=0, sticky="nsew")
        preview_surface.rowconfigure(0, weight=1)
        preview_surface.columnconfigure(0, weight=1)
        self.preview = ttk.Label(preview_surface, anchor="center", justify="center", text="Camera preview appears after Start.", style="Preview.TLabel")
        self.preview.grid(row=0, column=0, sticky="nsew")

        status_bar = ttk.Frame(preview_frame, style="Card.TFrame")
        status_bar.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for column in range(4):
            status_bar.columnconfigure(column, weight=1)
        self.hand_label = ttk.Label(status_bar, text="Hand: no", style="Status.TLabel")
        self.gesture_label = ttk.Label(status_bar, text="Gesture: none", style="Status.TLabel")
        self.voice_label = ttk.Label(status_bar, text="Voice: off", style="Status.TLabel")
        self.performance_label = ttk.Label(status_bar, text="FPS: 0.0", style="Status.TLabel")
        self.hand_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.gesture_label.grid(row=0, column=1, sticky="w", padx=(0, 8))
        self.voice_label.grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.performance_label.grid(row=0, column=3, sticky="e")

        controls = ttk.Frame(outer, padding=18, style="Card.TFrame")
        controls.grid(row=1, column=1, sticky="nsew")
        controls.rowconfigure(0, weight=1)
        controls.columnconfigure(0, weight=1)

        tabs = ttk.Notebook(controls)
        tabs.grid(row=0, column=0, sticky="nsew")

        main_tab = ttk.Frame(tabs, padding=14, style="TabBody.TFrame")
        advanced_tab = ttk.Frame(tabs, padding=0, style="TabBody.TFrame")
        custom_tab = ttk.Frame(tabs, padding=0, style="TabBody.TFrame")
        tabs.add(main_tab, text="Main")
        tabs.add(advanced_tab, text="Advanced Settings")
        tabs.add(custom_tab, text="Custom Gestures")

        self._build_main_tab(main_tab)
        self._build_advanced_tab(advanced_tab)
        self._build_custom_gestures_tab(custom_tab)

    def _build_main_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(7, weight=1)
        ttk.Label(parent, text="Session Control", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 14))

        ttk.Button(parent, text="Start", command=self.start_services, style="Hero.TButton").grid(row=1, column=0, sticky="ew", pady=(0, 12))
        
        # New Calibration wizard trigger
        ttk.Button(parent, text="Calibrate Workspace Mapping", command=self.start_calibration, style="Secondary.TButton").grid(row=2, column=0, sticky="ew", pady=(0, 12))
        
        ttk.Label(parent, text="Move your hand to control your cursor", anchor="center", style="Hint.TLabel").grid(row=3, column=0, sticky="n", pady=(6, 18))

        button_row = ttk.Frame(parent, style="TabBody.TFrame")
        button_row.grid(row=4, column=0, sticky="ew")
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text="Stop", command=self.stop_services, style="Secondary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(button_row, text="Save Settings", command=self.save_settings, style="Secondary.TButton").grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # New Scrollable Command History log
        ttk.Separator(parent).grid(row=5, column=0, sticky="ew", pady=(18, 12))
        ttk.Label(parent, text="Recent Activity Log", style="Section.TLabel").grid(row=6, column=0, sticky="w", pady=(0, 8))
        
        log_container = ttk.Frame(parent, style="TabBody.TFrame")
        log_container.grid(row=7, column=0, sticky="nsew")
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        
        self.activity_listbox = tk.Listbox(
            log_container,
            height=7,
            font=("Segoe UI", 9),
            bg="#f9fafb",
            fg="#111827",
            highlightcolor=COLORS["line"],
            selectbackground=COLORS["accent_soft"],
            selectforeground=COLORS["accent"],
            borderwidth=1,
            relief="solid"
        )
        self.activity_listbox.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.activity_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.activity_listbox.configure(yscrollcommand=scrollbar.set)

    def _build_advanced_tab(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        canvas = tk.Canvas(parent, background=COLORS["surface"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        content = ttk.Frame(canvas, padding=14, style="TabBody.TFrame")
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def match_content_width(event):
            canvas.itemconfigure(content_id, width=event.width)

        def on_mousewheel(event):
            if canvas.winfo_ismapped():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", match_content_width)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        content.columnconfigure(1, weight=1)
        row = 0
        row = self._section(content, "Gesture Settings", row)
        self._check(content, "Enable hand control", self.gestures_enabled, row)
        row += 1
        self._slider(content, "Cursor speed", self.cursor_sensitivity, 0.5, 2.5, row)
        row += 1
        self._slider(content, "Click sensitivity", self.click_threshold, 0.02, 0.08, row)
        row += 1
        self._slider(content, "Hold duration", self.selection_hold_ms, 80, 420, row)
        row += 1
        self._slider(content, "Scroll strength", self.scroll_multiplier, 80.0, 420.0, row)
        row += 1
        self._slider(content, "Scroll speed", self.scroll_speed_boost, 2.0, 24.0, row)
        row += 1

        row = self._section(content, "Voice Settings", row)
        self._check(content, "Enable voice commands", self.voice_enabled, row)
        row += 1
        self._check(content, "Require wake word", self.wake_word_mode, row)
        row += 1
        self._check(content, "Allow power commands", self.dangerous_voice, row)
        row += 1
        ttk.Label(content, text="Voice engine", style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        ttk.Combobox(content, textvariable=self.voice_engine, values=self.voice_engines, state="readonly").grid(row=row, column=1, sticky="ew", pady=7)
        row += 1
        ttk.Label(content, text="Wake word", style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        ttk.Entry(content, textvariable=self.wake_word).grid(row=row, column=1, sticky="ew", pady=7)
        row += 1

        row = self._section(content, "Performance Settings", row)
        ttk.Label(content, text="Camera", style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        ttk.Spinbox(content, from_=0, to=9, textvariable=self.camera_index, width=8).grid(row=row, column=1, sticky="w", pady=7)
        row += 1

        ttk.Separator(content).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(18, 12))
        row += 1
        ttk.Button(content, text="Reset to Defaults", command=self.reset_to_defaults, style="Secondary.TButton").grid(row=row, column=0, columnspan=2, sticky="ew")

    def _build_custom_gestures_tab(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        canvas = tk.Canvas(parent, background=COLORS["surface"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        content = ttk.Frame(canvas, padding=14, style="TabBody.TFrame")
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def match_content_width(event):
            canvas.itemconfigure(content_id, width=event.width)

        def on_mousewheel(event):
            if canvas.winfo_ismapped():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", match_content_width)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        heading = ttk.Frame(content, style="TabBody.TFrame")
        heading.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Custom Gestures", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(heading, text="BETA", style="Badge.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Label(
            content,
            text="Profiles save sensitivity and gesture mappings for shared laptops.",
            justify="left",
            wraplength=360,
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        self._build_profiles_section(content, 2)

        ttk.Separator(content).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 12))
        ttk.Label(content, text="Gesture Mapping", style="Section.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 8))

        list_frame = ttk.Frame(content, style="TabBody.TFrame")
        list_frame.grid(row=5, column=0, columnspan=2, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.columnconfigure(1, weight=1)

        ttk.Label(list_frame, text="Gesture", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(list_frame, text="Action", style="Section.TLabel").grid(row=0, column=1, sticky="w", pady=(0, 8), padx=(12, 0))

        actions = (
            "Left click",
            "Double click",
            "Right click",
            "Drag / select",
            "Scroll up",
            "Scroll down",
            "Switch desktop",
            "Previous desktop",
            "Task view",
            "Zoom in",
            "Zoom out",
            "No action",
        )
        for row, (gesture_label, gesture_key) in enumerate(CUSTOM_GESTURE_ROWS, start=1):
            self._custom_mapping_row(list_frame, row, gesture_label, self.custom_gesture_actions[gesture_key], actions)

        ttk.Separator(content).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(18, 12))
        action_row = ttk.Frame(content, style="TabBody.TFrame")
        action_row.grid(row=7, column=0, columnspan=2, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        ttk.Button(action_row, text="Reset Gesture Defaults", command=self.reset_custom_gestures, style="Secondary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(action_row, text="Save Custom Mapping", command=self._save_custom_gesture_preview, style="Secondary.TButton").grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_profiles_section(self, parent, row):
        profile_frame = ttk.Frame(parent, style="TabBody.TFrame")
        profile_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        profile_frame.columnconfigure(1, weight=1)
        profile_frame.columnconfigure(3, weight=1)

        ttk.Label(profile_frame, text="Profile", style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 8))
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_name, values=self._profile_names(), state="readonly")
        self.profile_combo.grid(row=0, column=1, columnspan=3, sticky="ew", pady=6)

        ttk.Label(profile_frame, text="New", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 8))
        ttk.Entry(profile_frame, textvariable=self.new_profile_name).grid(row=1, column=1, columnspan=3, sticky="ew", pady=6)

        ttk.Button(profile_frame, text="Load", command=self.load_profile, style="Secondary.TButton").grid(row=2, column=0, sticky="ew", pady=(8, 0), padx=(0, 6))
        ttk.Button(profile_frame, text="Save", command=self.save_profile, style="Secondary.TButton").grid(row=2, column=1, sticky="ew", pady=(8, 0), padx=6)
        ttk.Button(profile_frame, text="Create", command=self.create_profile, style="Secondary.TButton").grid(row=2, column=2, sticky="ew", pady=(8, 0), padx=6)
        ttk.Button(profile_frame, text="Delete", command=self.delete_profile, style="Secondary.TButton").grid(row=2, column=3, sticky="ew", pady=(8, 0), padx=(6, 0))

    def _custom_mapping_row(self, parent, row, gesture, variable, actions):
        ttk.Label(parent, text=gesture, style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        ttk.Combobox(parent, textvariable=variable, values=actions, state="readonly").grid(row=row, column=1, sticky="ew", pady=7, padx=(12, 0))

    def _ensure_profiles(self):
        if not isinstance(config.profiles, dict):
            config.profiles = {}
        if not config.profiles:
            config.profiles[DEFAULT_PROFILE_NAME] = self._profile_from_config()
        if config.active_profile not in config.profiles:
            config.active_profile = DEFAULT_PROFILE_NAME
        self.profile_name.set(config.active_profile)

    def _profile_names(self):
        names = sorted((config.profiles or {}).keys(), key=lambda name: (name != DEFAULT_PROFILE_NAME, name.lower()))
        return names or [DEFAULT_PROFILE_NAME]

    def _refresh_profile_combo(self):
        if hasattr(self, "profile_combo"):
            self.profile_combo.configure(values=self._profile_names())

    def _profile_from_config(self):
        return {
            "settings": {
                "cursor_sensitivity": config.cursor_sensitivity,
                "click_threshold": config.click_threshold,
                "selection_hold_ms": config.selection_hold_ms,
                "scroll_motion_multiplier": config.scroll_motion_multiplier,
                "scroll_speed_multiplier": config.scroll_speed_multiplier,
            },
            "custom_gesture_mapping": (config.custom_gesture_mapping or DEFAULT_CUSTOM_GESTURE_MAPPING).copy(),
        }

    def _profile_from_ui(self):
        return {
            "settings": {
                "cursor_sensitivity": round(float(self.cursor_sensitivity.get()), 3),
                "click_threshold": round(float(self.click_threshold.get()), 4),
                "selection_hold_ms": max(80, int(self.selection_hold_ms.get())),
                "scroll_motion_multiplier": round(float(self.scroll_multiplier.get()), 2),
                "scroll_speed_multiplier": round(float(self.scroll_speed_boost.get()), 2),
            },
            "custom_gesture_mapping": {
                gesture_key: variable.get()
                for gesture_key, variable in self.custom_gesture_actions.items()
            },
        }

    def _apply_profile(self, profile):
        settings = profile.get("settings", {}) if isinstance(profile, dict) else {}
        mapping = profile.get("custom_gesture_mapping", {}) if isinstance(profile, dict) else {}

        for key in PROFILE_SETTING_KEYS:
            if key in settings:
                setattr(config, key, settings[key])
        config.click_release_threshold = round(max(0.055, config.click_threshold + 0.02), 4)
        config.custom_gesture_mapping = DEFAULT_CUSTOM_GESTURE_MAPPING.copy()
        if isinstance(mapping, dict):
            config.custom_gesture_mapping.update(mapping)
        self._sync_variables_from_config()

    def save_profile(self):
        profile = self.profile_name.get().strip() or DEFAULT_PROFILE_NAME
        config.profiles[profile] = self._profile_from_ui()
        config.active_profile = profile
        self.profile_name.set(profile)
        config.save()
        self._refresh_profile_combo()
        self.status_text.set(f"Profile saved: {profile}")
        log.info(f"Profile saved: {profile}")

    def load_profile(self):
        profile = self.profile_name.get().strip() or DEFAULT_PROFILE_NAME
        if profile not in config.profiles:
            messagebox.showerror("Profile unavailable", f"Profile '{profile}' does not exist.")
            return
        self._apply_profile(config.profiles[profile])
        config.active_profile = profile
        config.save()
        self.profile_name.set(profile)
        self.status_text.set(f"Profile loaded: {profile}")
        log.info(f"Profile loaded: {profile}")

    def create_profile(self):
        profile = self.new_profile_name.get().strip()
        if not profile:
            messagebox.showerror("Profile name required", "Enter a profile name first.")
            return
        if profile in config.profiles and not messagebox.askyesno("Replace profile", f"Profile '{profile}' already exists. Replace it?"):
            return
        config.profiles[profile] = self._profile_from_ui()
        config.active_profile = profile
        self.profile_name.set(profile)
        self.new_profile_name.set("")
        config.save()
        self._refresh_profile_combo()
        self.status_text.set(f"Profile created: {profile}")
        log.info(f"Profile created: {profile}")

    def delete_profile(self):
        profile = self.profile_name.get().strip()
        if profile == DEFAULT_PROFILE_NAME:
            messagebox.showinfo("Default profile", "The Default profile cannot be deleted.")
            return
        if profile not in config.profiles:
            return
        if not messagebox.askyesno("Delete profile", f"Delete profile '{profile}'?"):
            return
        del config.profiles[profile]
        config.active_profile = DEFAULT_PROFILE_NAME
        self.profile_name.set(DEFAULT_PROFILE_NAME)
        self._apply_profile(config.profiles[DEFAULT_PROFILE_NAME])
        config.save()
        self._refresh_profile_combo()
        self.status_text.set(f"Profile deleted: {profile}")
        log.info(f"Profile deleted: {profile}")

    def _save_custom_gesture_preview(self):
        config.custom_gesture_mapping = {
            gesture_key: variable.get()
            for gesture_key, variable in self.custom_gesture_actions.items()
        }
        if isinstance(config.profiles, dict):
            profile = self.profile_name.get().strip() or DEFAULT_PROFILE_NAME
            config.profiles[profile] = self._profile_from_ui()
            config.active_profile = profile
        config.save()
        self.status_text.set("Custom gesture mapping saved.")
        messagebox.showinfo("Custom Gestures", "Custom gesture mapping saved. Press Start to use the active mappings.")

    def reset_custom_gestures(self):
        if not messagebox.askyesno("Reset gestures", "Reset custom gestures to the default mapping?"):
            return

        config.custom_gesture_mapping = DEFAULT_CUSTOM_GESTURE_MAPPING.copy()
        for gesture_key, action in config.custom_gesture_mapping.items():
            if gesture_key in self.custom_gesture_actions:
                self.custom_gesture_actions[gesture_key].set(action)
        if isinstance(config.profiles, dict):
            profile = self.profile_name.get().strip() or config.active_profile or DEFAULT_PROFILE_NAME
            config.profiles[profile] = self._profile_from_ui()
            config.save()
        self.status_text.set("Default gesture mapping restored.")
        log.info("Custom gesture mapping reset to defaults")

    def _custom_action_for(self, gesture_key):
        mapping = getattr(config, "custom_gesture_mapping", None) or DEFAULT_CUSTOM_GESTURE_MAPPING
        return mapping.get(gesture_key, DEFAULT_CUSTOM_GESTURE_MAPPING.get(gesture_key, "No action"))

    def _contact_support(self):
        subject = "X75%20MotionOS%20Beta%20Bug%20Report"
        body = (
            "Please%20describe%20the%20bug%2C%20your%20device%2C%20Windows%20version%2C%20camera%20model%2C%20"
            "and%20what%20you%20were%20doing%20when%20it%20happened."
        )
        webbrowser.open(f"mailto:{SUPPORT_EMAIL}?subject={subject}&body={body}")
        self.status_text.set("Opening support email...")

    def _show_how_to_use(self):
        dialog = tk.Toplevel(self)
        dialog.title("X75 MotionOS Manual")
        dialog.transient(self)
        dialog.resizable(True, True)
        dialog.configure(bg=COLORS["bg"])
        if os.path.exists(ICON_PATH):
            dialog.iconbitmap(ICON_PATH)

        shell = ttk.Frame(dialog, padding=14, style="Card.TFrame")
        shell.pack(fill="both", expand=True, padx=12, pady=12)
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)

        canvas = tk.Canvas(shell, background=COLORS["surface"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        body = ttk.Frame(canvas, padding=10, style="Card.TFrame")
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        body.columnconfigure(0, weight=1)

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def match_body_width(event):
            canvas.itemconfigure(body_id, width=event.width)

        canvas.bind("<Configure>", match_body_width)
        body.bind("<Configure>", update_scroll_region)

        row = 0
        ttk.Label(body, text="X75 MotionOS Manual", style="Section.TLabel").grid(row=row, column=0, sticky="w")
        row += 1
        ttk.Label(
            body,
            text="Free public beta. Start the app, keep your hand visible, and use gestures or voice commands to control your computer.",
            wraplength=560,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=row, column=0, sticky="ew", pady=(4, 18))
        row += 1

        def add_section(title, items):
            nonlocal row
            ttk.Label(body, text=title, style="Section.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 6))
            row += 1
            for left, right in items:
                line = ttk.Frame(body, style="Card.TFrame")
                line.grid(row=row, column=0, sticky="ew", pady=3)
                line.columnconfigure(1, weight=1)
                ttk.Label(line, text=left, width=22, style="Body.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
                ttk.Label(line, text=right, wraplength=380, justify="left", style="Muted.TLabel").grid(row=0, column=1, sticky="ew")
                row += 1

        add_section(
            "Gestures",
            (
                ("Move index finger", "Move cursor"),
                ("Thumb + index pinch", "Left click"),
                ("Two quick pinches", "Double click / select"),
                ("Hold pinch", "Drag or select items"),
                ("Index + middle close", "Enter scroll mode"),
                ("Move joined fingers", "Scroll faster or slower based on hand speed"),
                ("Three-finger swipe", "Switch desktop left or right"),
                ("Four fingers", "Task view"),
                ("Zoom gestures", "Zoom in or zoom out"),
            ),
        )
        add_section(
            "Voice Commands",
            (
                ("open notepad", "Open an app"),
                ("search for cats", "Search the web"),
                ("open website youtube.com", "Open a website"),
                ("type hello", "Type text"),
                ("dictate hello", "Type dictated text"),
                ("scroll up / down", "Scroll the current page"),
                ("volume up / down", "Change volume"),
                ("mute", "Toggle mute"),
                ("brightness up / down", "Change brightness when supported"),
                ("screenshot", "Take a screenshot"),
                ("task view", "Open task view"),
                ("lock screen", "Lock the computer"),
                ("shutdown / restart / sleep", "Blocked unless power commands are enabled in settings"),
            ),
        )
        add_section(
            "Publisher Credits",
            (
                ("Product", "X75 MotionOS"),
                ("Developer", "Hardil Solanki"),
                ("Publisher", "X75 Labs"),
                ("Support", SUPPORT_EMAIL),
            ),
        )

        button_row = ttk.Frame(body, style="Card.TFrame")
        button_row.grid(row=row, column=0, sticky="ew", pady=(18, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text="Contact Support", command=self._contact_support, style="Primary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(button_row, text="Close", command=dialog.destroy, style="Secondary.TButton").grid(row=0, column=1, sticky="ew", padx=(6, 0))

        dialog.geometry("680x640")
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.grab_set()

    def _section(self, parent, text, row):
        if row:
            ttk.Separator(parent).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 12))
            row += 1
        ttk.Label(parent, text=text, style="Section.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        return row + 1

    def _check(self, parent, text, variable, row):
        ttk.Checkbutton(parent, text=text, variable=variable).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)

    def _slider(self, parent, text, variable, start, end, row):
        ttk.Label(parent, text=text, style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        line = ttk.Frame(parent, style="Card.TFrame")
        line.grid(row=row, column=1, sticky="ew", pady=7)
        line.columnconfigure(0, weight=1)
        ttk.Scale(line, from_=start, to=end, variable=variable, orient="horizontal").grid(row=0, column=0, sticky="ew")
        ttk.Label(line, textvariable=variable, width=7, style="Muted.TLabel").grid(row=0, column=1, padx=(8, 0))

    def _apply_settings(self):
        config.gestures_enabled = self.gestures_enabled.get()
        config.voice_enabled = self.voice_enabled.get()
        config.wake_word_mode = self.wake_word_mode.get()
        config.dangerous_voice_commands_enabled = self.dangerous_voice.get()
        requested_engine = self.voice_engine.get().strip() or "google"
        config.voice_engine = requested_engine if requested_engine in self.voice_engines else "google"
        self.voice_engine.set(config.voice_engine)
        config.wake_word = self.wake_word.get().strip() or "computer"
        config.camera_index = max(0, int(self.camera_index.get()))
        config.cursor_sensitivity = round(float(self.cursor_sensitivity.get()), 3)
        config.click_threshold = round(float(self.click_threshold.get()), 4)
        config.click_release_threshold = round(max(0.055, config.click_threshold + 0.02), 4)
        config.selection_hold_ms = max(80, int(self.selection_hold_ms.get()))
        config.scroll_motion_multiplier = round(float(self.scroll_multiplier.get()), 2)
        config.scroll_speed_multiplier = round(float(self.scroll_speed_boost.get()), 2)
        config.custom_gesture_mapping = {
            gesture_key: variable.get()
            for gesture_key, variable in self.custom_gesture_actions.items()
        }

    def _sync_variables_from_config(self):
        self.gestures_enabled.set(config.gestures_enabled)
        self.voice_enabled.set(config.voice_enabled)
        self.wake_word_mode.set(config.wake_word_mode)
        self.dangerous_voice.set(config.dangerous_voice_commands_enabled)
        self.voice_engine.set(config.voice_engine if config.voice_engine in self.voice_engines else "google")
        self.wake_word.set(config.wake_word)
        self.camera_index.set(config.camera_index)
        self.cursor_sensitivity.set(config.cursor_sensitivity)
        self.click_threshold.set(config.click_threshold)
        self.selection_hold_ms.set(config.selection_hold_ms)
        self.scroll_multiplier.set(config.scroll_motion_multiplier)
        self.scroll_speed_boost.set(config.scroll_speed_multiplier)
        for gesture_key, variable in self.custom_gesture_actions.items():
            variable.set(self._custom_action_for(gesture_key))

    def reset_to_defaults(self):
        if not messagebox.askyesno("Reset settings", "Reset advanced settings to the default X75 MotionOS values?"):
            return

        defaults = AppConfig()
        for key, value in defaults.__dict__.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.voice_engine = config.voice_engine if config.voice_engine in self.voice_engines else "google"
        config.custom_gesture_mapping = DEFAULT_CUSTOM_GESTURE_MAPPING.copy()
        config.profiles = {DEFAULT_PROFILE_NAME: self._profile_from_config()}
        config.active_profile = DEFAULT_PROFILE_NAME
        config.save()
        self._sync_variables_from_config()
        self.profile_name.set(DEFAULT_PROFILE_NAME)
        self.new_profile_name.set("")
        self._refresh_profile_combo()
        self.status_text.set("Default settings restored.")
        log.info("Desktop app settings reset to defaults")

    def save_settings(self):
        self._apply_settings()
        if isinstance(config.profiles, dict):
            profile = self.profile_name.get().strip() or config.active_profile or DEFAULT_PROFILE_NAME
            config.profiles[profile] = self._profile_from_config()
            config.active_profile = profile
            self.profile_name.set(profile)
            self._refresh_profile_combo()
        config.save()
        self.status_text.set("Settings saved to settings.json.")
        log.info("Desktop app settings saved")

    def start_calibration(self):
        if not self._running:
            self.start_services()
            if not self._running:
                return
        CalibrationWizard(self)

    def start_services(self):
        if self._running:
            return

        self._apply_settings()
        state.reset_runtime()
        _sync_screen_size()
        camera_capture.start()
        if not state.get("camera_running"):
            available = camera_capture.list_cameras()
            self.status_text.set("Camera failed to start.")
            messagebox.showerror("Camera unavailable", f"Camera {config.camera_index} could not start.\nAvailable camera indices: {available}")
            return

        hand_tracker.start()
        self.voice_listener.start()
        self._running = True
        self.status_text.set("Running. Press Stop before closing or changing camera setup.")
        log.info("Desktop app services started")

    def stop_services(self):
        if not self._running and not state.get("camera_running"):
            return
        state.running = False
        self.voice_listener.stop()
        hand_tracker.stop()
        camera_capture.stop()
        self._running = False
        self._preview_image = None
        self.preview.configure(image="", text="Stopped. Start again when ready.")
        self.status_text.set("Stopped safely.")
        log.info("Desktop app services stopped")

    def _update_preview(self):
        frame = state.get("overlay_frame")
        if frame is None:
            frame = state.get("frame")

        if frame is not None and Image is not None and ImageTk is not None:
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(image)
            pil.thumbnail(PREVIEW_SIZE)
            self._preview_image = ImageTk.PhotoImage(pil)
            self.preview.configure(image=self._preview_image, text="")
        elif self._running and (Image is None or ImageTk is None):
            self.preview.configure(text="Install Pillow to show the in-app preview.")

        self.after(33, self._update_preview)

    def _friendly_gesture(self, gesture):
        names = {
            "none": "None",
            "pinch": "Click",
            "double_pinch": "Select",
            "drag": "Drag",
            "select": "Drag",
            "scroll_up": "Scroll up",
            "scroll_down": "Scroll down",
            "scroll": "Scroll",
        }
        key = str(gesture or "none").strip().lower()
        return names.get(key, key.replace("_", " ").title())

    def _update_status(self):
        hand_detected = bool(state.get("hand_detected"))
        raw_gesture = state.get("active_gesture") or "none"
        gesture = self._friendly_gesture(raw_gesture)
        gesture_active = gesture.lower() != "none"
        listening = bool(state.get("listening"))
        voice_running = bool(state.get("voice_running"))
        fps = state.get("fps") or 0.0
        latency = state.get("latency_ms") or 0.0

        self.hand_label.configure(
            text="Hand: detected" if hand_detected else "Hand: waiting",
            style="Success.Status.TLabel" if hand_detected else "Status.TLabel",
        )
        self.gesture_label.configure(
            text=f"Gesture detected: {gesture}" if gesture_active else "Gesture: ready",
            style="Accent.Status.TLabel" if gesture_active else "Status.TLabel",
        )
        self.voice_label.configure(
            text="Voice: Listening..." if listening else "Voice: on" if voice_running else "Voice: off",
            style="Accent.Status.TLabel" if listening else "Success.Status.TLabel" if voice_running else "Status.TLabel",
        )
        self.performance_label.configure(
            text=f"FPS: {fps:.1f} | {latency:.1f} ms",
            style="Warning.Status.TLabel" if self._running and fps and fps < 18 else "Status.TLabel",
        )

        if listening:
            self.status_text.set("Listening...")
        elif gesture_active:
            self.status_text.set(f"Gesture detected: {gesture}")
        elif hand_detected:
            self.status_text.set("Hand detected. Move your finger to control the cursor.")
        elif self._running:
            self.status_text.set("Tracking active. Show your hand to the camera.")
        else:
            self.status_text.set("Ready. Press Start to begin.")

        # Update activity log Listbox
        if hasattr(self, "activity_listbox"):
            history = state.command_history
            current_items = self.activity_listbox.get(0, tk.END)
            if list(current_items) != list(history):
                self.activity_listbox.delete(0, tk.END)
                for item in history:
                    self.activity_listbox.insert(tk.END, item)
                self.activity_listbox.see(tk.END)
        self.after(250, self._update_status)

    def _on_close(self):
        self.stop_services()
        self.destroy()


def main():
    try:
        app = HandsFreeApp()
    except tk.TclError as e:
        log.error(f"Desktop UI unavailable: {e}")
        print("Desktop UI unavailable. Falling back to the OpenCV preview launcher.")
        from hands_free_control.launcher import main as preview_main

        return preview_main()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
