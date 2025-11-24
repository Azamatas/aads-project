from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import random
import math

from city.graph import CityGraph, Edge
from domain.models import Plan, Vehicle
from algorithms.a_star import astar_shortest_path


@dataclass
class SimulationResult:
    vehicle_times: Dict[str, float]
    total_time: float
    max_time: float


class TrafficSimulator:
    """
    Прогоняем готовый план с шумом по рёбрам (имитация пробок/светофоров).
    Пока простая модель: нормальный шум 10% от времени на каждом ребре.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def _edge_time(self, edge: Edge, t_in: float) -> float:
        base = edge.base_travel_time
        sigma = 0.1 * base
        noise = self.rng.gauss(0.0, sigma) if sigma > 0 else 0.0
        return max(0.0, base + noise)

    def simulate_once(
        self,
        graph: CityGraph,
        plan: Plan,
        vehicles: List[Vehicle],
        return_to_depot: bool = True,
    ) -> SimulationResult:
        v_index = {v.id: v for v in vehicles}
        vehicle_times: Dict[str, float] = {}

        for vid, route in plan.routes.items():
            v = v_index[vid]
            cur = v.start_node
            t = 0.0

            for req in route.stops:
                path, _ = astar_shortest_path(graph, cur, req.node)
                if path is None:
                    t = math.inf
                    break
                for i in range(len(path) - 1):
                    src = path[i]
                    dst = path[i + 1]
                    edge = next(e for e in graph.neighbors(src) if e.dst == dst)
                    t += self._edge_time(edge, t)
                cur = req.node

            if return_to_depot and math.isfinite(t) and route.stops:
                path, _ = astar_shortest_path(graph, cur, plan.depot)
                if path is None:
                    t = math.inf
                else:
                    for i in range(len(path) - 1):
                        src = path[i]
                        dst = path[i + 1]
                        edge = next(e for e in graph.neighbors(src) if e.dst == dst)
                        t += self._edge_time(edge, t)

            vehicle_times[vid] = t

        max_time = max(vehicle_times.values()) if vehicle_times else 0.0
        total_time = sum(vehicle_times.values())
        return SimulationResult(
            vehicle_times=vehicle_times,
            total_time=total_time,
            max_time=max_time,
        )
