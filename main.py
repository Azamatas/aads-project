from __future__ import annotations
import random

import matplotlib.pyplot as plt
from algorithms.grouping_monte_carlo import MonteCarloGroupingPlanner
from domain.models import Vehicle, DeliveryRequest

from simulation.engine import TrafficSimulator
from visualization.html_map import export_plan_to_html

from city.campus_graph import build_campus_graph
from city.graph import CityGraph


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
    rng = random.Random()

    graph = build_campus_graph()
    depot = "C_GATE_S"

    vehicles = [
        Vehicle(id="V1", capacity=4, start_node=depot),
        Vehicle(id="V2", capacity=4, start_node=depot),
        Vehicle(id="V3", capacity=4, start_node=depot),
    ]

    requests: list[DeliveryRequest] = generate_random_requests(graph, depot, rng, n_requests=9)

    planner = MonteCarloGroupingPlanner(rng, iterations=2000)
    result = planner.build_plan(graph, depot, vehicles, requests)

    print("Estimated makespan (deterministic):", result.makespan_estimate)
    for vid, route in result.plan.routes.items():
        print(vid, "->", [r.id for r in route.stops])


    sim = TrafficSimulator(rng)
    sim_res = sim.simulate_once(graph, result.plan, vehicles)
    print("Stochastic per-vehicle:", sim_res.vehicle_times)
    print("Stochastic max_time:", sim_res.max_time)

    export_plan_to_html(graph, result.plan, vehicles, "output/campus_routes.html")

if __name__ == "__main__":
    main()
