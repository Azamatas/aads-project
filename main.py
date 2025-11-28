from __future__ import annotations
import random
from typing import List

import matplotlib.pyplot as plt

from algorithms.grouping_monte_carlo import MonteCarloGroupingPlanner
from algorithms.basic import GreedyVRPPlanner

from domain.models import Vehicle, DeliveryRequest
from simulation.engine import TrafficSimulator
from visualization.html_map import export_plan_to_html
from city.campus_graph import build_campus_graph
from city.graph import CityGraph


def plot_city_and_plan(graph: CityGraph, plan, vehicles) -> None:
    fig, ax = plt.subplots()

    # серые ребра графа
    for nid, node in graph.nodes.items():
        for e in graph.neighbors(nid):
            src = graph.nodes[e.src]
            dst = graph.nodes[e.dst]
            ax.plot([src.x, dst.x], [src.y, dst.y], linewidth=0.5, color="gray")

    # узлы и подписи
    xs = [n.x for n in graph.nodes.values()]
    ys = [n.y for n in graph.nodes.values()]
    ax.scatter(xs, ys, s=20, color="black")
    for nid, node in graph.nodes.items():
        ax.text(node.x, node.y, nid, fontsize=8, ha="center", va="bottom")

    # отрисовка маршрутов по кратчайшим путям
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

def validate_inputs(vehicles, requests):
    # capacity машин > 0
    for v in vehicles:
        if v.capacity <= 0:
            raise ValueError(f"Vehicle {v.id} has non-positive capacity: {v.capacity}")

    # demand заказов > 0 (если у тебя есть поле demand)
    for r in requests:
        d = getattr(r, "demand", 1)
        if d <= 0:
            raise ValueError(f"Request {r.id} has non-positive demand: {d}")


def generate_random_requests(
    graph: CityGraph,
    depot: str,
    rng: random.Random,
    n_requests: int,
) -> List[DeliveryRequest]:
    """
    Генерируем n_requests запросов на разных нодах (кроме депо).
    """
    candidates = [nid for nid in graph.nodes.keys() if nid != depot]
    if n_requests > len(candidates):
        raise ValueError(
            f"Requested {n_requests} requests, but only {len(candidates)} nodes available"
        )
    chosen = rng.sample(candidates, k=n_requests)
    return [
        DeliveryRequest(id=f"R{i+1}", node=nid)
        for i, nid in enumerate(chosen)
    ]


def main() -> None:
    # фиксированный сид → воспроизводимая картинка; хочешь рандом — сделай Random()
    # rng = random.Random()
    rng = random.Random(42)

    graph = build_campus_graph()
    depot = "C_GATE_S"

    vehicles = [
        Vehicle(id="V1", capacity=4, start_node=depot),
        Vehicle(id="V2", capacity=4, start_node=depot),
        Vehicle(id="V3", capacity=4, start_node=depot),
    ]

    # генерим случайные, но уникальные по нодам запросы
    requests: list[DeliveryRequest] = generate_random_requests(
        graph, depot, rng, n_requests=9
    )

    validate_inputs(vehicles, requests)

    print("Generated requests:")
    for r in requests:
        print(f"  {r.id} -> node {r.node}")
    print()

    # --- 1) Greedy ---
    greedy_planner = GreedyVRPPlanner()
    greedy_result = greedy_planner.build_plan(graph, depot, vehicles, requests)
    greedy_plan = greedy_result.plan
    print("[Greedy] deterministic total_time:", greedy_result.total_time)
    for vid, route in greedy_plan.routes.items():
        print("[Greedy]", vid, "->", [r.id for r in route.stops])
    print()

    # --- 2) Monte Carlo Grouping ---
    mc_planner = MonteCarloGroupingPlanner(rng, iterations=2000)
    mc_result = mc_planner.build_plan(graph, depot, vehicles, requests)
    mc_plan = mc_result.plan
    print("[MonteCarlo] deterministic makespan_estimate:", mc_result.makespan_estimate)
    for vid, route in mc_plan.routes.items():
        print("[MonteCarlo]", vid, "->", [r.id for r in route.stops])
    print()

    # --- 3) Стохастическая симуляция для обоих ---
    sim = TrafficSimulator(rng)

    sim_res_greedy = sim.simulate_once(graph, greedy_plan, vehicles)
    print("[Greedy] stochastic per-vehicle:", sim_res_greedy.vehicle_times)
    print("[Greedy] stochastic max_time:", sim_res_greedy.max_time)
    print()

    sim_res_mc = sim.simulate_once(graph, mc_plan, vehicles)
    print("[MonteCarlo] stochastic per-vehicle:", sim_res_mc.vehicle_times)
    print("[MonteCarlo] stochastic max_time:", sim_res_mc.max_time)
    print()

    # --- 4) Экспорт обоих планов в один HTML с выбором алгоритма ---
    plans_by_algo = {
        "Greedy VRP": greedy_plan,
        "Monte Carlo Grouping": mc_plan,
    }

    export_plan_to_html(graph, plans_by_algo, vehicles, "output/campus_routes.html")
    print("\nOpen output/campus_routes.html in your browser to see the map.")


if __name__ == "__main__":
    main()
