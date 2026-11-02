"""
Лабораторная работа №5. Вариант 11.
Энкодер вала: Encoder (базовый) и GearedEncoder (потомок с передаточным числом).
Окно на Tkinter: вращение стрелки на Canvas, вывод угла (рад/град),
числа оборотов и скорости (об/мин), кнопка обнуления счётчика.
"""

import math                                      # Модуль для математических функций (sin, cos, pi, radians)
import tkinter as tk                             # Главная библиотека для графического интерфейса (окна, кнопки, холст)
from tkinter import ttk, messagebox              # ttk — современные красивые виджеты, messagebox — всплывающие окна с ошибками


# ============================================================
#  МОДЕЛЬ (классы, которые считают физику, не зависят от интерфейса)
# ============================================================

class Encoder:
    """Энкодер вала: считает импульсы и угол поворота."""

    MAX_RPM = 600.0                              # Максимально допустимая скорость (константа для всего класса)

    def __init__(self, name: str, ppr: int = 200):
        """Конструктор: срабатывает при создании объекта Encoder()."""
        if ppr <= 0:                             # Защита от дурака: импульсов на оборот не может быть 0 или меньше
            raise ValueError("Число импульсов на оборот должно быть > 0")  # Выбрасываем ошибку
        self.name = name                         # Имя энкодера (например, "ENC-1")
        self._ppr = int(ppr)                     # Кол-во импульсов на 1 оборот (приводим к целому числу)
        self._count = 0                          # Счетчик импульсов (при создании равен 0)
        self._rpm = 0.0                          # Текущая скорость (при создании 0)
        self._phase = 0.0                        # Аккумулятор дробной части (копит "хвостики", чтобы не терять точность)

    @property
    def ppr(self) -> int:
        """Геттер для _ppr (позволяет прочитать значение)."""
        return self._ppr

    @ppr.setter
    def ppr(self, value: int):
        """Сеттер для _ppr (срабатывает при попытке записать encoder.ppr = 500)."""
        value = int(value)                       # Приводим введенное значение к целому числу
        if value <= 0:                           # Проверяем, что число положительное
            raise ValueError("Число импульсов на оборот должно быть > 0")
        self._ppr = value                        # Записываем новое значение

    @property
    def count(self) -> int:
        """Геттер для счетчика (ТОЛЬКО ЧТЕНИЕ, изменить напрямую нельзя)."""
        return self._count

    @property
    def rpm(self) -> float:
        """Геттер для скорости."""
        return self._rpm

    @rpm.setter
    def rpm(self, value: float):
        """Сеттер для скорости (проверяет, чтобы не превышала 600)."""
        value = float(value)                     # Приводим к дробному числу
        if abs(value) > self.MAX_RPM:            # Проверяем по модулю (для реверса тоже)
            raise ValueError(f"Скорость должна быть в диапазоне -{self.MAX_RPM:g}...{self.MAX_RPM:g} об/мин")
        self._rpm = value                        # Записываем скорость

    def _impulses_per_rev(self) -> float:
        """Сколько импульсов генерируется за 1 оборот ВЫХОДНОГО вала (в базовом классе просто ppr)."""
        return float(self._ppr)

    def revolutions(self) -> float:
        """Вычисляет количество полных оборотов вала."""
        return self._count / self._impulses_per_rev()  # Делим счетчик на количество импульсов на оборот

    def angle_rad(self) -> float:
        """Вычисляет угол в радианах (от 0 до 2π)."""
        return (2.0 * math.pi * self.revolutions()) % (2.0 * math.pi)  # Берем остаток от деления, чтобы сбрасывать после 360°

    def angle_deg(self) -> float:
        """Вычисляет угол в градусах (от 0 до 360)."""
        deg = math.degrees(self.angle_rad())     # Переводим радианы в градусы
        return deg if deg < 360.0 else 0.0       # Если вдруг получилось ровно 360, возвращаем 0

    def output_rpm(self) -> float:
        """Скорость на выходном валу (в базовом классе совпадает с входной)."""
        return self._rpm

    def rotate(self, dt: float):
        """Главный метод симуляции: двигает вал на время dt (секунды)."""
        if dt <= 0:                              # Защита от отрицательного времени
            raise ValueError("Шаг времени должен быть > 0")
        # Считаем, сколько импульсов должно добавиться: (об/мин / 60) * импульсов_на_оборот * время
        delta = self._rpm / 60.0 * self._impulses_per_rev() * dt
        self._phase += delta                     # Копим результат в аккумуляторе (там могут быть дробные части)
        whole = int(self._phase)                 # Отрезаем целую часть (целые импульсы)
        if whole != 0:                           # Если накопился хотя бы 1 целый импульс
            self._count += whole                 # Добавляем его к общему счетчику
            self._phase -= whole                 # А дробный остаток оставляем на следующий раз

    def reset(self):
        """Сброс энкодера в исходное состояние."""
        self._count = 0                          # Счетчик в 0
        self._rpm = 0.0                          # Скорость в 0
        self._phase = 0.0                        # Аккумулятор в 0

    def __str__(self) -> str:
        """Красивое строковое представление (вызывается при print())."""
        return (f"{self.name}: импульсы={self._count}, "
                f"обороты={self.revolutions():.3f}, "
                f"угол={self.angle_deg():.1f}°, "
                f"скорость={self.output_rpm():.1f} об/мин")


class GearedEncoder(Encoder):
    """Энкодер с редуктором: учитывает передаточное число (наследник)."""

    def __init__(self, name: str, ppr: int = 200, ratio: float = 10.0):
        """Конструктор потомка."""
        super().__init__(name, ppr)              # Вызываем конструктор РОДИТЕЛЯ (чтобы не дублировать код)
        if ratio <= 0:                           # Проверка передаточного числа
            raise ValueError("Передаточное число должно быть > 0")
        self._ratio = float(ratio)               # Сохраняем передаточное число (например, 10.0)

    @property
    def ratio(self) -> float:
        """Геттер для ratio."""
        return self._ratio

    @ratio.setter
    def ratio(self, value: float):
        """Сеттер для ratio (проверяет, что число > 0)."""
        value = float(value)
        if value <= 0:
            raise ValueError("Передаточное число должно быть > 0")
        self._ratio = value

    def _impulses_per_rev(self) -> float:
        """ПОЛИМОРФИЗМ: переопределяем метод родителя."""
        return float(self._ppr) * self._ratio    # На выходе редуктора импульсов в `ratio` раз больше

    def output_rpm(self) -> float:
        """ПОЛИМОРФИЗМ: скорость на выходе редуктора."""
        return self._rpm / self._ratio           # Выходной вал крутится в `ratio` раз медленнее

    def __str__(self) -> str:
        """ПОЛИМОРФИЗМ: свой формат строки с указанием редуктора."""
        return (f"{self.name} (редуктор 1:{self._ratio:g}): "
                f"импульсы={self.count}, "
                f"обороты выхода={self.revolutions():.3f}, "
                f"угол={self.angle_deg():.1f}°, "
                f"скорость выхода={self.output_rpm():.2f} об/мин")


# ============================================================
#  ИНТЕРФЕЙС (класс окна, отвечает только за кнопки и картинку)
# ============================================================

class EncoderApp(tk.Tk):
    """Главное окно приложения (наследник стандартного окна Tkinter)."""

    SIZE = 320                                   # Размер белого квадрата (холста) в пикселях
    CENTER = SIZE / 2                            # Центр холста (160)
    ARROW = 120                                  # Длина красной стрелки (120 пикселей)
    DT = 0.05                                    # Шаг времени для таймера (0.05 сек = 50 мс)

    def __init__(self, encoder: Encoder):
        """Создание окна и запуск таймера."""
        super().__init__()                       # Инициализация самого окна Windows
        self.title("Энкодер вала — панель управления")  # Заголовок окна
        self.resizable(False, False)             # Запрещаем менять размер окна мышкой
        self.encoder = encoder                   # Ссылка на модель (через нее обновляем данные)

        self.running = False                     # Флаг: если True — стрелка крутится, если False — стоит
        self.info = tk.StringVar()               # Переменная для нижней строки (туда пишем текст)
        self.rpm_var = tk.DoubleVar(value=encoder.rpm)  # Переменная для связи с ползунком скорости
        self.angle_var = tk.StringVar(value="0.0°")     # Переменная для текста с углом

        self._build_widgets()                    # Создаем все кнопки и холст (вызов метода ниже)
        self._redraw()                           # Первый раз рисуем картинку
        self.after(int(self.DT * 1000), self._tick)  # Запускаем таймер (через 50 мс вызовется _tick)

    def _build_widgets(self):
        """Метод, который создает и расставляет все элементы интерфейса."""
        # --- БЕЛЫЙ ХОЛСТ С ЦИФЕРБЛАТОМ ---
        self.canvas = tk.Canvas(self, width=self.SIZE, height=self.SIZE, bg="white", highlightthickness=1)
        self.canvas.grid(row=0, column=0, rowspan=2, padx=6, pady=6)  # Размещаем слева

        # --- ПАНЕЛЬ УПРАВЛЕНИЯ (СПРАВА) ---
        panel = ttk.LabelFrame(self, text="Управление")
        panel.grid(row=0, column=1, sticky="n", padx=6, pady=6)  # Размещаем справа

        # 1. Ползунок скорости
        ttk.Label(panel, text="Скорость, об/мин:").pack(anchor="w")  # Текст над ползунком
        self.scale = ttk.Scale(panel, from_=-Encoder.MAX_RPM, to=Encoder.MAX_RPM,
                               variable=self.rpm_var, command=self._on_rpm_change)
        self.scale.pack(fill="x", pady=3)        # Растягиваем ползунок на всю ширину

        # 2. Текст текущего угла
        ttk.Label(panel, textvariable=self.angle_var).pack(anchor="w")

        # 3. Кнопки
        ttk.Button(panel, text="◀ Вперёд (по таймеру)", command=self._start_forward).pack(fill="x", pady=2)
        ttk.Button(panel, text="Назад ▶", command=self._start_backward).pack(fill="x", pady=2)
        ttk.Button(panel, text="Стоп", command=self._stop).pack(fill="x", pady=2)
        ttk.Button(panel, text="Обнулить счётчик", command=self._reset).pack(fill="x", pady=2)

        # 4. Поле ввода передаточного числа (показываем только если это GearedEncoder)
        if isinstance(self.encoder, GearedEncoder):  # Проверяем тип модели
            row = ttk.Frame(panel)               # Маленькая рамка для строки
            row.pack(fill="x", pady=(8, 0))
            ttk.Label(row, text="Передат. число:").pack(side="left")
            self.ratio_var = tk.StringVar(value=f"{self.encoder.ratio:g}")  # Текст в поле
            ttk.Entry(row, textvariable=self.ratio_var, width=8).pack(side="left", padx=4)  # Само поле
            ttk.Button(row, text="OK", command=self._apply_ratio).pack(side="left")  # Кнопка ОК

        # 5. Прогрессбар заполнения оборота
        ttk.Label(panel, text="Оборот (0…100 %):").pack(anchor="w", pady=(8, 0))
        self.bar = ttk.Progressbar(panel, maximum=360, length=160)  # Шкала от 0 до 360 градусов
        self.bar.pack(fill="x")

        # 6. Нижняя строка информации (на всю ширину окна)
        ttk.Label(self, textvariable=self.info).grid(row=2, column=0, columnspan=2, pady=(0, 6))

    def _on_rpm_change(self, value):
        """Срабатывает, когда двигают ползунок скорости."""
        try:
            self.encoder.rpm = float(value)      # Пытаемся передать значение в модель
        except ValueError as err:                # Если значение недопустимо (например, больше 600)
            messagebox.showerror("Ошибка", str(err))  # Показываем красное окно с ошибкой
            self.rpm_var.set(self.encoder.rpm)   # Откатываем ползунок назад на старое значение
        self._redraw()                           # Обновляем стрелку на экране

    def _start_forward(self):
        """Кнопка 'Вперёд'."""
        if self.encoder.rpm <= 0:                # Если стояли или крутились назад
            self.rpm_var.set(60.0)               # Двигаем ползунок
            self.encoder.rpm = 60.0              # Задаем модели скорость 60
        self.running = True                      # Включаем таймер (стрелка начнет крутиться)

    def _start_backward(self):
        """Кнопка 'Назад'."""
        if self.encoder.rpm >= 0:                # Если стояли или крутились вперед
            self.rpm_var.set(-60.0)              # Двигаем ползунок в минус
            self.encoder.rpm = -60.0             # Задаем отрицательную скорость (реверс)
        self.running = True                      # Включаем таймер

    def _stop(self):
        """Кнопка 'Стоп'."""
        self.running = False                     # Выключаем таймер (стрелка замирает)
        self.rpm_var.set(0.0)                    # Ползунок в ноль
        self.encoder.rpm = 0.0                   # Скорость в модели в ноль

    def _reset(self):
        """Кнопка 'Обнулить'."""
        self.running = False                     # Останавливаем вращение
        self.encoder.reset()                     # Сбрасываем счетчик и угол в модели
        self.rpm_var.set(0.0)                    # Ползунок в ноль
        self._redraw()                           # Перерисовываем (стрелка возвращается на 12 часов)

    def _apply_ratio(self):
        """Срабатывает при нажатии 'OK' рядом с полем передаточного числа."""
        text = self.ratio_var.get().strip().replace(",", ".")  # Берем текст, убираем пробелы, меняем запятую на точку
        if not text:                             # Если поле пустое
            messagebox.showerror("Ошибка ввода", "Введите передаточное число (например, 10)")
            return                               # Выходим из метода
        try:
            self.encoder.ratio = float(text)     # Пытаемся передать число в модель
            self._redraw()                       # Если получилось — перерисовываем
        except ValueError as err:                # Если ввели букву или отрицательное число
            messagebox.showerror("Ошибка ввода", str(err))

    def _tick(self):
        """Сердце программы: срабатывает каждые 50 мс по таймеру."""
        if self.running:                         # Если нажата кнопка Вперёд/Назад
            try:
                self.encoder.rotate(self.DT)     # Двигаем вал в модели на 0.05 секунды
            except ValueError as err:            # Ловим ошибки, если они вдруг возникнут
                messagebox.showerror("Ошибка", str(err))
                self.running = False             # Останавливаем движение при ошибке
            self._redraw()                       # Перерисовываем стрелку на холсте
        self.after(int(self.DT * 1000), self._tick)  # Планируем следующий "тик" через 50 мс

    def _redraw(self):
        """Полная перерисовка холста и обновление текста."""
        cv = self.canvas                         # Ссылка на холст
        cv.delete("all")                         # Стираем всё, что было нарисовано
        c = self.CENTER                          # Центр холста (160, 160)

        # 1. Внешняя окружность (циферблат)
        cv.create_oval(c - self.ARROW - 10, c - self.ARROW - 10,
                       c + self.ARROW + 10, c + self.ARROW + 10, outline="#888")

        # 2. Деления (каждые 30 градусов)
        for deg in range(0, 360, 30):            # Цикл: 0, 30, 60... 330
            a = math.radians(deg)                # Переводим градусы в радианы для sin/cos
            r1, r2 = self.ARROW + 4, self.ARROW + 10  # Внутренний и внешний радиусы делений
            cv.create_line(c + r1 * math.sin(a), c - r1 * math.cos(a),
                           c + r2 * math.sin(a), c - r2 * math.cos(a), fill="#888")

        # 3. Красная стрелка
        ang = self.encoder.angle_rad()           # Берем текущий угол из модели
        x = c + self.ARROW * math.sin(ang)       # Вычисляем X конца стрелки
        y = c - self.ARROW * math.cos(ang)       # Вычисляем Y конца стрелки (минус из-за экранных координат)
        cv.create_line(c, c, x, y, width=4, fill="red", arrow="last")  # Рисуем линию со стрелкой

        # 4. Черный кружок по центру (ось)
        cv.create_oval(c - 5, c - 5, c + 5, c + 5, fill="black")

        # 5. Обновляем прогрессбар и текстовые строки
        self.bar["value"] = self.encoder.angle_deg()  # Полоска заполняется от 0 до 360
        self.angle_var.set(f"Угол: {self.encoder.angle_deg():.1f}° ({self.encoder.angle_rad():.3f} рад)")  # Текст угла
        self.info.set(f"{self.encoder} | скорость={self.encoder.output_rpm():.1f} об/мин")  # Нижняя строка


# ============================================================
#  ТОЧКА ВХОДА
# ============================================================

def main():
    """Создает модель и запускает окно приложения."""
    encoder = GearedEncoder("ENC-1", ppr=200, ratio=10.0)  # Создаем энкодер с редуктором 1:10
    app = EncoderApp(encoder)                # Создаем окно и передаем ему модель
    app.mainloop()                           # Запускаем бесконечный цикл окна (ждем нажатий)


if __name__ == "__main__":
    # --- ТЕСТОВЫЙ ПРОГОН МОДЕЛИ (без окна) ---
    enc = GearedEncoder("TEST", ppr=200, ratio=10.0)
    enc.rpm = 600.0                          # Ставим максимальную скорость
    for _ in range(10):                      # Делаем 10 шагов
        enc.rotate(0.1)                      # По 0.1 секунде
    print(enc)                               # Проверяем, что импульсы посчитались верно

    # --- ПРОВЕРКА ОШИБОК ---
    try:
        enc.rpm = 99999                      # Пытаемся задать скорость больше 600
    except ValueError as e:
        print("OK, поймали:", e)             # Должно поймать ошибку

    try:
        enc.ratio = -1                       # Пытаемся задать отрицательный редуктор
    except ValueError as e:
        print("OK, поймали:", e)             # Должно поймать ошибку

    main()                                   # Запускаем приложение с интерфейсом