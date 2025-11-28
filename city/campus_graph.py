# city/campus_graph.py
from __future__ import annotations
from typing import Dict
import math

from city.graph import CityGraph, NodeId


def build_campus_graph() -> "CityGraph":

    g = CityGraph()

    coords = {
        "FH_W": (0.0, 0.0),   # западный перекрёсток
        "FH_M": (4.0, 0.0),   # центральный въезд к кампусу
        "FH_E": (8.0, 0.0),   # восточный перекрёсток

        # Левая вертикаль (Südstraße / Brun-Brüg-Straße)
        "W_S": (0.0, 1.5),
        "W_M": (0.0, 3.5),
        "W_N": (0.0, 7.5),

        # Правая вертикаль (Manfred-Eggert-Straße)
        "E_S": (8.0, 1.5),
        "E_M": (8.0, 3.5),
        "E_N": (8.0, 7.5),

        # Верхняя улица (Steingutstraße)
        "ST_W": (1.0, 8.0),
        "ST_M": (4.0, 8.0),
        "ST_E": (7.0, 8.0),

        # Въезд в кампус и центральная вертикаль через кампус
        "C_GATE_S": (4.0, 1.5),  # въезд в кампус
        "C_MID":    (4.0, 4.0),  # район главного кампуса
        "C_PARK":   (4.0, 6.5),  # северный парк над кампусом

        # Внутреннее "кольцо" кампуса (примерный прямоугольник)
        "R_SW": (2.0, 2.0),
        "R_SE": (6.0, 2.0),
        "R_NE": (6.0, 6.0),
        "R_NW": (2.0, 6.0),

        # Важные точки внутри
        "C_MAIN":   (4.0, 3.8),  # основной кампус
        "C_GREEN":  (3.6, 4.6),  # Campus Green
        "KRUPP_S":  (5.5, 3.5),
        "KRUPP_N":  (5.5, 4.7),
        "PARK_N":   (4.0, 7.5),  # северный парк ближе к Steingutstraße
    }

    for nid, (x, y) in coords.items():
        g.add_node(nid, x, y)

    # небольшой helper, чтобы длины были согласованы с координатами
    def road(a: str, b: str, speed_limit: float, bidirectional: bool = True) -> None:
        na = g.nodes[a]
        nb = g.nodes[b]
        dist = math.hypot(na.x - nb.x, na.y - nb.y)
        # умножаем на 100, чтобы получить "метры" (масштаб условный)
        g.add_edge(a, b, length=dist * 100.0, speed_limit=speed_limit,
                   bidirectional=bidirectional)

    # Скорости: "артериальные" улицы и внутренние
    V_MAIN = 13.9  # ~50 км/ч
    V_LOCAL = 8.3  # ~30 км/ч

    # ----------------- Внешний контур дорог -----------------

    # Friedrich-Humbert-Straße
    road("FH_W", "FH_M", V_MAIN)
    road("FH_M", "FH_E", V_MAIN)

    # Левая вертикаль
    road("FH_W", "W_S", V_MAIN)
    road("W_S", "W_M", V_MAIN)
    road("W_M", "W_N", V_MAIN)

    # Правая вертикаль
    road("FH_E", "E_S", V_MAIN)
    road("E_S", "E_M", V_MAIN)
    road("E_M", "E_N", V_MAIN)

    # Верхняя улица Steingutstraße + стыковки
    road("W_N", "ST_W", V_MAIN)
    road("ST_W", "ST_M", V_MAIN)
    road("ST_M", "ST_E", V_MAIN)
    road("ST_E", "E_N", V_MAIN)

    # Связи верха с центром
    road("ST_M", "C_PARK", V_LOCAL)
    road("C_PARK", "C_MID", V_LOCAL)

    # ----------------- Внутреннее кольцо кампуса -----------------

    # Кольцо
    road("R_SW", "R_SE", V_LOCAL)
    road("R_SE", "R_NE", V_LOCAL)
    road("R_NE", "R_NW", V_LOCAL)
    road("R_NW", "R_SW", V_LOCAL)

    # Связь кольца с внешними улицами
    road("FH_M", "C_GATE_S", V_LOCAL)
    road("C_GATE_S", "R_SW", V_LOCAL)
    road("C_GATE_S", "R_SE", V_LOCAL)

    road("W_S", "R_SW", V_LOCAL)
    road("E_S", "R_SE", V_LOCAL)
    road("W_N", "R_NW", V_LOCAL)
    road("E_N", "R_NE", V_LOCAL)

    # ----------------- Внутренние дороги к объектам кампуса -----------------

    # Ось через кампус
    road("C_GATE_S", "C_MID", V_LOCAL)
    road("C_MID", "C_PARK", V_LOCAL)

    # Campus Main / Green
    road("R_SW", "C_MAIN", V_LOCAL)
    road("R_SE", "C_MAIN", V_LOCAL)
    road("C_MAIN", "C_GREEN", V_LOCAL)
    road("R_NW", "C_GREEN", V_LOCAL)
    road("R_NE", "C_GREEN", V_LOCAL)

    # Krupp College (справа от центра)
    road("R_SE", "KRUPP_S", V_LOCAL)
    road("KRUPP_S", "KRUPP_N", V_LOCAL)
    road("KRUPP_N", "R_NE", V_LOCAL)

    # Парк на севере
    road("C_PARK", "PARK_N", V_LOCAL)
    road("PARK_N", "ST_M", V_LOCAL)

    return g