"""
Графический интерфейс для игры с шариками.
Использует logic.py: движение, всасывание/выплёвывание, смешивание цветов, зона удаления.
"""

import random
import tkinter as tk
from tkinter import Canvas

from logic import GameLogic, Rect

# ============== НАСТРОЙКИ (меняй здесь) ==============
STARTING_BALLS_COUNT = 50
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
BACKGROUND_COLOR = "#ffffff"
DELETE_ZONE_COLOR = "#ffcccc"
DELETE_ZONE_OUTLINE = "#cc0000"
FPS = 60
# ====================================================


def rgb_to_hex(color):
    """Преобразование (r, g, b) 0..1 в строку #RRGGBB."""
    r, g, b = color
    return "#{:02x}{:02x}{:02x}".format(
        int(max(0, min(1, r)) * 255),
        int(max(0, min(1, g)) * 255),
        int(max(0, min(1, b)) * 255),
    )


def random_color():
    """Случайный насыщенный цвет (не белый)."""
    return (
        random.uniform(0.3, 0.95),
        random.uniform(0.3, 0.95),
        random.uniform(0.3, 0.95),
    )


class GameWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Шарики — всасывание, смешивание, зона удаления")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BACKGROUND_COLOR)

        # Зона удаления — правый верхний угол
        delete_zone = Rect(WINDOW_WIDTH - 90, 0, 90, 70)
        self.game = GameLogic(
            screen_width=WINDOW_WIDTH,
            screen_height=WINDOW_HEIGHT,
            delete_zone=delete_zone,
            default_radius=18.0,
        )

        self.canvas = Canvas(
            self.root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg=BACKGROUND_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._spawn_initial_balls()
        self._last_time = None
        self._inventory_label = None
        self._setup_ui_labels()
        self._setup_bindings()
        self._draw_delete_zone()
        self._running = True
        self.root.after(0, self._tick)

    def _spawn_initial_balls(self):
        """Создать стартовые шарики в случайных местах с небольшими скоростями."""
        margin = 80
        for _ in range(STARTING_BALLS_COUNT):
            x = random.uniform(margin, WINDOW_WIDTH - margin)
            y = random.uniform(margin, WINDOW_HEIGHT - margin)
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(30, 80)
            vx = speed * (0.5 - random.random())
            vy = speed * (0.5 - random.random())
            self.game.add_ball(x, y, vx, vy, color=random_color())

    def _setup_ui_labels(self):
        """Подсказки и счётчик инвентаря."""
        self.canvas.create_text(
            WINDOW_WIDTH // 2,
            18,
            text="ЛКМ — всасывать шарик | ПКМ — выпустить шарик | Перетащите шарик в красную зону — удалить",
            fill="#333",
            font=("Segoe UI", 10),
        )
        self._inventory_label = self.canvas.create_text(
            12,
            WINDOW_HEIGHT - 20,
            anchor=tk.W,
            text="В инвентаре: 0",
            fill="#555",
            font=("Segoe UI", 11),
        )

    def _setup_bindings(self):
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

    def _on_left_click(self, event):
        """ЛКМ — всасывание шарика под курсором."""
        self.game.suck_ball(event.x, event.y)

    def _on_right_click(self, event):
        """ПКМ — выпустить шарик из инвентаря в позицию курсора."""
        self.game.spit_ball(event.x, event.y, velocity=(0, 0))

    def _draw_delete_zone(self):
        """Отрисовка зоны удаления (красноватый прямоугольник)."""
        z = self.game.delete_zone
        self.canvas.create_rectangle(
            z.x, z.y, z.x + z.w, z.y + z.h,
            fill=DELETE_ZONE_COLOR,
            outline=DELETE_ZONE_OUTLINE,
            width=2,
            tags="delete_zone",
        )
        self.canvas.create_text(
            z.x + z.w / 2, z.y + z.h / 2,
            text="УДАЛИТЬ",
            fill=DELETE_ZONE_OUTLINE,
            font=("Segoe UI", 11, "bold"),
            tags="delete_zone",
        )

    def _redraw(self):
        """Перерисовать все шарики и обновить подпись инвентаря."""
        self.canvas.delete("ball")
        for ball in self.game.balls:
            color = rgb_to_hex(ball.color)
            self.canvas.create_oval(
                ball.x - ball.radius,
                ball.y - ball.radius,
                ball.x + ball.radius,
                ball.y + ball.radius,
                fill=color,
                outline="#333",
                width=1,
                tags="ball",
            )
        self.canvas.itemconfig(
            self._inventory_label,
            text=f"В инвентаре: {len(self.game.inventory)}",
        )

    def _tick(self):
        if not self._running:
            return
        import time
        now = time.perf_counter()
        if self._last_time is not None:
            dt = min(now - self._last_time, 0.1)
            self.game.update(dt)
        self._last_time = now
        self._redraw()
        self.root.after(1000 // FPS, self._tick)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._running = False
        self.root.destroy()


if __name__ == "__main__":
    app = GameWindow()
    app.run()
