from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from city.graph import NodeId


@dataclass
class Vehicle:
    id: str
    capacity: int
    start_node: NodeId


@dataclass
class DeliveryRequest:
    id: str
    node: NodeId
    demand: int = 1


@dataclass
class VehicleRoute:
    vehicle_id: str
    stops: List[DeliveryRequest] = field(default_factory=list)


@dataclass
class Plan:
    """План VRP: для каждой машины свой маршрут по клиентам."""
    depot: NodeId
    routes: Dict[str, VehicleRoute]

    def all_request_ids(self) -> List[str]:
        ids: List[str] = []
        for r in self.routes.values():
            ids.extend(req.id for req in r.stops)
        return ids
