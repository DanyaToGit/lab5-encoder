"""
Лабораторная работа №5. Вариант 11.
Энкодер вала: Encoder (базовый) и GearedEncoder (потомок с передаточным числом).
Окно на Tkinter: вращение стрелки на Canvas, вывод угла (рад/град),
числа оборотов и скорости (об/мин), кнопка обнуления счётчика.
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox


# ============================================================
#  МОДЕЛЬ (не импортирует tkinter)
# ============================================================

class Encoder:
    """Энкодер вала: считает импульсы и угол поворота."""

    MAX_RPM = 600.0

    def __init__(self, name: str, ppr: int = 200):
        if ppr <= 0:
            raise ValueError("Число импульсов на оборот должно быть > 0")
        self.name = name
        self._ppr = int(ppr)
        self._count = 0
        self._rpm = 0.0
        self._phase = 0.0

    @property
    def ppr(self) -> int:
        return self._ppr

    @ppr.setter
    def ppr(self, value: int):
        value = int(value)
        if value <= 0:
            raise ValueError("Число импульсов на оборот должно быть > 0")
        self._ppr = value

    @property
    def count(self) -> int:
        return self._count

    @property
    def rpm(self) -> float:
        return self._rpm

    @rpm.setter
    def rpm(self, value: float):
        value = float(value)
        if abs(value) > self.MAX_RPM:
            raise ValueError(
                f"Скорость должна быть в диапазоне "
                f"-{self.MAX_RPM:g}...{self.MAX_RPM:g} об/мин")
        self._rpm = value

    def _impulses_per_rev(self) -> float:
        return float(self._ppr)

    def revolutions(self) -> float:
        return self._count / self._impulses_per_rev()

    def angle_rad(self) -> float:
        return (2.0 * math.pi * self.revolutions()) % (2.0 * math.pi)

    def angle_deg(self) -> float:
        deg = math.degrees(self.angle_rad())
        return deg if deg < 360.0 else 0.0

    def output_rpm(self) -> float:
        return self._rpm

    def rotate(self, dt: float):
        if dt <= 0:
            raise ValueError("Шаг времени должен быть > 0")
        delta = self._rpm / 60.0 * self._impulses_per_rev() * dt
        self._phase += delta
        whole = int(self._phase)
        if whole != 0:
            self._count += whole
            self._phase -= whole

    def reset(self):
        self._count = 0
        self._rpm = 0.0
        self._phase = 0.0

    def __str__(self) -> str:
        return (f"{self.name}: импульсы={self._count}, "
                f"обороты={self.revolutions():.3f}, "
                f"угол={self.angle_deg():.1f}°, "
                f"скорость={self.output_rpm():.1f} об/мин")


class GearedEncoder(Encoder):
    """Энкодер с редуктором: учитывает передаточное число."""

    def __init__(self, name: str, ppr: int = 200, ratio: float = 10.0):
        super().__init__(name, ppr)
        if ratio <= 0:
            raise ValueError("Передаточное число должно быть > 0")
        self._ratio = float(ratio)

    @property
    def ratio(self) -> float:
        return self._ratio

    @ratio.setter
    def ratio(self, value: float):
        value = float(value)
        if value <= 0:
            raise ValueError("Передаточное число должно быть > 0")
        self._ratio = value

    def _impulses_per_rev(self) -> float:
        return float(self._ppr) * self._ratio

    def output_rpm(self) -> float:
        return self._rpm / self._ratio

    def __str__(self) -> str:
        return (f"{self.name} (редуктор 1:{self._ratio:g}): "
                f"импульсы={self.count}, "
                f"обороты выхода={self.revolutions():.3f}, "
                f"угол={self.angle_deg():.1f}°, "
                f"скорость выхода={self.output_rpm():.2f} об/мин")


# ============================================================
#  ИНТЕРФЕЙС
# ============================================================

class EncoderApp(tk.Tk):
    """Главное окно приложения «Энкодер вала»."""

    SIZE = 320
    CENTER = SIZE / 2
    ARROW = 120
    DT = 0.05

    def __init__(self, encoder: Encoder):
        super().__init__()
        self.title("Энкодер вала — панель управления")
        self.resizable(False, False)
        self.encoder = encoder

        self.running = False
        self.info = tk.StringVar()
        self.rpm_var = tk.DoubleVar(value=encoder.rpm)
        self.angle_var = tk.StringVar(value="0.0°")

        self._build_widgets()
        self._redraw()
        self.after(int(self.DT * 1000), self._tick)

    def _build_widgets(self):
        # Canvas — циферблат
        self.canvas = tk.Canvas(self, width=self.SIZE, height=self.SIZE,
                                bg="white", highlightthickness=1)
        self.canvas.grid(row=0, column=0, rowspan=2, padx=6, pady=6)

        # Панель управления
        panel = ttk.LabelFrame(self, text="Управление")
        panel.grid(row=0, column=1, sticky="n", padx=6, pady=6)

        ttk.Label(panel, text="Скорость, об/мин:").pack(anchor="w")

        self.scale = ttk.Scale(panel,
                               from_=-Encoder.MAX_RPM,
                               to=Encoder.MAX_RPM,
                               variable=self.rpm_var,
                               command=self._on_rpm_change)
        self.scale.pack(fill="x", pady=3)

        ttk.Label(panel, textvariable=self.angle_var).pack(anchor="w")

        ttk.Button(panel, text="◀ Вперёд (по таймеру)",
                   command=self._start_forward).pack(fill="x", pady=2)
        ttk.Button(panel, text="Назад ▶",
                   command=self._start_backward).pack(fill="x", pady=2)
        ttk.Button(panel, text="Стоп",
                   command=self._stop).pack(fill="x", pady=2)
        ttk.Button(panel, text="Обнулить счётчик",
                   command=self._reset).pack(fill="x", pady=2)

        # Поле ввода передаточного числа — только для GearedEncoder
        if isinstance(self.encoder, GearedEncoder):
            row = ttk.Frame(panel)
            row.pack(fill="x", pady=(8, 0))
            ttk.Label(row, text="Передат. число:").pack(side="left")
            self.ratio_var = tk.StringVar(value=f"{self.encoder.ratio:g}")
            ttk.Entry(row, textvariable=self.ratio_var,
                      width=8).pack(side="left", padx=4)
            ttk.Button(row, text="OK",
                       command=self._apply_ratio).pack(side="left")

        ttk.Label(panel, text="Оборот (0…100 %):").pack(anchor="w",
                                                         pady=(8, 0))
        self.bar = ttk.Progressbar(panel, maximum=360, length=160)
        self.bar.pack(fill="x")

        # Строка информации — grid, потому что лежит прямо в окне
        ttk.Label(self, textvariable=self.info).grid(
            row=2, column=0, columnspan=2, pady=(0, 6))

    def _on_rpm_change(self, value):
        try:
            self.encoder.rpm = float(value)
        except ValueError as err:
            messagebox.showerror("Ошибка", str(err))
            self.rpm_var.set(self.encoder.rpm)
        self._redraw()

    def _start_forward(self):
        if self.encoder.rpm <= 0:
            self.rpm_var.set(60.0)
            self.encoder.rpm = 60.0
        self.running = True

    def _start_backward(self):
        if self.encoder.rpm >= 0:
            self.rpm_var.set(-60.0)
            self.encoder.rpm = -60.0
        self.running = True

    def _stop(self):
        self.running = False
        self.rpm_var.set(0.0)
        self.encoder.rpm = 0.0

    def _reset(self):
        self.running = False
        self.encoder.reset()
        self.rpm_var.set(0.0)
        self._redraw()

    def _apply_ratio(self):
        text = self.ratio_var.get().strip().replace(",", ".")
        if not text:
            messagebox.showerror("Ошибка ввода",
                                 "Введите передаточное число (например, 10)")
            return
        try:
            self.encoder.ratio = float(text)
            self._redraw()
        except ValueError as err:
            messagebox.showerror("Ошибка ввода", str(err))

    def _tick(self):
        if self.running:
            try:
                self.encoder.rotate(self.DT)
            except ValueError as err:
                messagebox.showerror("Ошибка", str(err))
                self.running = False
            self._redraw()
        self.after(int(self.DT * 1000), self._tick)

    def _redraw(self):
        cv = self.canvas
        cv.delete("all")
        c = self.CENTER

        cv.create_oval(c - self.ARROW - 10, c - self.ARROW - 10,
                       c + self.ARROW + 10, c + self.ARROW + 10,
                       outline="#888")
        for deg in range(0, 360, 30):
            a = math.radians(deg)
            r1, r2 = self.ARROW + 4, self.ARROW + 10
            cv.create_line(c + r1 * math.sin(a), c - r1 * math.cos(a),
                           c + r2 * math.sin(a), c - r2 * math.cos(a),
                           fill="#888")

        ang = self.encoder.angle_rad()
        x = c + self.ARROW * math.sin(ang)
        y = c - self.ARROW * math.cos(ang)
        cv.create_line(c, c, x, y, width=4, fill="red", arrow="last")
        cv.create_oval(c - 5, c - 5, c + 5, c + 5, fill="black")

        self.bar["value"] = self.encoder.angle_deg()
        self.angle_var.set(
            f"Угол: {self.encoder.angle_deg():.1f}° "
            f"({self.encoder.angle_rad():.3f} рад)")
        self.info.set(
            f"{self.encoder} | скорость={self.encoder.output_rpm():.1f} об/мин")


# ============================================================
#  ТОЧКА ВХОДА
# ============================================================

def main():
    """Создаёт модель и запускает главное окно приложения."""
    encoder = GearedEncoder("ENC-1", ppr=200, ratio=10.0)
    app = EncoderApp(encoder)
    app.mainloop()


if __name__ == "__main__":
    # Тестовый прогон модели без интерфейса
    enc = GearedEncoder("TEST", ppr=200, ratio=10.0)
    enc.rpm = 600.0
    for _ in range(10):
        enc.rotate(0.1)
    print(enc)

    # Проверка граничных случаев
    try:
        enc.rpm = 99999
    except ValueError as e:
        print("OK, поймали:", e)
    try:
        enc.ratio = -1
    except ValueError as e:
        print("OK, поймали:", e)

    main()