import json
import csv
import os
from dataclasses import dataclass
from tkinter import Tk, Frame, Label, Button, Entry, StringVar, filedialog, messagebox, Canvas
from PIL import Image, ImageTk

# Simple data holder for pixel info
@dataclass
class Pixel:
    x: int
    y: int
    hex_color: str


def rgb_to_hex(rgb):
    r, g, b = rgb[:3]
    return f"#{r:02X}{g:02X}{b:02X}"


class WplaceHelperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wplace Image Helper (Manual)")
        self.root.geometry("980x640")

        # State
        self.src_image_path = None
        self.src_image = None  # PIL Image
        self.scaled_image = None  # PIL Image resized to grid
        self.preview_image = None  # ImageTk.PhotoImage for Canvas preview

        # Controls
        control_frame = Frame(root)
        control_frame.pack(side="top", fill="x", padx=10, pady=8)

        Button(control_frame, text="Открыть изображение", command=self.open_image).pack(side="left")

        Label(control_frame, text="Ширина:").pack(side="left", padx=(10, 4))
        self.width_var = StringVar(value="8")
        Entry(control_frame, textvariable=self.width_var, width=6).pack(side="left")

        Label(control_frame, text="Высота:").pack(side="left", padx=(10, 4))
        self.height_var = StringVar(value="8")
        Entry(control_frame, textvariable=self.height_var, width=6).pack(side="left")

        Label(control_frame, text="Лимит пикселей:").pack(side="left", padx=(10, 4))
        self.limit_var = StringVar(value="62")
        Entry(control_frame, textvariable=self.limit_var, width=8).pack(side="left")

        Button(control_frame, text="Применить размер", command=self.apply_resize).pack(side="left", padx=(10, 0))

        Button(control_frame, text="Экспорт CSV", command=self.export_csv).pack(side="left", padx=(10, 0))
        Button(control_frame, text="Экспорт JSON", command=self.export_json).pack(side="left", padx=(6, 0))

        # Info label
        self.info_var = StringVar(value="Откройте изображение")
        Label(root, textvariable=self.info_var).pack(side="top", anchor="w", padx=10)

        # Canvas preview
        self.canvas = Canvas(root, bg="#2b2b2b")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", self.refresh_preview)

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
        self.apply_resize()  # auto fit into current width/height if possible

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
            messagebox.showwarning(
                "Лимит превышен",
                f"Запрошенный размер {w}x{h} = {w*h} пикселей превышает лимит {limit}.",
            )
            return

        # Resize using nearest neighbor for pixel-art like effect
        self.scaled_image = self.src_image.resize((w, h), Image.NEAREST)
        self.refresh_preview()
        self.info_var.set(
            f"Готово: сетка {w}x{h} ({w*h} пикселей). Можно экспортировать инструкции."
        )

    def get_pixels(self):
        if self.scaled_image is None:
            return []
        w, h = self.scaled_image.size
        pixels = []
        data = self.scaled_image.convert("RGBA").load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = data[x, y]
                if a < 10:
                    # пропуск почти прозрачных пикселей
                    continue
                pixels.append(Pixel(x=x, y=y, hex_color=rgb_to_hex((r, g, b))))
        return pixels

    def export_csv(self):
        pixels = self.get_pixels()
        if not pixels:
            messagebox.showinfo("Нет данных", "Нет пикселей для экспорта. Примените размер.")
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
                writer = csv.writer(f)
                writer.writerow(["x", "y", "hex_color"])  # header
                for p in pixels:
                    writer.writerow([p.x, p.y, p.hex_color])
            messagebox.showinfo("Экспорт завершён", f"Сохранено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить CSV: {e}")

    def export_json(self):
        pixels = self.get_pixels()
        if not pixels:
            messagebox.showinfo("Нет данных", "Нет пикселей для экспорта. Примените размер.")
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
            messagebox.showinfo("Экспорт завершён", f"Сохранено: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить JSON: {e}")

    def refresh_preview(self, event=None):
        self.canvas.delete("all")
        if self.scaled_image is None:
            return
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        w, h = self.scaled_image.size

        # compute scale to fit canvas with some padding
        pad = 10
        max_w = max(1, cw - pad * 2)
        max_h = max(1, ch - pad * 2)
        scale = min(max_w / w, max_h / h)
        scale = max(1, int(scale))  # integer scale for crisp pixels

        # create enlarged preview image
        big = self.scaled_image.resize((w * scale, h * scale), Image.NEAREST)
        self.preview_image = ImageTk.PhotoImage(big)
        x0 = (cw - big.width) // 2
        y0 = (ch - big.height) // 2
        self.canvas.create_image(x0, y0, image=self.preview_image, anchor="nw")

        # draw grid lines
        grid_color = "#444444"
        for ix in range(w + 1):
            x = x0 + ix * scale
            self.canvas.create_line(x, y0, x, y0 + h * scale, fill=grid_color)
        for iy in range(h + 1):
            y = y0 + iy * scale
            self.canvas.create_line(x0, y, x0 + w * scale, y, fill=grid_color)


if __name__ == "__main__":
    root = Tk()
    app = WplaceHelperApp(root)
    root.mainloop()

