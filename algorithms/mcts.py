from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional
import random

from city.graph import CityGraph, NodeId
from domain.models import Vehicle, DeliveryRequest, VehicleRoute, Plan
from algorithms.a_star import astar_shortest_path


@dataclass
class PlanCost:
    plan: Plan
    total_time: float


class MonteCarloVRPPlanner:
    """
    Простая Monte Carlo версия:
    - случайно распределяем клиентов по машинам (с учётом capacity)
    - считаем детерминированное время, берём лучший вариант.
    Позже сюда можно добавить настоящую MCTS-логику.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.rng = rng or random.Random()

    def _random_feasible_plan(
            self,
            depot: NodeId,
            vehicles: List[Vehicle],
            requests: List[DeliveryRequest],
    ) -> Plan:
        shuffled = requests[:]
        self.rng.shuffle(shuffled)

        routes: Dict[str, VehicleRoute] = {
            v.id: VehicleRoute(vehicle_id=v.id) for v in vehicles
        }

        # Просто случайно раскидываем заказы по машинам
        for req in shuffled:
            v = self.rng.choice(vehicles)
            routes[v.id].stops.append(req)

        return Plan(depot=depot, routes=routes)

    def _deterministic_cost(
            self,
            graph: CityGraph,
            vehicles: List[Vehicle],
            plan: Plan,
            return_to_depot: bool = True,
    ) -> PlanCost:
        total_time = 0.0
        v_index = {v.id: v for v in vehicles}

        for vid, route in plan.routes.items():
            v = v_index[vid]
            cap = v.capacity
            if cap <= 0:
                return PlanCost(plan, float("inf"))

            cur = v.start_node
            t = 0.0
            cap_left = cap

            for req in route.stops:
                demand = getattr(req, "demand", 1)
                if demand <= 0:
                    return PlanCost(plan, float("inf"))

                # если не хватает места — возвращаемся на depot и начинаем новый рейс
                if cap_left < demand:
                    if cur != plan.depot:
                        path, travel = astar_shortest_path(graph, cur, plan.depot)
                        if path is None:
                            return PlanCost(plan, float("inf"))
                        t += travel
                        cur = plan.depot
                    cap_left = cap

                # едем к заказу
                path, travel = astar_shortest_path(graph, cur, req.node)
                if path is None:
                    return PlanCost(plan, float("inf"))
                t += travel
                cur = req.node
                cap_left -= demand

            # в конце возвращаемся на depot (если нужно)
            if return_to_depot and cur != plan.depot:
                path, travel = astar_shortest_path(graph, cur, plan.depot)
                if path is None:
                    return PlanCost(plan, float("inf"))
                t += travel

            total_time += t

        return PlanCost(plan=plan, total_time=total_time)

    def search(
        self,
        graph: CityGraph,
        depot: NodeId,
        vehicles: List[Vehicle],
        requests: List[DeliveryRequest],
        iterations: int = 1000,
    ) -> PlanCost:
        best: Optional[PlanCost] = None

        for _ in range(iterations):
            try:
                plan = self._random_feasible_plan(depot, vehicles, requests)
            except RuntimeError:
                continue
            cost = self._deterministic_cost(graph, vehicles, plan)
            if best is None or cost.total_time < best.total_time:
                best = cost

        if best is None:
            raise RuntimeError("Failed to find any feasible plan")

        return best
