from __future__ import annotations
import random

import matplotlib.pyplot as plt
from domain.models import Vehicle, DeliveryRequest
from algorithms.basic import GreedyVRPPlanner
from algorithms.mcts import MonteCarloVRPPlanner
from simulation.engine import TrafficSimulator
from visualization.html_map import export_plan_to_html



from city.graph import CityGraph

import math  # у тебя уже, скорее всего, импортирован выше

def build_constructor_university_detailed() -> "CityGraph":
    """
    Упрощённая, но достаточно подробная карта района вокруг Constructor University.
    Координаты условные (в условных единицах), но топология похожа:
    - снизу Friedrich-Humbert-Straße
    - слева и справа основные вертикальные улицы
    - внутри кольцо кампуса + внутренние дороги к Campus Green, Krupp и т.д.
    """

    g = CityGraph()

    coords = {
        # Нижняя линия (Friedrich-Humbert-Straße)
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



def plot_city_and_plan(graph: CityGraph, plan, vehicles) -> None:
    fig, ax = plt.subplots()

    for nid, node in graph.nodes.items():
        for e in graph.neighbors(nid):
            src = graph.nodes[e.src]
            dst = graph.nodes[e.dst]
            ax.plot([src.x, dst.x], [src.y, dst.y], linewidth=0.5, color="gray")

    xs = [n.x for n in graph.nodes.values()]
    ys = [n.y for n in graph.nodes.values()]
    ax.scatter(xs, ys, s=20, color="black")
    for nid, node in graph.nodes.items():
        ax.text(node.x, node.y, nid, fontsize=8, ha="center", va="bottom")


    from algorithms.a_star import astar_shortest_path

    v_index = {v.id: v for v in vehicles}

    for vid, route in plan.routes.items():
        v = v_index[vid]
        cur = v.start_node
        full_nodes = [cur]

        for req in route.stops:
            path, _ = astar_shortest_path(graph, cur, req.node)
            if path is None:
                continue
            full_nodes.extend(path[1:])
            cur = req.node

        if not route.stops:
            continue

        # возврат на склад
        path, _ = astar_shortest_path(graph, cur, plan.depot)
        if path is not None:
            full_nodes.extend(path[1:])

        route_x = [graph.nodes[nid].x for nid in full_nodes]
        route_y = [graph.nodes[nid].y for nid in full_nodes]
        ax.plot(route_x, route_y, linewidth=2, label=f"Vehicle {vid}")

    ax.set_aspect("equal", adjustable="datalim")
    ax.legend()
    ax.set_title("City and planned routes")
    plt.tight_layout()
    plt.show()

from typing import List
def generate_random_requests(
    graph: CityGraph,
    depot: str,
    rng: random.Random,
    n_requests: int,
) -> List[DeliveryRequest]:
    # берём все узлы, кроме депо
    candidates = [nid for nid in graph.nodes.keys() if nid != depot]
    # если хочешь только "внутренние" узлы — можно тут отфильтровать по префиксам id
    chosen = rng.sample(candidates, k=min(n_requests, len(candidates)))
    return [
        DeliveryRequest(id=f"R{i+1}", node=nid)
        for i, nid in enumerate(chosen)
    ]

def main() -> None:
    rng = random.Random(42)

    graph = build_constructor_university_detailed()
    depot = "C_GATE_S"

    vehicles = [
        Vehicle(id="V1", capacity=4, start_node=depot),
        Vehicle(id="V2", capacity=4, start_node=depot),
        Vehicle(id="V3", capacity=4, start_node=depot),
    ]

    # вместо ручного списка:
    requests = generate_random_requests(graph, depot, rng, n_requests=9)

    greedy = GreedyVRPPlanner()
    greedy_cost = greedy.build_plan(graph, depot, vehicles, requests)

    mc = MonteCarloVRPPlanner(rng)
    mc_cost = mc.search(graph, depot, vehicles, requests, iterations=500)

    simulator = TrafficSimulator(rng)
    sim_res = simulator.simulate_once(graph, mc_cost.plan, vehicles)
    print("per-vehicle:", sim_res.vehicle_times)
    print("max_time:", sim_res.max_time)

    from visualization.html_map import export_plan_to_html
    export_plan_to_html(graph, mc_cost.plan, vehicles, "output/campus_routes.html")


if __name__ == "__main__":
    main()
