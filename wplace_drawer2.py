import threading
import time
import os
import csv
import json
import random
import math
from dataclasses import dataclass
from collections import defaultdict
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, Listbox, SINGLE,
    filedialog, messagebox, Canvas, Scrollbar, END, ttk
)
from PIL import Image, ImageTk

# External control
try:
    import pyautogui
    pyautogui.FAILSAFE = True  # move mouse to (0,0) to abort
except Exception:
    pyautogui = None

# Enhanced site palette with better color coverage for improved matching
SITE_PALETTE = [
    # Extended grayscale range
    "#000000", "#111111", "#222222", "#333333", "#444444", "#555555", 
    "#666666", "#777777", "#888888", "#999999", "#AAAAAA", "#BBBBBB", 
    "#CCCCCC", "#DDDDDD", "#EEEEEE", "#FFFFFF",
    
    # Deep reds to bright reds
    "#4A0E11", "#6A0015", "#8B1538", "#B91C3C", "#DC2626", "#E53935", 
    "#EF4444", "#F87171", "#FCA5A5", "#FECACA",
    
    # Oranges with better transitions
    "#7C2D12", "#9A3412", "#C2410C", "#EA580C", "#F0641E", "#F97316", 
    "#FB923C", "#FDBA74", "#FED7AA", "#FFE4C4",
    
    # Yellows and warm tones
    "#A16207", "#CA8A04", "#EAB308", "#F4A300", "#FACC15", "#FDE047", 
    "#FEF08A", "#FEFCE8", "#FFE98A", "#FFFBEB",
    
    # Green spectrum expanded
    "#14532D", "#166534", "#15803D", "#16A34A", "#1E8E3E", "#22C55E", 
    "#27AE60", "#4ADE80", "#5BE36C", "#86EFAC", "#BBF7D0", "#DCFCE7",
    
    # Teals and cyans
    "#0F4C4C", "#0F766E", "#0D9488", "#0E8A6A", "#14B8A6", "#17BEBB", 
    "#2DD4BF", "#5EEAD4", "#99F6E4", "#CCFBF1",
    
    # Blues comprehensive range
    "#0C4A6E", "#075985", "#0369A1", "#0284C7", "#0096C7", "#0EA5E9", 
    "#1E40AF", "#2563EB", "#3B82F6", "#60A5FA", "#7C83FF", "#93C5FD", 
    "#BFDBFE", "#DBEAFE", "#7DD3FC",
    
    # Sky and light blues
    "#0284C7", "#0EA5E9", "#22B8CF", "#38BDF8", "#7DD3FC", "#BAE6FD", 
    "#E0F2FE", "#F0F9FF",
    
    # Purples extended
    "#4C1D95", "#5B21B6", "#6D28D9", "#7C3AED", "#7E22CE", "#8B5CF6", 
    "#8E44AD", "#A855F7", "#C084FC", "#D8B4FE", "#E9D5FF", "#FAF5FF",
    
    # Pinks and magentas
    "#831843", "#9D174D", "#BE185D", "#C2185B", "#E91E63", "#EC4899", 
    "#F472B6", "#F9A8D4", "#FBCFE8", "#FCE7F3",
    
    # Violets
    "#6B21A8", "#7E22CE", "#8B5A96", "#9B59B6", "#A855F7", "#B794F6", 
    "#C4A8E8", "#DDD6FE", "#EDE9FE",
    
    # Browns and earth tones
    "#451A03", "#54350A", "#6B3F2C", "#78350F", "#8D5A3A", "#92400E", 
    "#A16207", "#B45309", "#D97706", "#E6A57E", "#FBBF24",
    
    # Peach and coral tones
    "#FF6B6B", "#FF8E8E", "#FFB38A", "#FFC5A3", "#FFD7BB", "#FFE9D4", 
    "#FFF2E7", "#FFFAF5",
    
    # Additional useful colors
    "#2F1B69", "#3730A3", "#4338CA", "#5147E5", "#6366F1", "#818CF8", 
    "#A78BFA", "#C7D2FE", "#E0E7FF"
]

@dataclass
class Pixel:
    x: int
    y: int
    hex_color: str

def rgb_to_hex(rgb):
    r, g, b = rgb[:3]
    return f"#{r:02X}{g:02X}{b:02X}"

def hex_to_rgb(hx: str):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

# --- Color science helpers (OKLab) for perceptual distance ---
# Reference: https://bottosson.github.io/posts/oklab/

def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def _linear_to_oklab(r: float, g: float, b: float):
    # r,g,b are linear [0..1]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_ = l ** (1/3)
    m_ = m ** (1/3)
    s_ = s ** (1/3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return (L, a, b2)

def _rgb_to_oklab(r: int, g: int, b: int):
    rl = _srgb_to_linear(r)
    gl = _srgb_to_linear(g)
    bl = _srgb_to_linear(b)
    return _linear_to_oklab(rl, gl, bl)

def _oklab_dist(c1, c2):
    dL = c1[0] - c2[0]
    da = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return dL*dL + da*da + db*db

# --- Additional color distance algorithms ---

def _rgb_euclidean_distance(c1, c2):
    """Simple RGB Euclidean distance"""
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return dr*dr + dg*dg + db*db

def _xyz_to_lab(x, y, z):
    """Convert XYZ to Lab color space for Delta E CIE76"""
    # Observer: 2°, Illuminant: D65
    xn, yn, zn = 0.95047, 1.00000, 1.08883
    
    x = x / xn
    y = y / yn
    z = z / zn
    
    def f(t):
        return t**(1/3) if t > 0.008856 else (7.787 * t + 16/116)
    
    fx = f(x)
    fy = f(y)
    fz = f(z)
    
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    
    return L, a, b

def _rgb_to_xyz(r, g, b):
    """Convert RGB to XYZ color space"""
    # Normalize RGB values to [0,1]
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0
    
    # Apply gamma correction
    def gamma_correct(c):
        if c > 0.04045:
            return ((c + 0.055) / 1.055) ** 2.4
        else:
            return c / 12.92
    
    r = gamma_correct(r)
    g = gamma_correct(g)
    b = gamma_correct(b)
    
    # Convert to XYZ using sRGB matrix
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    return x, y, z

def _rgb_to_lab(r, g, b):
    """Convert RGB to Lab color space"""
    x, y, z = _rgb_to_xyz(r, g, b)
    return _xyz_to_lab(x, y, z)

def _delta_e_cie76(lab1, lab2):
    """Delta E CIE76 color difference"""
    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return (dL*dL + da*da + db*db) ** 0.5

# Color distance algorithm globals
COLOR_ALGORITHM = "oklab"  # options: "oklab", "deltaE", "rgb"

# Current palette (mutable) and precomputed arrays
CURRENT_PALETTE = list(SITE_PALETTE)
_PALETTE_RGB = [hex_to_rgb(hx) for hx in CURRENT_PALETTE]
_PALETTE_LAB = [_rgb_to_oklab(*rgb) for rgb in _PALETTE_RGB]
_PALETTE_CIE_LAB = [_rgb_to_lab(*rgb) for rgb in _PALETTE_RGB]

def set_palette(hex_list):
    global CURRENT_PALETTE, _PALETTE_RGB, _PALETTE_LAB, _PALETTE_CIE_LAB
    # sanitize and unique while preserving order
    seen = set()
    cleaned = []
    for hx in hex_list:
        if not isinstance(hx, str):
            continue
        if not hx.startswith('#'):
            hx = '#' + hx
        hx = hx[:7].upper()
        if len(hx) != 7:
            continue
        if hx in seen:
            continue
        seen.add(hx)
        cleaned.append(hx)
    if cleaned:
        CURRENT_PALETTE = cleaned
        _PALETTE_RGB = [hex_to_rgb(hx) for hx in CURRENT_PALETTE]
        _PALETTE_LAB = [_rgb_to_oklab(*rgb) for rgb in _PALETTE_RGB]
        _PALETTE_CIE_LAB = [_rgb_to_lab(*rgb) for rgb in _PALETTE_RGB]

def get_palette():
    return list(CURRENT_PALETTE)

def set_color_algorithm(algorithm: str):
    """Set the color distance algorithm to use"""
    global COLOR_ALGORITHM
    if algorithm in ["oklab", "deltaE", "rgb"]:
        COLOR_ALGORITHM = algorithm

def nearest_palette_color(r: int, g: int, b: int) -> str:
    """Find the closest palette color using the selected algorithm"""
    global COLOR_ALGORITHM
    
    best_i = 0
    best_d = 1e9
    
    if COLOR_ALGORITHM == "oklab":
        # Use OKLab distance (perceptual)
        lab = _rgb_to_oklab(r, g, b)
        for i, labp in enumerate(_PALETTE_LAB):
            d = _oklab_dist(lab, labp)
            if d < best_d:
                best_d = d
                best_i = i
    
    elif COLOR_ALGORITHM == "deltaE":
        # Use Delta E CIE76
        lab = _rgb_to_lab(r, g, b)
        for i, labp in enumerate(_PALETTE_CIE_LAB):
            d = _delta_e_cie76(lab, labp)
            if d < best_d:
                best_d = d
                best_i = i
    
    elif COLOR_ALGORITHM == "rgb":
        # Use simple RGB Euclidean distance
        rgb = (r, g, b)
        for i, rgbp in enumerate(_PALETTE_RGB):
            d = _rgb_euclidean_distance(rgb, rgbp)
            if d < best_d:
                best_d = d
                best_i = i
    
    return CURRENT_PALETTE[best_i]

class ScrollableFrame(Frame):
    def __init__(self, parent, width=320, height=500):
        super().__init__(parent)
        self.canvas = Canvas(self, borderwidth=0, width=width, height=height)
        self.vsb = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.frame = Frame(self.canvas)
        self.frame_id = self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Mouse wheel support
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.frame_id, width=event.width)

    def _on_mousewheel(self, event):
        # Windows uses event.delta multiples of 120
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class WplaceDrawerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wplace Drawer (Testing Mode)")
        self.root.geometry("1120x720")
        
        # Bind hotkeys for calibration
        self.root.bind('<F1>', lambda e: self.set_tl())
        self.root.bind('<F2>', lambda e: self.set_tr())
        self.root.bind('<F3>', lambda e: self.set_bl())
        self.root.bind('<F4>', lambda e: self.set_br())
        self.root.bind('<F5>', lambda e: self.set_palette_tl())
        self.root.bind('<F6>', lambda e: self.set_palette_br())
        self.root.bind('<F7>', lambda e: self.bind_palette_for_selected())
        self.root.bind('<F8>', lambda e: self.request_stop())
        
        # Focus on root to capture key events
        self.root.focus_set()

        # State
        self.src_image_path = None
        self.src_image = None  # PIL Image RGBA
        self.scaled_image = None  # PIL Image RGBA
        self.quant_image = None  # PIL Image after palette mapping
        self.preview_image = None  # ImageTk in canvas
        self.draw_mask = None  # 2D bool mask: True -> draw, False -> transparent/skip
        self.transparent_bg = (235, 235, 235)  # preview background for transparent cells
        # Options
        self.trim_margins = StringVar(value="1")  # "1" to enable auto-cropping of empty margins
        self.auto_maximize = StringVar(value="1")  # "1" to auto-maximize under limit
        self.enable_dither = StringVar(value="0")  # Floyd–Steinberg dithering
        self.alpha_threshold = StringVar(value="10")  # transparency threshold 0..255
        self.bg_tolerance = StringVar(value="12")  # background tolerance (0..255) for solid bg detection

        self.width_var = StringVar(value="8")
        self.height_var = StringVar(value="8")
        self.limit_var = StringVar(value="62")
        self.delay_var = StringVar(value="2.0")  # seconds before drawing starts
        self.click_sleep_var = StringVar(value="0.05")  # seconds between clicks

        # Calibration: screen positions of grid cell centers
        self.tl = None  # (x, y)
        self.tr = None  # (x, y)
        self.bl = None  # (x, y)
        self.br = None  # (x, y)

        # Palette used for quantization (starts with default)
        set_palette(SITE_PALETTE)
        # Palette bindings
        self.palette_coords = {}
        # Palette area (for auto-search): top-left, bottom-right
        self.pal_tl = None
        self.pal_br = None
        # Color distance algorithm variable
        self.color_algorithm_var = StringVar(value="oklab")
        # Highlight selected color on preview
        self.highlight_color = None

        # Drawing thread control
        self._draw_thread = None
        self._stop_flag = threading.Event()

        # UI layout
        top = Frame(root)
        top.pack(side="top", fill="x", padx=10, pady=8)

        Button(top, text="Открыть изображение", command=self.open_image).pack(side="left")

        Label(top, text="Ширина:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.width_var, width=6).pack(side="left")
        Label(top, text="Высота:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.height_var, width=6).pack(side="left")
        Label(top, text="Лимит пикселей:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.limit_var, width=8).pack(side="left")
        Button(top, text="Применить размер", command=self.apply_resize).pack(side="left", padx=(10, 0))

        # Options row
        Label(top, text="Опции:").pack(side="left", padx=(12, 4))
        from tkinter import Checkbutton
        Checkbutton(top, text="Обрезать поля", variable=self.trim_margins, onvalue="1", offvalue="0").pack(side="left")
        Checkbutton(top, text="Авто-максимум", variable=self.auto_maximize, onvalue="1", offvalue="0").pack(side="left")
        Checkbutton(top, text="Дизеринг", variable=self.enable_dither, onvalue="1", offvalue="0").pack(side="left")

        Label(top, text="Стартовая задержка, c:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.delay_var, width=6).pack(side="left")
        Label(top, text="Пауза между кликами, c:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.click_sleep_var, width=6).pack(side="left")

        # Info
        self.info_var = StringVar(value="Откройте изображение и задайте размеры (W*H ≤ 62)")
        Label(root, textvariable=self.info_var).pack(side="top", anchor="w", padx=10)
        # Advanced thresholds
        adv = Frame(root)
        adv.pack(side="top", fill="x", padx=10)
        Label(adv, text="Порог альфы:").pack(side="left")
        Entry(adv, textvariable=self.alpha_threshold, width=5).pack(side="left", padx=(0, 10))
        Label(adv, text="Толерантность фона:").pack(side="left")
        Entry(adv, textvariable=self.bg_tolerance, width=5).pack(side="left")

        # Canvas preview
        mid = Frame(root)
        mid.pack(fill="both", expand=True)
        self.canvas = Canvas(mid, bg="#2b2b2b")
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", self.refresh_preview)

        # Right panel (scrollable)
        right_scroll = ScrollableFrame(mid, width=320, height=620)
        right_scroll.pack(side="right", fill="y")
        right = right_scroll.frame

        Label(right, text="Обнаруженные цвета:").pack(anchor="w", padx=6, pady=(10, 4))
        self.colors_list = Listbox(right, selectmode=SINGLE, height=12)
        self.colors_list.pack(fill="x", padx=6)
        sb = Scrollbar(right, orient='vertical', command=self.colors_list.yview)
        self.colors_list.config(yscrollcommand=sb.set)
        self.colors_list.bind('<<ListboxSelect>>', self.on_color_select)

        Label(right, text="Калибровка (центры ячеек):").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="1) Top-Left (F1)", command=self.set_tl).pack(fill="x", padx=6, pady=2)
        Button(right, text="2) Top-Right (F2)", command=self.set_tr).pack(fill="x", padx=6, pady=2)
        Button(right, text="3) Bottom-Left (F3)", command=self.set_bl).pack(fill="x", padx=6, pady=2)
        Button(right, text="4) Bottom-Right (F4)", command=self.set_br).pack(fill="x", padx=6, pady=2)
        self.calib_lbl = Label(right, text="TL: -, TR: -, BL: -, BR: -")
        self.calib_lbl.pack(anchor="w", padx=6)

        Label(right, text="Экспорт:").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Экспорт CSV", command=self.export_csv).pack(fill="x", padx=6, pady=2)
        Button(right, text="Экспорт JSON", command=self.export_json).pack(fill="x", padx=6, pady=2)

        Label(right, text="Привязка палитры:").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Запомнить координату для выбранного цвета", command=self.bind_palette_for_selected).pack(fill="x", padx=6, pady=2)
        Button(right, text="Сохранить привязки", command=self.save_palette_bindings).pack(fill="x", padx=6, pady=2)
        Button(right, text="Загрузить привязки", command=self.load_palette_bindings).pack(fill="x", padx=6, pady=2)
        Label(right, text="Область палитры (для авто-поиска):").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="TL палитры (F5)", command=self.set_palette_tl).pack(fill="x", padx=6, pady=2)
        Button(right, text="BR палитры (F6)", command=self.set_palette_br).pack(fill="x", padx=6, pady=2)
        # Palette acquisition / load-save
        Label(right, text="Алгоритм подбора цвета:").pack(anchor="w", padx=6, pady=(12, 4))
        algo_frame = Frame(right)
        algo_frame.pack(fill="x", padx=6)
        Label(algo_frame, text="Алгоритм:").pack(side="left")
        self.algorithm_combo = ttk.Combobox(algo_frame, textvariable=self.color_algorithm_var, 
                                          values=["oklab", "deltaE", "rgb"], state="readonly", width=8)
        self.algorithm_combo.pack(side="left", padx=(4, 0))
        self.algorithm_combo.bind("<<ComboboxSelected>>", self.on_algorithm_change)
        
        Label(right, text="Палитра цветов:").pack(anchor="w", padx=6, pady=(12, 4))
        rowp = Frame(right)
        rowp.pack(fill="x", padx=6)
        Label(rowp, text="Размер:").pack(side="left")
        self.palette_k_var = StringVar(value="24")
        Entry(rowp, textvariable=self.palette_k_var, width=5).pack(side="left")
        
        # Palette management buttons
        Button(right, text="Оптимизировать палитру (анализ изображения)", command=self.optimize_palette_for_image).pack(fill="x", padx=6, pady=2)
        Button(right, text="Сбросить к расширенной палитре", command=self.reset_to_default_palette).pack(fill="x", padx=6, pady=2)
        Button(right, text="Собрать палитру из области", command=self.build_palette_from_screen).pack(fill="x", padx=6, pady=2)
        Button(right, text="Загрузить палитру JSON", command=self.load_palette_json).pack(fill="x", padx=6, pady=2)
        Button(right, text="Сохранить палитру JSON", command=self.save_palette_json).pack(fill="x", padx=6, pady=2)

        Label(right, text="Отрисовка:").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Нарисовать выбранный цвет", command=self.draw_selected_color).pack(fill="x", padx=6, pady=2)
        Button(right, text="Нарисовать все цвета (по порядку)", command=self.draw_all_colors).pack(fill="x", padx=6, pady=2)
        Button(right, text="Стоп", command=self.request_stop).pack(fill="x", padx=6, pady=(6, 2))

        Label(right, text="Подсказки:\nГорячие клавиши: F1-F4 - калибровка сетки\nF5-F6 - калибровка палитры, F7 - запомнить цвет\nF8 - стоп. Failsafe: мышь в левый верхний угол", justify="left").pack(anchor="w", padx=6, pady=(10, 6))

    # ---------- Image handling ----------
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[
                ("Изображения", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть изображение: {e}")
            return
        self.src_image_path = path
        self.src_image = img
        self.info_var.set(f"Загружено: {os.path.basename(path)} ({img.width}x{img.height})")
        self.apply_resize()

    def get_int(self, var: StringVar, default: int) -> int:
        try:
            v = int(var.get())
            if v <= 0:
                raise ValueError
            return v
        except Exception:
            return default

    def _detect_bg_color(self, img_rgba, tol: int):
        # Heuristic: use the top-left pixel (or median of 4 corners) as background candidate
        w, h = img_rgba.size
        px = img_rgba.load()
        corners = [px[0,0], px[w-1,0], px[0,h-1], px[w-1,h-1]]
        # pick the one with highest alpha as bg sample
        corners.sort(key=lambda p: p[3], reverse=True)
        r, g, b, a = corners[0]
        return (r, g, b, a)

    def _crop_empty_margins(self, img_rgba, alpha_thr: int, tol: int):
        w, h = img_rgba.size
        px = img_rgba.load()
        bg = self._detect_bg_color(img_rgba, tol)
        def is_empty(x, y):
            r, g, b, a = px[x, y]
            if a < alpha_thr:
                return True
            # close to bg color?
            dr = abs(r - bg[0]); dg = abs(g - bg[1]); db = abs(b - bg[2])
            return (dr + dg + db) <= 3 * tol
        top = 0
        while top < h and all(is_empty(x, top) for x in range(w)):
            top += 1
        if top == h:
            return img_rgba, (0, 0)  # fully empty
        bottom = h - 1
        while bottom >= 0 and all(is_empty(x, bottom) for x in range(w)):
            bottom -= 1
        left = 0
        while left < w and all(is_empty(left, y) for y in range(top, bottom+1)):
            left += 1
        right = w - 1
        while right >= 0 and all(is_empty(right, y) for y in range(top, bottom+1)):
            right -= 1
        cropped = img_rgba.crop((left, top, right+1, bottom+1))
        return cropped, (left, top)

    def _compute_fit_size(self, w_req, h_req, limit, src_w, src_h):
        # Preserve aspect ratio of src
        if self.auto_maximize.get() != "1":
            # clamp to limit if necessary by scaling down proportionally
            if w_req * h_req > limit:
                scale = (limit / (w_req * h_req)) ** 0.5
                w = max(1, int(w_req * scale))
                h = max(1, int(h_req * scale))
                return w, h
            return w_req, h_req
        # Auto maximize: compute the largest integer (w,h) under limit with src aspect
        aspect = src_w / src_h if src_h != 0 else 1.0
        # try base on width
        w = max(1, w_req)
        h = max(1, int(round(w / aspect)))
        if w * h > limit:
            # reduce until within limit
            scale = (limit / (w * h)) ** 0.5
            w = max(1, int(w * scale))
            h = max(1, int(round(w / aspect)))
        # try to grow until limit
        improved = True
        while improved:
            improved = False
            if (w+1) * int(round((w+1) / aspect)) <= limit:
                w += 1
                h = max(1, int(round(w / aspect)))
                improved = True
            elif (h+1) * int(round((h+1) * aspect)) <= limit:
                h += 1
                w = max(1, int(round(h * aspect)))
                improved = True
        return w, h

    def _quantize_to_palette(self, img_rgba, dither: bool, alpha_thr: int):
        w, h = img_rgba.size
        out = Image.new("RGB", (w, h))
        dst = out.load()
        src = img_rgba.load()
        mask = [[False for _ in range(w)] for _ in range(h)]
        if not dither:
            for yy in range(h):
                for xx in range(w):
                    r, g, b, a = src[xx, yy]
                    if a < alpha_thr:
                        mask[yy][xx] = False
                        dst[xx, yy] = self.transparent_bg
                    else:
                        mask[yy][xx] = True
                        hx = nearest_palette_color(r, g, b)
                        dst[xx, yy] = hex_to_rgb(hx)
            return out, mask
        # Floyd–Steinberg dithering in RGB space with perceptual mapping for target
        err = [[(0.0, 0.0, 0.0) for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                r, g, b, a = src[x, y]
                if a < alpha_thr:
                    mask[y][x] = False
                    dst[x, y] = self.transparent_bg
                    continue
                mask[y][x] = True
                er, eg, eb = err[y][x]
                nr = min(255, max(0, int(round(r + er))))
                ng = min(255, max(0, int(round(g + eg))))
                nb = min(255, max(0, int(round(b + eb))))
                hx = nearest_palette_color(nr, ng, nb)
                pr, pg, pb = hex_to_rgb(hx)
                dst[x, y] = (pr, pg, pb)
                dr = nr - pr; dg = ng - pg; db = nb - pb
                # distribute error
                def add_err(xx, yy, fr):
                    if 0 <= xx < w and 0 <= yy < h:
                        e0 = err[yy][xx]
                        err[yy][xx] = (e0[0] + dr * fr, e0[1] + dg * fr, e0[2] + db * fr)
                add_err(x+1, y,   7/16)
                add_err(x-1, y+1, 3/16)
                add_err(x,   y+1, 5/16)
                add_err(x+1, y+1, 1/16)
        return out, mask

    def apply_resize(self):
        if self.src_image is None:
            messagebox.showinfo("Нет изображения", "Сначала откройте изображение")
            return
        w_req = self.get_int(self.width_var, 8)
        h_req = self.get_int(self.height_var, 8)
        limit = self.get_int(self.limit_var, 62)
        alpha_thr = self.get_int(self.alpha_threshold, 10)
        tol = self.get_int(self.bg_tolerance, 12)
        img = self.src_image.convert("RGBA")
        # optional trim
        offset = (0, 0)
        if self.trim_margins.get() == "1":
            img, offset = self._crop_empty_margins(img, alpha_thr, tol)
        src_w, src_h = img.size
        # compute fit size
        w, h = self._compute_fit_size(w_req, h_req, limit, src_w, src_h)
        if w * h > limit:
            messagebox.showwarning("Лимит превышен", f"{w}x{h} = {w*h} > лимита {limit}")
            return
        self.scaled_image = img.resize((w, h), Image.NEAREST)
        # quantize
        self.quant_image, self.draw_mask = self._quantize_to_palette(
            self.scaled_image.convert("RGBA"),
            dither=(self.enable_dither.get()=="1"),
            alpha_thr=alpha_thr,
        )
        self.populate_colors()
        self.refresh_preview()
        trim_note = " (обрезано)" if self.trim_margins.get()=="1" and (offset != (0,0)) else ""
        self.info_var.set(f"Сетка {w}x{h} ({w*h}). Цветов: {self.colors_list.size()}" + trim_note)

    def populate_colors(self):
        self.colors_list.delete(0, END)
        if self.quant_image is None:
            return
        w, h = self.quant_image.size
        seen = {}
        data = self.quant_image.load()
        for y in range(h):
            for x in range(w):
                if self.draw_mask is not None and not self.draw_mask[y][x]:
                    continue
                r, g, b = data[x, y]
                hx = rgb_to_hex((r, g, b))
                if hx not in seen:
                    seen[hx] = 0
                seen[hx] += 1
        items = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
        for hx, cnt in items:
            self.colors_list.insert(END, f"{hx}  ({cnt})")
        if items:
            self.colors_list.selection_set(0)

    def get_pixels(self):
        if self.quant_image is None:
            return []
        w, h = self.quant_image.size
        pixels = []
        data = self.quant_image.load()
        for y in range(h):
            for x in range(w):
                if self.draw_mask is not None and not self.draw_mask[y][x]:
                    continue
                r, g, b = data[x, y]
                pixels.append(Pixel(x=x, y=y, hex_color=rgb_to_hex((r, g, b))))
        return pixels

    def group_pixels_by_color(self):
        groups = defaultdict(list)
        for p in self.get_pixels():
            groups[p.hex_color].append(p)
        return groups

    # ---------- Calibration ----------
    def set_tl(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        x, y = pyautogui.position()
        self.tl = (x, y)
        self.update_calib_label()

    def set_tr(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        x, y = pyautogui.position()
        self.tr = (x, y)
        self.update_calib_label()

    def set_bl(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        x, y = pyautogui.position()
        self.bl = (x, y)
        self.update_calib_label()

    def set_br(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        x, y = pyautogui.position()
        self.br = (x, y)
        self.update_calib_label()

    def update_calib_label(self):
        tl = f"TL: {self.tl}" if self.tl else "TL: -"
        tr = f"TR: {self.tr}" if self.tr else "TR: -"
        bl = f"BL: {self.bl}" if self.bl else "BL: -"
        br = f"BR: {self.br}" if self.br else "BR: -"
        self.calib_lbl.config(text=f"{tl}, {tr}, {bl}, {br}")

    def compute_cell_coords(self, x, y):
        if not self.tl or self.scaled_image is None:
            return None
        w, h = self.scaled_image.size
        # Prefer 3-point affine grid (TL, TR, BL). Fallback to TL/BR.
        if self.tr and self.bl:
            x0, y0 = self.tl
            tx, ty = self.tr
            bx, by = self.bl
            ux_x = 0 if w == 1 else (tx - x0) / (w - 1)
            ux_y = 0 if w == 1 else (ty - y0) / (w - 1)
            uy_x = 0 if h == 1 else (bx - x0) / (h - 1)
            uy_y = 0 if h == 1 else (by - y0) / (h - 1)
            sx = x0 + ux_x * x + uy_x * y
            sy = y0 + ux_y * x + uy_y * y
            return int(round(sx)), int(round(sy))
        if not self.br:
            return None
        (x0, y0), (x1, y1) = self.tl, self.br
        step_x = 0 if w == 1 else (x1 - x0) / (w - 1)
        step_y = 0 if h == 1 else (y1 - y0) / (h - 1)
        sx = x0 + step_x * x
        sy = y0 + step_y * y
        return int(round(sx)), int(round(sy))

    # ---------- Export ----------
    def export_csv(self):
        pixels = self.get_pixels()
        if not pixels:
            messagebox.showinfo("Нет данных", "Нет пикселей для экспорта")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                wcsv = csv.writer(f)
                wcsv.writerow(["x", "y", "hex_color"])  # header
                for p in pixels:
                    wcsv.writerow([p.x, p.y, p.hex_color])
            messagebox.showinfo("Готово", f"Сохранено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить CSV: {e}")

    def export_json(self):
        pixels = self.get_pixels()
        if not pixels:
            messagebox.showinfo("Нет данных", "Нет пикселей для экспорта")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            w, h = (self.quant_image.size if self.quant_image else (self.scaled_image.size if self.scaled_image else (0,0)))
            payload = {
                "width": w,
                "height": h,
                "pixels": [p.__dict__ for p in pixels],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Готово", f"Сохранено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить JSON: {e}")

    # ---------- Drawing ----------
    def parse_float(self, var: StringVar, default: float) -> float:
        try:
            v = float(var.get())
            return max(0.0, v)
        except Exception:
            return default

    def _draw_pixels(self, pixels):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        delay = self.parse_float(self.delay_var, 2.0)
        sleep_between = self.parse_float(self.click_sleep_var, 0.05)
        for _ in range(int(delay * 10)):
            if self._stop_flag.is_set():
                return
            time.sleep(0.1)
        for p in pixels:
            if self._stop_flag.is_set():
                return
            tgt = self.compute_cell_coords(p.x, p.y)
            if tgt is None:
                return
            try:
                pyautogui.moveTo(tgt[0], tgt[1])
                pyautogui.click()
                time.sleep(sleep_between)
            except Exception:
                return

    def start_draw_thread(self, pixels):
        if not pixels:
            messagebox.showinfo("Нет пикселей", "Нечего рисовать")
            return
        if not self.tl or not self.br:
            messagebox.showwarning("Нет калибровки", "Укажите TL и BR центры ячеек перед рисованием")
            return
        if self._draw_thread and self._draw_thread.is_alive():
            messagebox.showinfo("Уже идёт", "Дождитесь завершения или нажмите Стоп")
            return
        self._stop_flag.clear()
        self._draw_thread = threading.Thread(target=self._draw_pixels, args=(pixels,), daemon=True)
        self._draw_thread.start()

    def select_palette_color(self, hx: str):
        if pyautogui is None:
            return
        # If explicit binding exists — use it
        pos = self.palette_coords.get(hx)
        if not pos:
            # try auto-find in palette area by screenshot
            pos = self.auto_find_palette_color(hx)
        if not pos:
            return
        try:
            pyautogui.moveTo(pos[0], pos[1])
            pyautogui.click()
            time.sleep(0.2)
        except Exception:
            pass

    def draw_selected_color(self):
        groups = self.group_pixels_by_color()
        if not groups:
            messagebox.showinfo("Нет данных", "Нет пикселей для рисования")
            return
        sel = self.colors_list.curselection()
        if not sel:
            messagebox.showinfo("Не выбран цвет", "Выберите цвет из списка справа")
            return
        item = self.colors_list.get(sel[0])
        hx = item.split()[0]
        pixels = groups.get(hx, [])
        self.select_palette_color(hx)
        self.start_draw_thread(pixels)

    def start_draw_thread_with_color_switch(self, sequence):
        if not sequence:
            return
        if not self.tl or not self.br:
            messagebox.showwarning("Нет калибровки", "Укажите TL и BR центры ячеек перед рисованием")
            return
        if self._draw_thread and self._draw_thread.is_alive():
            messagebox.showinfo("Уже идёт", "Дождитесь завершения или нажмите Стоп")
            return
        self._stop_flag.clear()
        self._draw_thread = threading.Thread(target=self._draw_with_switch_worker, args=(sequence,), daemon=True)
        self._draw_thread.start()

    def _draw_with_switch_worker(self, sequence):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        delay = self.parse_float(self.delay_var, 2.0)
        sleep_between = self.parse_float(self.click_sleep_var, 0.05)
        for _ in range(int(delay * 10)):
            if self._stop_flag.is_set():
                return
            time.sleep(0.1)
        for item in sequence:
            if self._stop_flag.is_set():
                return
            if isinstance(item, tuple) and item[0] == "COLOR":
                hx = item[1]
                self.select_palette_color(hx)
                continue
            tgt = self.compute_cell_coords(item.x, item.y)
            if tgt is None:
                return
            try:
                pyautogui.moveTo(tgt[0], tgt[1])
                pyautogui.click()
                time.sleep(sleep_between)
            except Exception:
                return

    def draw_all_colors(self):
        groups = self.group_pixels_by_color()
        if not groups:
            messagebox.showinfo("Нет данных", "Нет пикселей для рисования")
            return
        order = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        seq = []
        for hx, arr in order:
            seq.append(("COLOR", hx))
            seq.extend(arr)
        self.start_draw_thread_with_color_switch(seq)

    def request_stop(self):
        self._stop_flag.set()

    # ---------- Palette binding save/load ----------
    def bind_palette_for_selected(self):
        sel = self.colors_list.curselection()
        if not sel:
            messagebox.showinfo("Не выбран цвет", "Выберите цвет справа")
            return
        item = self.colors_list.get(sel[0])
        hx = item.split()[0]
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        x, y = pyautogui.position()
        self.palette_coords[hx] = (x, y)
        messagebox.showinfo("Готово", f"Сохранена координата палитры для {hx}: {x},{y}")

    def save_palette_bindings(self):
        data = self.palette_coords
        path = filedialog.asksaveasfilename(title="Сохранить привязки", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Готово", f"Сохранено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def load_palette_bindings(self):
        path = filedialog.askopenfilename(title="Загрузить привязки", filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.palette_coords = json.load(f)
            messagebox.showinfo("Готово", f"Загружено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {e}")

    # ---------- Preview ----------
    def refresh_preview(self, event=None):
        self.canvas.delete("all")
        if self.quant_image is None:
            return
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        w, h = self.quant_image.size
        pad = 10
        max_w = max(1, cw - pad * 2)
        max_h = max(1, ch - pad * 2)
        scale = min(max_w / w, max_h / h)
        scale = max(1, int(scale))
        big = self.quant_image.resize((w * scale, h * scale), Image.NEAREST)
        self.preview_image = ImageTk.PhotoImage(big)
        x0 = (cw - big.width) // 2
        y0 = (ch - big.height) // 2
        self.canvas.create_image(x0, y0, image=self.preview_image, anchor="nw")
        grid_color = "#444444"
        for ix in range(w + 1):
            x = x0 + ix * scale
            self.canvas.create_line(x, y0, x, y0 + h * scale, fill=grid_color)
        for iy in range(h + 1):
            y = y0 + iy * scale
            self.canvas.create_line(x0, y, x0 + w * scale, y, fill=grid_color)

        # highlight selected color cells
        if self.highlight_color:
            data = self.quant_image.load()
            outline = "#FFEE00"
            for yy in range(h):
                for xx in range(w):
                    if self.draw_mask is not None and not self.draw_mask[yy][xx]:
                        continue
                    r, g, b = data[xx, yy]
                    if rgb_to_hex((r, g, b)).upper() == self.highlight_color.upper():
                        rx0 = x0 + xx * scale
                        ry0 = y0 + yy * scale
                        rx1 = rx0 + scale
                        ry1 = ry0 + scale
                        self.canvas.create_rectangle(rx0, ry0, rx1, ry1, outline=outline, width=max(1, scale//6))


    # ---------- Palette area calibration ----------
    def set_palette_tl(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        self.pal_tl = pyautogui.position()
        messagebox.showinfo("OK", f"Palette TL: {self.pal_tl}")

    def set_palette_br(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        self.pal_br = pyautogui.position()
        messagebox.showinfo("OK", f"Palette BR: {self.pal_br}")

    def auto_find_palette_color(self, hx: str):
        # requires palette TL/BR
        if pyautogui is None or not self.pal_tl or not self.pal_br:
            return None
        try:
            x0, y0 = self.pal_tl
            x1, y1 = self.pal_br
            if x1 <= x0 or y1 <= y0:
                return None
            shot = pyautogui.screenshot(region=(x0, y0, x1 - x0, y1 - y0))
            target = hex_to_rgb(hx)
            w, h = shot.size
            best = None
            best_d = 1e18
            step = max(1, min(w, h) // 60)  # coarse scan
            pix = shot.load()
            for yy in range(0, h, step):
                for xx in range(0, w, step):
                    r, g, b = pix[xx, yy][:3]
                    d = (r - target[0])**2 + (g - target[1])**2 + (b - target[2])**2
                    if d < best_d:
                        best_d = d
                        best = (x0 + xx, y0 + yy)
            return best
        except Exception:
            return None

    def _downsample_image(self, img, max_side=240):
        w, h = img.size
        scale = min(1.0, max_side / max(w, h))
        if scale < 1.0:
            img = img.resize((int(w*scale), int(h*scale)), Image.BILINEAR)
        return img

    def _kmeans_colors(self, pixels, k, iters=8):
        # pixels: list of (r,g,b)
        if not pixels:
            return []
        k = max(1, min(k, len(pixels)))
        centers = random.sample(pixels, k)
        for _ in range(iters):
            buckets = [[] for _ in range(k)]
            for r,g,b in pixels:
                bi = 0
                bd = 1e18
                for i,(cr,cg,cb) in enumerate(centers):
                    d = (r-cr)*(r-cr) + (g-cg)*(g-cg) + (b-cb)*(b-cb)
                    if d < bd:
                        bd = d
                        bi = i
                buckets[bi].append((r,g,b))
            new_centers = []
            for bucket in buckets:
                if bucket:
                    sr = sum(p[0] for p in bucket)
                    sg = sum(p[1] for p in bucket)
                    sb = sum(p[2] for p in bucket)
                    n = len(bucket)
                    new_centers.append((sr//n, sg//n, sb//n))
            if len(new_centers) < k:
                # refill missing with random
                while len(new_centers) < k:
                    new_centers.append(random.choice(pixels))
            if new_centers == centers:
                break
            centers = new_centers
        # unique centers
        seen = set()
        uniq = []
        for c in centers:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        return uniq

    def build_palette_from_screen(self):
        if pyautogui is None or not self.pal_tl or not self.pal_br:
            messagebox.showwarning("Нет области", "Укажите TL и BR области палитры")
            return
        try:
            k = int(self.palette_k_var.get())
        except Exception:
            k = 24
        try:
            x0, y0 = self.pal_tl
            x1, y1 = self.pal_br
            if x1 <= x0 or y1 <= y0:
                messagebox.showerror("Ошибка", "Неверная область палитры")
                return
            shot = pyautogui.screenshot(region=(x0, y0, x1 - x0, y1 - y0))
            shot = self._downsample_image(shot.convert('RGB'))
            w, h = shot.size
            pix = shot.load()
            pts = []
            step = max(1, min(w, h)//80)
            for yy in range(0, h, step):
                for xx in range(0, w, step):
                    r,g,b = pix[xx, yy]
                    pts.append((r,g,b))
            centers = self._kmeans_colors(pts, k)
            hexes = [rgb_to_hex(c) for c in centers]
            set_palette(hexes)
            # re-quantize using new palette
            if self.scaled_image is not None:
                self.apply_resize()
            messagebox.showinfo("Палитра обновлена", f"Цветов: {len(get_palette())}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось собрать палитру: {e}")

    def load_palette_json(self):
        path = filedialog.askopenfilename(title="Загрузить палитру", filetypes=[["JSON","*.json"],["Все файлы","*.*"]])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'palette' in data:
                hexes = data['palette']
            else:
                hexes = data
            set_palette(hexes)
            if self.scaled_image is not None:
                self.apply_resize()
            messagebox.showinfo("Готово", f"Загружено {len(get_palette())} цветов")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить палитру: {e}")

    def save_palette_json(self):
        path = filedialog.asksaveasfilename(title="Сохранить палитру", defaultextension=".json", filetypes=[["JSON","*.json"]])
        if not path:
            return
        try:
            payload = {"palette": get_palette()}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Готово", f"Сохранено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить палитру: {e}")

    # ---------- Algorithm and Palette Management ----------
    def on_algorithm_change(self, event=None):
        """Handle algorithm change event"""
        new_algorithm = self.color_algorithm_var.get()
        set_color_algorithm(new_algorithm)
        # Re-process the image with the new algorithm if we have one
        if self.scaled_image is not None:
            self.apply_resize()
    
    def optimize_palette_for_image(self):
        """Optimize palette using k-means clustering on the current image"""
        if self.scaled_image is None:
            messagebox.showinfo("Нет изображения", "Сначала загрузите изображение")
            return
        
        try:
            k = int(self.palette_k_var.get())
        except Exception:
            k = 24
        
        try:
            # Downsample for faster processing
            img = self._downsample_image(self.scaled_image.convert('RGB'))
            w, h = img.size
            pix = img.load()
            
            # Sample pixels from the image
            pixels = []
            for y in range(h):
                for x in range(w):
                    r, g, b = pix[x, y]
                    pixels.append((r, g, b))
            
            if not pixels:
                messagebox.showwarning("Предупреждение", "Нет пикселей для анализа")
                return
            
            # Use k-means clustering to find dominant colors
            centers = self._kmeans_colors(pixels, k)
            hexes = [rgb_to_hex(c) for c in centers]
            
            # Update palette
            set_palette(hexes)
            
            # Re-quantize using new palette
            self.apply_resize()
            
            messagebox.showinfo("Палитра оптимизирована", 
                              f"Палитра адаптирована под изображение. Цветов: {len(get_palette())}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось оптимизировать палитру: {e}")
    
    def reset_to_default_palette(self):
        """Reset to the default extended palette"""
        set_palette(SITE_PALETTE)
        # Re-quantize using default palette
        if self.scaled_image is not None:
            self.apply_resize()
        messagebox.showinfo("Палитра сброшена", 
                          f"Использована расширенная палитра. Цветов: {len(get_palette())}")

    # ---------- UI events ----------
    def on_color_select(self, event=None):
        sel = self.colors_list.curselection()
        if not sel:
            self.highlight_color = None
            self.refresh_preview()
            return
        item = self.colors_list.get(sel[0])
        hx = item.split()[0]
        self.highlight_color = hx
        self.refresh_preview()


if __name__ == "__main__":
    root = Tk()
    app = WplaceDrawerApp(root)
    root.mainloop()

