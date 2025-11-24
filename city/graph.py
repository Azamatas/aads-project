from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import math

NodeId = str


@dataclass
class Node:
    id: NodeId
    x: float
    y: float


@dataclass
class Edge:
    src: NodeId
    dst: NodeId
    length: float       # метры
    speed_limit: float  # м/с

    @property
    def base_travel_time(self) -> float:
        return self.length / self.speed_limit


class CityGraph:
    def __init__(self) -> None:
        self.nodes: Dict[NodeId, Node] = {}
        self.adj: Dict[NodeId, List[Edge]] = {}

    def add_node(self, node_id: NodeId, x: float, y: float) -> None:
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists")
        self.nodes[node_id] = Node(node_id, x, y)
        self.adj[node_id] = []

    def add_edge(
        self,
        src: NodeId,
        dst: NodeId,
        length: float,
        speed_limit: float,
        bidirectional: bool = False,
    ) -> None:
        if src not in self.nodes or dst not in self.nodes:
            raise ValueError("Both src and dst must be existing nodes")

        self.adj[src].append(
            Edge(src=src, dst=dst, length=length, speed_limit=speed_limit)
        )
        if bidirectional:
            self.adj[dst].append(
                Edge(src=dst, dst=src, length=length, speed_limit=speed_limit)
            )

    def neighbors(self, node_id: NodeId) -> List[Edge]:
        return self.adj.get(node_id, [])

    def max_speed_limit(self) -> float:
        max_speed = 1.0
        for edges in self.adj.values():
            for e in edges:
                max_speed = max(max_speed, e.speed_limit)
        return max_speed

    def heuristic_time(self, a: NodeId, b: NodeId) -> float:
        """Эвристика для A*: евклид / max_speed."""
        na = self.nodes[a]
        nb = self.nodes[b]
        dx = na.x - nb.x
        dy = na.y - nb.y
        dist = math.hypot(dx, dy)
        return dist / self.max_speed_limit()
