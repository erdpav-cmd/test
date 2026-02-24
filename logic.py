"""
Игровая логика шариков: движение, инвентарь (всасывание/выплёвывание),
смешивание цветов при касании, зона удаления. Без отталкивания шариков.
Интерфейс не входит в этот модуль.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# Цвет в RGB, компоненты 0.0..1.0
Color = Tuple[float, float, float]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mix_colors(c1: Color, c2: Color) -> Color:
    """
    Смешивание цветов при касании шариков.
    Используется «субтрактивное» смешивание (как краски): результат получается
    тёмнее и насыщеннее, белый (1,1,1) не возникает — это плохой результат.
    """
    r = c1[0] * c2[0]
    g = c1[1] * c2[1]
    b = c1[2] * c2[2]
    # Лёгкое осветление, чтобы не уходить в чёрный, но без приближения к белому
    scale = 1.4
    r = 1.0 - (1.0 - r) / scale
    g = 1.0 - (1.0 - g) / scale
    b = 1.0 - (1.0 - b) / scale
    return (_clamp(r, 0.0, 1.0), _clamp(g, 0.0, 1.0), _clamp(b, 0.0, 1.0))


@dataclass
class Ball:
    """Шарик: позиция, скорость, цвет, радиус. id для однозначной идентификации."""
    x: float
    y: float
    vx: float
    vy: float
    color: Color
    radius: float
    id: int = 0

    def center(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def contains_point(self, px: float, py: float) -> bool:
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= self.radius ** 2

    def distance_to(self, other: Ball) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def overlaps(self, other: Ball) -> bool:
        return self.distance_to(other) < self.radius + other.radius


@dataclass
class Rect:
    """Прямоугольник (например, зона удаления): x, y — левый верхний угол, w, h — размеры."""
    x: float
    y: float
    w: float
    h: float

    def contains_point(self, px: float, py: float) -> bool:
        return (
            self.x <= px <= self.x + self.w
            and self.y <= py <= self.y + self.h
        )


class GameLogic:
    """
    Вся игровая логика: экран, шарики, инвентарь, зона удаления.
    Интерфейс передаёт размеры экрана и вызывает update / suck / spit.
    """

    def __init__(
        self,
        screen_width: float,
        screen_height: float,
        delete_zone: Optional[Rect] = None,
        default_radius: float = 20.0,
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.default_radius = default_radius
        # Зона удаления: если центр шарика попадает сюда — шарик удаляется
        self.delete_zone = delete_zone or Rect(
            screen_width - 80, 0, 80, 60
        )
        self._balls: List[Ball] = []
        self._inventory: List[Ball] = []
        self._next_id = 1

    @property
    def balls(self) -> List[Ball]:
        return self._balls

    @property
    def inventory(self) -> List[Ball]:
        return self._inventory

    def _new_id(self) -> int:
        uid = self._next_id
        self._next_id += 1
        return uid

    def add_ball(
        self,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        color: Optional[Color] = None,
        radius: Optional[float] = None,
    ) -> Ball:
        """Добавить шарик на поле (например, при «выплёвывании» или для тестов)."""
        if color is None:
            color = (0.2, 0.5, 0.9)
        if radius is None:
            radius = self.default_radius
        ball = Ball(x=x, y=y, vx=vx, vy=vy, color=color, radius=radius, id=self._new_id())
        self._balls.append(ball)
        return ball

    def _reflect_from_walls(self, ball: Ball) -> None:
        """Отражение от границ экрана (шарики не вылетают)."""
        r = ball.radius
        if ball.x - r < 0:
            ball.x = r
            ball.vx = abs(ball.vx)
        if ball.x + r > self.screen_width:
            ball.x = self.screen_width - r
            ball.vx = -abs(ball.vx)
        if ball.y - r < 0:
            ball.y = r
            ball.vy = abs(ball.vy)
        if ball.y + r > self.screen_height:
            ball.y = self.screen_height - r
            ball.vy = -abs(ball.vy)

    def _process_collisions(self) -> None:
        """
        Обработка касаний: шарики не отталкиваются, а при касании
        объединяются в один с смешанным цветом.
        """
        merged: set[int] = set()
        new_balls: List[Ball] = []

        for i, a in enumerate(self._balls):
            if a.id in merged:
                continue
            merged_a = False
            for j, b in enumerate(self._balls):
                if i >= j or b.id in merged or a.id in merged:
                    continue
                if not a.overlaps(b):
                    continue
                # Касание: один новый шарик в середине с смешанным цветом
                mx = (a.x + b.x) / 2
                my = (a.y + b.y) / 2
                # Скорость — сумма импульсов, нормализованная по массе (радиусу)
                total_r = a.radius + b.radius
                vx = (a.vx * a.radius + b.vx * b.radius) / total_r
                vy = (a.vy * a.radius + b.vy * b.radius) / total_r
                new_radius = math.sqrt(a.radius ** 2 + b.radius ** 2)  # сохранение «площади»
                new_radius = min(new_radius, max(self.screen_width, self.screen_height) * 0.15)
                new_color = mix_colors(a.color, b.color)
                new_ball = Ball(
                    x=mx, y=my, vx=vx, vy=vy,
                    color=new_color, radius=new_radius, id=self._new_id()
                )
                new_balls.append(new_ball)
                merged.add(a.id)
                merged.add(b.id)
                merged_a = True
                break
            if not merged_a and a.id not in merged:
                new_balls.append(a)

        self._balls = new_balls

    def _process_delete_zone(self) -> None:
        """Удаление шариков, центр которых попал в зону удаления."""
        self._balls = [
            b for b in self._balls
            if not self.delete_zone.contains_point(b.x, b.y)
        ]

    def update(self, dt: float) -> None:
        """
        Шаг симуляции на dt секунд:
        движение, отражение от стен, объединение при касании, удаление в зоне.
        """
        for ball in self._balls:
            ball.x += ball.vx * dt
            ball.y += ball.vy * dt
            self._reflect_from_walls(ball)

        self._process_collisions()
        self._process_delete_zone()

    def suck_ball(self, mouse_x: float, mouse_y: float) -> Optional[Ball]:
        """
        «Всасывание»: шарик под курсором перемещается в инвентарь.
        Возвращает всасанный шарик или None, если под курсором никого нет.
        Приоритет — ближайший к курсору из пересекающихся.
        """
        candidates = [
            (b, (b.x - mouse_x) ** 2 + (b.y - mouse_y) ** 2)
            for b in self._balls
            if b.contains_point(mouse_x, mouse_y)
        ]
        if not candidates:
            return None
        ball, _ = min(candidates, key=lambda p: p[1])
        self._balls.remove(ball)
        self._inventory.append(ball)
        return ball

    def spit_ball(
        self,
        mouse_x: float,
        mouse_y: float,
        velocity: Optional[Tuple[float, float]] = None,
    ) -> Optional[Ball]:
        """
        «Выплёвывание»: последний шарик из инвентаря возвращается на поле
        в позицию курсора. velocity — начальная скорость (vx, vy); если None — (0, 0).
        Возвращает выплюнутый шарик или None, если инвентарь пуст.
        """
        if not self._inventory:
            return None
        ball = self._inventory.pop()
        ball.x = mouse_x
        ball.y = mouse_y
        if velocity is not None:
            ball.vx, ball.vy = velocity
        else:
            ball.vx = ball.vy = 0.0
        self._balls.append(ball)
        return ball

    def set_delete_zone(self, zone: Rect) -> None:
        """Задать зону удаления (например, угол экрана)."""
        self.delete_zone = zone
