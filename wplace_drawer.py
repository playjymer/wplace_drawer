import threading
import time
import os
import csv
import json
from dataclasses import dataclass
from collections import defaultdict
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, Listbox, SINGLE,
    filedialog, messagebox, Canvas, Scrollbar, END
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
    """Convert sRGB value to linear RGB"""
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def _linear_to_oklab(r: float, g: float, b: float):
    """Convert linear RGB to OKLab color space"""
    # r,g,b are linear [0..1]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_ = l ** (1/3) if l > 0 else 0
    m_ = m ** (1/3) if m > 0 else 0
    s_ = s ** (1/3) if s > 0 else 0
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return (L, a, b2)

def _rgb_to_oklab(r: int, g: int, b: int):
    """Convert RGB to OKLab color space"""
    rl = _srgb_to_linear(r)
    gl = _srgb_to_linear(g)
    bl = _srgb_to_linear(b)
    return _linear_to_oklab(rl, gl, bl)

def _oklab_dist(c1, c2):
    """Calculate perceptual distance in OKLab space"""
    dL = c1[0] - c2[0]
    da = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return dL*dL + da*da + db*db

# --- LAB color space for Delta E CIE76 ---
def _rgb_to_xyz(r: int, g: int, b: int):
    """Convert RGB to XYZ color space"""
    # Normalize RGB values
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    
    # Apply gamma correction
    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
    
    # Observer = 2°, Illuminant = D65
    X = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    Y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    Z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    return (X, Y, Z)

def _xyz_to_lab(x, y, z):
    """Convert XYZ to LAB color space"""
    # Reference white D65
    xn, yn, zn = 0.95047, 1.0, 1.08883
    
    x, y, z = x / xn, y / yn, z / zn
    
    fx = x ** (1/3) if x > 0.008856 else (7.787 * x + 16/116)
    fy = y ** (1/3) if y > 0.008856 else (7.787 * y + 16/116)
    fz = z ** (1/3) if z > 0.008856 else (7.787 * z + 16/116)
    
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    
    return (L, a, b)

def _rgb_to_lab(r: int, g: int, b: int):
    """Convert RGB directly to LAB"""
    x, y, z = _rgb_to_xyz(r, g, b)
    return _xyz_to_lab(x, y, z)

def _delta_e_cie76(lab1, lab2):
    """Calculate Delta E CIE76 color difference"""
    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return (dL*dL + da*da + db*db) ** 0.5

# Precompute color space values for palette colors for better performance
_PALETTE_RGB = [hex_to_rgb(hx) for hx in SITE_PALETTE]
_PALETTE_LAB_OKLAB = [_rgb_to_oklab(*rgb) for rgb in _PALETTE_RGB]
_PALETTE_LAB_CIE = [_rgb_to_lab(*rgb) for rgb in _PALETTE_RGB]

# Color matching algorithm selection
COLOR_ALGORITHM = "oklab"  # "oklab", "cie76", or "rgb"

def set_color_algorithm(algorithm: str):
    """Set the color matching algorithm"""
    global COLOR_ALGORITHM
    if algorithm in ["oklab", "cie76", "rgb"]:
        COLOR_ALGORITHM = algorithm

def nearest_palette_color(r: int, g: int, b: int) -> str:
    """Find nearest palette color using the selected algorithm"""
    if COLOR_ALGORITHM == "cie76":
        return _nearest_palette_color_cie76(r, g, b)
    elif COLOR_ALGORITHM == "rgb":
        return _nearest_palette_color_rgb(r, g, b)
    else:  # default oklab
        return _nearest_palette_color_oklab(r, g, b)

def _nearest_palette_color_oklab(r: int, g: int, b: int) -> str:
    """Find nearest palette color using perceptual OKLab distance"""
    lab = _rgb_to_oklab(r, g, b)
    best_i = 0
    best_d = 1e9
    for i, labp in enumerate(_PALETTE_LAB_OKLAB):
        d = _oklab_dist(lab, labp)
        if d < best_d:
            best_d = d
            best_i = i
    return SITE_PALETTE[best_i]

def _nearest_palette_color_cie76(r: int, g: int, b: int) -> str:
    """Find nearest palette color using Delta E CIE76"""
    lab = _rgb_to_lab(r, g, b)
    best_i = 0
    best_d = 1e9
    for i, labp in enumerate(_PALETTE_LAB_CIE):
        d = _delta_e_cie76(lab, labp)
        if d < best_d:
            best_d = d
            best_i = i
    return SITE_PALETTE[best_i]

def _nearest_palette_color_rgb(r: int, g: int, b: int) -> str:
    """Find nearest palette color using simple RGB Euclidean distance"""
    best_i = 0
    best_d = 1e9
    for i, (pr, pg, pb) in enumerate(_PALETTE_RGB):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best_d = d
            best_i = i
    return SITE_PALETTE[best_i]

class WplaceDrawerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wplace Drawer (Testing Mode)")
        self.root.geometry("1120x720")

        # State
        self.src_image_path = None
        self.src_image = None  # PIL Image RGBA
        self.scaled_image = None  # PIL Image RGBA
        self.quant_image = None  # PIL Image after palette mapping
        self.preview_image = None  # ImageTk in canvas

        self.width_var = StringVar(value="8")
        self.height_var = StringVar(value="8")
        self.limit_var = StringVar(value="62")
        self.delay_var = StringVar(value="2.0")  # seconds before drawing starts
        self.click_sleep_var = StringVar(value="0.05")  # seconds between clicks

        # Calibration: screen positions of top-left and bottom-right cell centers
        self.tl = None  # (x, y)
        self.br = None  # (x, y)

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

        Label(top, text="Стартовая задержка, c:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.delay_var, width=6).pack(side="left")
        Label(top, text="Пауза между кликами, c:").pack(side="left", padx=(10, 4))
        Entry(top, textvariable=self.click_sleep_var, width=6).pack(side="left")

        # Color algorithm selection
        Label(top, text="Алгоритм:").pack(side="left", padx=(10, 4))
        self.color_algorithm_var = StringVar(value="oklab")
        from tkinter import OptionMenu
        algorithm_menu = OptionMenu(top, self.color_algorithm_var, "oklab", "cie76", "rgb", command=self.on_algorithm_change)
        algorithm_menu.pack(side="left")

        # Info
        self.info_var = StringVar(value="Откройте изображение и задайте размеры (W*H ≤ 62) | Алгоритм: OKLab (перцептуальный)")
        Label(root, textvariable=self.info_var).pack(side="top", anchor="w", padx=10)

        # Canvas preview
        mid = Frame(root)
        mid.pack(fill="both", expand=True)
        self.canvas = Canvas(mid, bg="#2b2b2b")
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", self.refresh_preview)

        # Right panel: colors list + calibration + actions
        right = Frame(mid, width=320)
        right.pack(side="right", fill="y")

        Label(right, text="Обнаруженные цвета:").pack(anchor="w", padx=6, pady=(10, 4))
        self.colors_list = Listbox(right, selectmode=SINGLE, height=12)
        self.colors_list.pack(fill="x", padx=6)

        # Scrollbar optional (if needed)
        sb = Scrollbar(right, orient='vertical', command=self.colors_list.yview)
        self.colors_list.config(yscrollcommand=sb.set)

        # Calibration controls
        Label(right, text="Калибровка (укажите центры ячеек):").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="1) Запомнить Top-Left (текущая позиция мыши)", command=self.set_tl).pack(fill="x", padx=6, pady=2)
        Button(right, text="2) Запомнить Bottom-Right (текущая позиция мыши)", command=self.set_br).pack(fill="x", padx=6, pady=2)
        self.calib_lbl = Label(right, text="TL: -, BR: -")
        self.calib_lbl.pack(anchor="w", padx=6)

        # Export buttons
        Label(right, text="Экспорт инструкций:").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Экспорт CSV", command=self.export_csv).pack(fill="x", padx=6, pady=2)
        Button(right, text="Экспорт JSON", command=self.export_json).pack(fill="x", padx=6, pady=2)

        # Palette optimization
        Label(right, text="Оптимизация палитры:").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Оптимизировать палитру под изображение", command=self.optimize_palette_for_image).pack(fill="x", padx=6, pady=2)
        Button(right, text="Сбросить к стандартной палитре", command=self.reset_to_default_palette).pack(fill="x", padx=6, pady=2)

        # Palette binding controls
        Label(right, text="Привязка палитры (автовыбор цвета):").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Запомнить координату палитры для выбранного цвета", command=self.bind_palette_for_selected).pack(fill="x", padx=6, pady=2)
        Button(right, text="Сохранить привязки", command=self.save_palette_bindings).pack(fill="x", padx=6, pady=2)
        Button(right, text="Загрузить привязки", command=self.load_palette_bindings).pack(fill="x", padx=6, pady=2)

        # Drawing actions
        Label(right, text="Отрисовка:").pack(anchor="w", padx=6, pady=(12, 4))
        Button(right, text="Нарисовать выбранный цвет", command=self.draw_selected_color).pack(fill="x", padx=6, pady=2)
        Button(right, text="Нарисовать все цвета (по порядку)", command=self.draw_all_colors).pack(fill="x", padx=6, pady=2)
        Button(right, text="Стоп", command=self.request_stop).pack(fill="x", padx=6, pady=(6, 2))

        Label(right, text="Подсказки:\n- Перед стартом переключитесь в окно браузера\n- Выберите нужный цвет палитры на сайте\n- Failsafe: подведите мышь в левый верхний угол экрана", justify="left").pack(anchor="w", padx=6, pady=(10, 6))

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

    def apply_resize(self):
        if self.src_image is None:
            messagebox.showinfo("Нет изображения", "Сначала откройте изображение")
            return
        w = self.get_int(self.width_var, 8)
        h = self.get_int(self.height_var, 8)
        limit = self.get_int(self.limit_var, 62)
        if w * h > limit:
            messagebox.showwarning("Лимит превышен", f"{w}x{h} = {w*h} > лимита {limit}")
            return
        # Resize, then map to site palette for drawing/preview
        self.scaled_image = self.src_image.resize((w, h), Image.NEAREST)
        self.quant_image = Image.new("RGB", (w, h))
        src = self.scaled_image.convert("RGBA").load()
        dst = self.quant_image.load()
        for yy in range(h):
            for xx in range(w):
                r, g, b, a = src[xx, yy]
                if a < 10:
                    # treat as transparent -> skip later; fill with white just for preview
                    dst[xx, yy] = hex_to_rgb("#FFFFFF")
                else:
                    hx = nearest_palette_color(r, g, b)
                    dst[xx, yy] = hex_to_rgb(hx)
        self.populate_colors()
        self.refresh_preview()
        self.info_var.set(f"Сетка {w}x{h} ({w*h}). Цветов: {self.colors_list.size()}")

    def populate_colors(self):
        self.colors_list.delete(0, END)
        if self.quant_image is None:
            return
        w, h = self.quant_image.size
        seen = {}
        data = self.quant_image.convert("RGBA").load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = data[x, y]
                if a < 10:
                    continue
                hx = rgb_to_hex((r, g, b))
                if hx not in seen:
                    seen[hx] = 0
                seen[hx] += 1
        # sort colors by count desc
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
        data = self.quant_image.convert("RGBA").load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = data[x, y]
                if a < 10:
                    continue
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

    def set_br(self):
        if pyautogui is None:
            messagebox.showerror("Ошибка", "pyautogui не установлен")
            return
        x, y = pyautogui.position()
        self.br = (x, y)
        self.update_calib_label()

    def update_calib_label(self):
        tl = f"TL: {self.tl}" if self.tl else "TL: -"
        br = f"BR: {self.br}" if self.br else "BR: -"
        self.calib_lbl.config(text=f"{tl}, {br}")

    def compute_cell_coords(self, x, y):
        """Return absolute screen coords for grid cell (x,y) center"""
        if not self.tl or not self.br or self.scaled_image is None:
            return None
        w, h = self.scaled_image.size
        (x0, y0), (x1, y1) = self.tl, self.br
        if w == 1:
            step_x = 0
        else:
            step_x = (x1 - x0) / (w - 1)
        if h == 1:
            step_y = 0
        else:
            step_y = (y1 - y0) / (h - 1)
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
            payload = {
                "width": self.scaled_image.size[0],
                "height": self.scaled_image.size[1],
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

        # Allow user to focus browser and select color
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
        # Try select palette swatch if bound
        self.select_palette_color(hx)
        self.start_draw_thread(pixels)

    def draw_all_colors(self):
        groups = self.group_pixels_by_color()
        if not groups:
            messagebox.showinfo("Нет данных", "Нет пикселей для рисования")
            return
        # Order by count desc and draw color by color
        order = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        # Build sequence with separators as tuples ("COLOR", hex)
        seq = []
        for hx, arr in order:
            seq.append(("COLOR", hx))
            seq.extend(arr)
        # Run in same thread helper that handles color switches
        self.start_draw_thread_with_color_switch(seq)

    def request_stop(self):
        self._stop_flag.set()

    # ---------- Palette bindings and color switch ----------
    def select_palette_color(self, hx: str):
        if pyautogui is None:
            return
        pos = getattr(self, 'palette_coords', {}).get(hx)
        if not pos:
            return
        try:
            pyautogui.moveTo(pos[0], pos[1])
            pyautogui.click()
            time.sleep(0.2)
        except Exception:
            pass

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
        if not hasattr(self, 'palette_coords'):
            self.palette_coords = {}
        self.palette_coords[hx] = (x, y)
        messagebox.showinfo("Готово", f"Сохранена координата палитры для {hx}: {x},{y}")

    def save_palette_bindings(self):
        data = getattr(self, 'palette_coords', {}) or {}
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

    # ---------- Palette optimization ----------
    def optimize_palette_for_image(self):
        """Optimize the palette based on the current image using k-means clustering"""
        if self.src_image is None:
            messagebox.showinfo("Нет изображения", "Сначала откройте изображение")
            return
        
        try:
            # Downsample image for performance
            img = self.src_image.convert("RGB")
            if img.width * img.height > 10000:  # Downsample large images
                ratio = (10000 / (img.width * img.height)) ** 0.5
                new_w = int(img.width * ratio)
                new_h = int(img.height * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Extract pixel colors
            pixels = list(img.getdata())
            
            # Remove very dark/light colors that might be artifacts
            filtered_pixels = []
            for r, g, b in pixels:
                brightness = (r + g + b) / 3
                if 20 < brightness < 235:  # Skip very dark/light pixels
                    filtered_pixels.append((r, g, b))
            
            if len(filtered_pixels) < 50:
                filtered_pixels = pixels  # Use all pixels if filtering removed too many
                
            # Perform k-means clustering to find dominant colors
            optimal_colors = self._kmeans_colors(filtered_pixels, k=min(60, len(set(filtered_pixels))))
            
            # Convert to hex and combine with essential colors
            essential_colors = [
                "#000000", "#FFFFFF", "#808080",  # Essential grayscale
            ]
            
            optimized_hex = [rgb_to_hex(color) for color in optimal_colors]
            
            # Combine essential colors with optimized ones, remove duplicates
            new_palette = essential_colors + optimized_hex
            seen = set()
            unique_palette = []
            for color in new_palette:
                if color not in seen:
                    seen.add(color)
                    unique_palette.append(color)
            
            # Update global palette
            global SITE_PALETTE, _PALETTE_RGB, _PALETTE_LAB_OKLAB, _PALETTE_LAB_CIE
            SITE_PALETTE = unique_palette
            _PALETTE_RGB = [hex_to_rgb(hx) for hx in SITE_PALETTE]
            _PALETTE_LAB_OKLAB = [_rgb_to_oklab(*rgb) for rgb in _PALETTE_RGB]
            _PALETTE_LAB_CIE = [_rgb_to_lab(*rgb) for rgb in _PALETTE_RGB]
            
            # Re-process the image with new palette
            self.apply_resize()
            
            messagebox.showinfo("Готово", f"Палитра оптимизирована! Теперь содержит {len(SITE_PALETTE)} цветов, подобранных специально для этого изображения.")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось оптимизировать палитру: {e}")
    
    def _kmeans_colors(self, pixels, k, max_iterations=20):
        """Simple k-means clustering for color quantization"""
        import random
        
        if k >= len(set(pixels)):
            return list(set(pixels))
        
        # Initialize centroids randomly
        unique_pixels = list(set(pixels))
        centroids = random.sample(unique_pixels, k)
        
        for _ in range(max_iterations):
            # Assign pixels to closest centroid
            clusters = [[] for _ in range(k)]
            for pixel in pixels:
                distances = [sum((a - b) ** 2 for a, b in zip(pixel, centroid)) for centroid in centroids]
                closest = distances.index(min(distances))
                clusters[closest].append(pixel)
            
            # Update centroids
            new_centroids = []
            for cluster in clusters:
                if cluster:
                    avg_r = sum(p[0] for p in cluster) / len(cluster)
                    avg_g = sum(p[1] for p in cluster) / len(cluster)
                    avg_b = sum(p[2] for p in cluster) / len(cluster)
                    new_centroids.append((int(avg_r), int(avg_g), int(avg_b)))
                else:
                    new_centroids.append(centroids[len(new_centroids)])  # Keep old centroid
            
            # Check for convergence
            if new_centroids == centroids:
                break
                
            centroids = new_centroids
        
        return centroids
    
    def reset_to_default_palette(self):
        """Reset to the original enhanced palette"""
        global SITE_PALETTE, _PALETTE_RGB, _PALETTE_LAB_OKLAB, _PALETTE_LAB_CIE
        
        # Reset to original enhanced palette
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
        
        # Recompute precomputed values
        _PALETTE_RGB = [hex_to_rgb(hx) for hx in SITE_PALETTE]
        _PALETTE_LAB_OKLAB = [_rgb_to_oklab(*rgb) for rgb in _PALETTE_RGB]
        _PALETTE_LAB_CIE = [_rgb_to_lab(*rgb) for rgb in _PALETTE_RGB]
        
        # Re-process the image
        if self.src_image:
            self.apply_resize()
        
        messagebox.showinfo("Готово", "Палитра сброшена к расширенной стандартной версии")

    # ---------- Algorithm selection ----------
    def on_algorithm_change(self, value):
        """Handle algorithm selection change"""
        set_color_algorithm(value)
        
        # Update info text
        algorithm_names = {
            "oklab": "OKLab (перцептуальный)",
            "cie76": "Delta E CIE76 (точный)", 
            "rgb": "RGB (простой)"
        }
        algorithm_desc = algorithm_names.get(value, value)
        
        if self.src_image:
            filename = os.path.basename(self.src_image_path) if self.src_image_path else "изображение"
            self.info_var.set(f"Загружено: {filename} | Алгоритм: {algorithm_desc}")
        else:
            self.info_var.set(f"Откройте изображение и задайте размеры (W*H ≤ 62) | Алгоритм: {algorithm_desc}")
        
        # Re-process the image if it's loaded
        if self.src_image:
            self.apply_resize()

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


if __name__ == "__main__":
    root = Tk()
    app = WplaceDrawerApp(root)
    root.mainloop()

