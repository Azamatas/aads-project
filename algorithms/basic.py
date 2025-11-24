from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

from city.graph import CityGraph, NodeId
from domain.models import Vehicle, DeliveryRequest, VehicleRoute, Plan
from algorithms.a_star import astar_shortest_path


@dataclass
class PlanCost:
    plan: Plan
    total_time: float


class GreedyVRPPlanner:
    """
    Простой baseline: для каждой машины берём "ближайшего" ещё не обслуженного клиента.
    """

    def _route_cost(
        self,
        graph: CityGraph,
        vehicle: Vehicle,
        stops: List[DeliveryRequest],
        depot: NodeId,
        return_to_depot: bool = True,
    ) -> float:
        cur = vehicle.start_node
        t = 0.0

        for req in stops:
            path, travel = astar_shortest_path(graph, cur, req.node)
            if path is None:
                return float("inf")
            t += travel
            cur = req.node

        if return_to_depot and stops:
            path, travel = astar_shortest_path(graph, cur, depot)
            if path is None:
                return float("inf")
            t += travel

        return t

    def build_plan(
        self,
        graph: CityGraph,
        depot: NodeId,
        vehicles: List[Vehicle],
        requests: List[DeliveryRequest],
    ) -> PlanCost:
        remaining = requests[:]
        routes: Dict[str, VehicleRoute] = {
            v.id: VehicleRoute(vehicle_id=v.id) for v in vehicles
        }
        capacities_left: Dict[str, int] = {v.id: v.capacity for v in vehicles}

        while remaining:
            best_choice: Optional[tuple[str, DeliveryRequest, float]] = None

            for req in remaining:
                for v in vehicles:
                    if capacities_left[v.id] < req.demand:
                        continue

                    stops = routes[v.id].stops + [req]
                    cost = self._route_cost(graph, v, stops, depot)
                    if best_choice is None or cost < best_choice[2]:
                        best_choice = (v.id, req, cost)

            if best_choice is None:
                raise RuntimeError("Cannot build feasible greedy plan")

            vid, chosen_req, _ = best_choice
            routes[vid].stops.append(chosen_req)
            capacities_left[vid] -= chosen_req.demand
            remaining.remove(chosen_req)

        total_time = 0.0
        for v in vehicles:
            total_time += self._route_cost(
                graph, v, routes[v.id].stops, depot
            )

        return PlanCost(plan=Plan(depot=depot, routes=routes),
                        total_time=total_time)
