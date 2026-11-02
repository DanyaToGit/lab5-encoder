Федеральное государственное автономное образовательное учреждение высшего образования
«Омский государственный технический университет»
Кафедра «Автоматизация и робототехника»


ОТЧЕТ 
по лабораторной работе №5
«Объектно-ориентированное программирование (ООП) в приложении с оконным интерфейсом»


Выполнил: ст. гр. УТС-251т Замарин Д. А.
«___» ____________ 20__ г.


Проверил: доц., К. Н. 
Ситников Д. В. 
«___» ____________ 20__ г.   



Омск, 2026 г.



Вариант 11
Цель работы: изучить основы объектно-ориентированного программирования в Python (классы,
инкапсуляция, наследование, полиморфизм) и получить практические навыки разработки настольного
приложения с графическим интерфейсом на библиотеке Tkinter для моделирования и контроля
мехатронного объекта


Энкодер вала. Классы: Encoder (число импульсов на оборот, счётчик), GearedEncoder (потомок, учёт передаточного числа). Окно: кнопки «Вращать вперёд/назад» (шаг по таймеру), Canvas с вращающейся стрелкой, вывод угла (рад, град), числа оборотов и скорости (об/мин); кнопка обнуления счётчика.

код для решения задания 
```python
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
```


Описание работы программы
Программа разделена на две логические части: модель (классы Encoder и GearedEncoder) и интерфейс (класс EncoderApp). Такое разделение позволяет тестировать логику энкодера отдельно от окна и делает код чище.

1. Класс Encoder (Базовый класс модели)
Этот класс описывает физику работы обычного энкодера: подсчет импульсов, вычисление угла и скорости.

Атрибуты класса (переменные):

MAX_RPM = 600.0 — константа класса. Задает максимально допустимую скорость вращения (600 об/мин). Используется для проверки ввода.

name (строка) — имя энкодера (например, "ENC-1").

_ppr (целое число) — pulses per revolution. Количество импульсов, которое энкодер генерирует за один полный оборот вала (по умолчанию 200).

_count (целое число) — текущий счетчик импульсов. Именно он увеличивается или уменьшается при вращении.

_rpm (дробное число) — текущая скорость вращения в оборотах в минуту (может быть отрицательной при реверсе).

_phase (дробное число) — «аккумулятор фазы». Поскольку импульсы — это целые числа, а за маленький шаг времени (dt) энкодер может не успеть сгенерировать целый импульс, дробная часть сохраняется здесь и переносится на следующий шаг. Это предотвращает потерю точности на малых скоростях.

Свойства (@property и @setter) — Инкапсуляция:

ppr — позволяет читать и изменять _ppr. Сеттер проверяет, чтобы значение было больше нуля, иначе выбрасывает ошибку ValueError.

count — свойство только для чтения. Мы можем узнать количество импульсов, но не можем изменить его напрямую (изменить можно только через метод rotate).

rpm — позволяет читать и задавать скорость. Сеттер проверяет, чтобы скорость не превышала MAX_RPM по модулю.

Методы (функции):

__init__(self, name, ppr=200) — конструктор. Вызывается при создании объекта. Задает имя, количество импульсов, обнуляет счетчик, скорость и фазу.

_impulses_per_rev(self) — вспомогательный метод. Возвращает количество импульсов на оборот. В базовом классе просто возвращает _ppr (нужен для переопределения в потомке).

revolutions(self) — вычисляет количество полных оборотов вала: _count / _impulses_per_rev().

angle_rad(self) — вычисляет текущий угол поворота в радианах (от 0 до 2π). Берется остаток от деления, чтобы угол «сбрасывался» после полного оборота.

angle_deg(self) — переводит угол из радиан в градусы (от 0 до 360).

output_rpm(self) — возвращает скорость на выходном валу. В базовом классе совпадает с _rpm.

rotate(self, dt) — главный метод симуляции. Принимает шаг времени dt. Считает, сколько импульсов должно добавиться за это время: (об/мин / 60) * (импульсов на оборот) * dt. Добавляет результат в _phase. Целую часть отдает в _count, а дробную оставляет в _phase.

reset(self) — сбрасывает счетчик, скорость и фазу в ноль.

__str__(self) — магический метод. Задает красивое строковое представление объекта. Вызывается, когда мы делаем print(encoder) или передаем объект в текстовую метку.

2. Класс GearedEncoder (Потомок — Наследование и Полиморфизм)
Этот класс описывает энкодер, который стоит на двигателе, но мы считываем вращение с выходного вала редуктора. У него появляется передаточное число.

Атрибуты:

_ratio (дробное число) — передаточное число редуктора. Показывает, во сколько раз выходной вал вращается медленнее входного (например, 10.0).

Свойства:

ratio — чтение и запись _ratio с проверкой, что число больше нуля.

Методы:

__init__(self, name, ppr=200, ratio=10.0) — конструктор. Через super().__init__(name, ppr) вызывает конструктор родителя (чтобы не дублировать код), а затем добавляет _ratio.

_impulses_per_rev(self) — переопределенный метод (полиморфизм). Теперь возвращает ppr * ratio, так как на выходе импульсов больше.

output_rpm(self) — переопределенный метод. Возвращает _rpm / ratio, так как выходной вал вращается медленнее.

__str__(self) — переопределенный метод. Возвращает свою строку, указывая передаточное число.

3. Класс EncoderApp (Интерфейс — наследник tk.Tk)
Этот класс отвечает только за окно, кнопки и отрисовку. Он не считает физику, а только дергает методы модели.

Атрибуты:

SIZE, CENTER, ARROW, DT — константы для рисования (размер холста, центр, длина стрелки) и шаг таймера (0.05 сек).

encoder — ссылка на объект модели (Encoder или GearedEncoder).

running (логический) — флаг. Если True, таймер двигает стрелку. Если False — стоит на паузе.

info, rpm_var, angle_var — специальные переменные Tkinter (StringVar, DoubleVar). Они связывают данные Python с виджетами (метками и ползунком), автоматически обновляя их на экране.

Методы:

__init__(self, encoder) — создает окно, привязывает модель, строит виджеты (_build_widgets) и запускает первый таймер (after).

_build_widgets(self) — создает все кнопки, ползунки, холст и прогрессбар. Располагает их на экране с помощью pack и grid.

_on_rpm_change(self, value) — обработчик ползунка скорости. Пытается передать значение в модель. Если модель выбрасывает ошибку (скорость слишком большая) — ловит ее через try/except, показывает messagebox и откатывает ползунок назад.

_start_forward / _start_backward — обработчики кнопок. Включают флаг running = True и задают скорость (положительную или отрицательную).

_stop — останавливает вращение, ставит скорость в 0.

_reset — останавливает вращение и вызывает encoder.reset().

_apply_ratio — считывает текст из поля ввода передаточного числа. Если пусто или ошибка — показывает диалоговое окно.

_tick(self) — сердце программы. Вызывается каждые 50 мс через self.after(). Если running == True, вызывает encoder.rotate(DT), чтобы модель сделала шаг, а затем _redraw(), чтобы перерисовать картинку.

_redraw(self) — рисует на Canvas: стирает старую картинку (delete("all")), рисует окружность циферблата, деления, и красную стрелку под углом из модели. Также обновляет Progressbar и текстовые метки.

4. Функция main() и точка входа
main() — создает объект модели GearedEncoder и объект окна EncoderApp, после чего запускает бесконечный цикл окна app.mainloop().

Блок if __name__ == "__main__": — выполняется только при прямом запуске файла. Внутри происходит тестовый прогон модели (цикл из 10 шагов), проверка ошибок и вызов функции main(). Это позволяет проверить математику без открытия окна.

Результат программы 
рисунок 1 - 