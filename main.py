from __future__ import annotations
import random

import matplotlib.pyplot as plt

from city.graph import CityGraph
from domain.models import Vehicle, DeliveryRequest
from algorithms.basic import GreedyVRPPlanner
from algorithms.mcts import MonteCarloVRPPlanner
from simulation.engine import TrafficSimulator


from city.graph import CityGraph

def build_demo_city() -> CityGraph:
    g = CityGraph()

    # 10 перекрёстков
    coords = {
        "A": (0.0, 0.0),   # склад
        "B": (1.0, 0.2),
        "C": (2.0, 0.1),
        "D": (2.5, 0.8),
        "E": (2.0, 1.5),
        "F": (1.0, 1.8),
        "G": (0.0, 1.5),
        "H": (-0.5, 0.8),
        "I": (1.5, 0.9),
        "J": (0.5, 0.9),
    }

    for nid, (x, y) in coords.items():
        g.add_node(nid, x, y)

    speed = 10.0  # м/с

    # основное "кольцо"
    g.add_edge("A", "B", 120, speed, bidirectional=True)
    g.add_edge("B", "C", 130, speed, bidirectional=True)
    g.add_edge("C", "D", 100, speed, bidirectional=True)
    g.add_edge("D", "E", 110, speed, bidirectional=True)
    g.add_edge("E", "F", 120, speed, bidirectional=True)
    g.add_edge("F", "G", 130, speed, bidirectional=True)
    g.add_edge("G", "H", 120, speed, bidirectional=True)
    g.add_edge("H", "A", 110, speed, bidirectional=True)

    # диагонали / «магистрали»
    g.add_edge("B", "I", 90, speed, bidirectional=True)
    g.add_edge("I", "E", 100, speed, bidirectional=True)
    g.add_edge("J", "F", 90, speed, bidirectional=True)
    g.add_edge("J", "A", 90, speed, bidirectional=True)
    g.add_edge("J", "I", 70, speed, bidirectional=True)

    return g




def plot_city_and_plan(graph: CityGraph, plan, vehicles) -> None:
    fig, ax = plt.subplots()

    # граф
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

    # маршруты
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


def main() -> None:
    rng = random.Random(42)

    graph = build_demo_city()
    depot = "A"

    vehicles = [
        Vehicle(id="V1", capacity=4, start_node=depot),
        Vehicle(id="V2", capacity=4, start_node=depot),
        Vehicle(id="V3", capacity=4, start_node=depot),
    ]

    # заказы в разных вершинах (кроме склада A)
    request_nodes = ["B", "C", "D", "E", "F", "G", "H", "I", "J"]
    requests = [
        DeliveryRequest(id=f"R{k+1}", node=n)
        for k, n in enumerate(request_nodes)
    ]

    # Greedy baseline
    greedy = GreedyVRPPlanner()
    greedy_cost = greedy.build_plan(graph, depot, vehicles, requests)
    print("Greedy total deterministic time:", greedy_cost.total_time)
    for vid, route in greedy_cost.plan.routes.items():
        print("Greedy", vid, "->", [r.id for r in route.stops])

    # Monte Carlo
    mc = MonteCarloVRPPlanner(rng)
    mc_cost = mc.search(graph, depot, vehicles, requests, iterations=500)
    print("\nMonte Carlo total deterministic time:", mc_cost.total_time)
    for vid, route in mc_cost.plan.routes.items():
        print("MC    ", vid, "->", [r.id for r in route.stops])

    # симуляция для лучшего плана
    simulator = TrafficSimulator(rng)
    sim_res = simulator.simulate_once(graph, mc_cost.plan, vehicles)
    print("\nStochastic simulation (single run):")
    print("per-vehicle:", sim_res.vehicle_times)
    print("max_time:", sim_res.max_time)

    # визуализация плана Monte Carlo
    plot_city_and_plan(graph, mc_cost.plan, vehicles)


if __name__ == "__main__":
    main()
