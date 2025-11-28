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
    Простой baseline:
    – capacity трактуем как максимальный груз за ОДИН рейс.
    – если заказов больше, машина делает несколько рейсов:
      depot -> ...заказы... -> depot -> ...ещё заказы... -> depot.
    – build_plan не ограничивает общее число заказов на машину, только следит,
      что каждый отдельный заказ в принципе помещается (demand <= capacity).
    """

    def _route_cost(
        self,
        graph: CityGraph,
        vehicle: Vehicle,
        stops: List[DeliveryRequest],
        depot: NodeId,
        return_to_depot: bool = True,
    ) -> float:
        """
        Стоимость маршрута для ПОЛНОГО списка stops с учётом capacity:
        машина может делать несколько рейсов к складу.
        """
        cur = vehicle.start_node
        t = 0.0
        cap = vehicle.capacity
        if cap <= 0:
            return float("inf")

        cap_left = cap

        for req in stops:
            demand = getattr(req, "demand", 1)
            if demand <= 0:
                return float("inf")

            # если под следующий заказ не хватает места – сначала домой
            if cap_left < demand:
                if cur != depot:
                    path, travel = astar_shortest_path(graph, cur, depot)
                    if path is None:
                        return float("inf")
                    t += travel
                    cur = depot
                cap_left = cap

            # едем к заказу
            path, travel = astar_shortest_path(graph, cur, req.node)
            if path is None:
                return float("inf")
            t += travel
            cur = req.node
            cap_left -= demand

        # в конце, если нужно, возвращаемся на depot
        if return_to_depot and cur != depot:
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
        # safety: каждый заказ должен помещаться хотя бы в одну машину
        for req in requests:
            demand = getattr(req, "demand", 1)
            if all(v.capacity < demand for v in vehicles):
                raise RuntimeError(
                    f"Request {req.id} has demand {demand}, "
                    f"но ни одна машина не может увезти его за один рейс"
                )

        remaining = requests[:]
        routes: Dict[str, VehicleRoute] = {
            v.id: VehicleRoute(vehicle_id=v.id) for v in vehicles
        }

        while remaining:
            best_choice: Optional[tuple[str, DeliveryRequest, float]] = None

            for req in remaining:
                demand = getattr(req, "demand", 1)
                for v in vehicles:
                    # эта машина хотя бы теоретически может увезти этот заказ
                    if v.capacity < demand:
                        continue

                    stops = routes[v.id].stops + [req]
                    cost = self._route_cost(graph, v, stops, depot)
                    if best_choice is None or cost < best_choice[2]:
                        best_choice = (v.id, req, cost)

            if best_choice is None:
                # теоретически не должно случаться, так как выше мы проверили demand <= max capacity
                raise RuntimeError("Cannot build feasible greedy plan (no vehicle can take remaining requests)")

            vid, chosen_req, _ = best_choice
            routes[vid].stops.append(chosen_req)
            remaining.remove(chosen_req)

        total_time = 0.0
        for v in vehicles:
            total_time += self._route_cost(graph, v, routes[v.id].stops, depot)

        return PlanCost(
            plan=Plan(depot=depot, routes=routes),
            total_time=total_time,
        )
