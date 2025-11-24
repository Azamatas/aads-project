from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Set
import heapq

from city.graph import CityGraph, NodeId


Path = List[NodeId]


def _reconstruct_path(
    came_from: Dict[NodeId, NodeId],
    start: NodeId,
    goal: NodeId,
) -> Path:
    cur = goal
    rev = [cur]
    while cur != start:
        cur = came_from[cur]
        rev.append(cur)
    rev.reverse()
    return rev


def astar_shortest_path(
    graph: CityGraph,
    start: NodeId,
    goal: NodeId,
) -> Tuple[Optional[Path], float]:
    """Классический A*: путь и детерминированное время по base_travel_time."""
    if start == goal:
        return [start], 0.0

    open_set: List[Tuple[float, NodeId]] = []
    heapq.heappush(open_set, (0.0, start))

    came_from: Dict[NodeId, NodeId] = {}
    g_score: Dict[NodeId, float] = {start: 0.0}
    closed: Set[NodeId] = set()

    while open_set:
        _, current = heapq.heappop(open_set)
        if current in closed:
            continue
        if current == goal:
            return _reconstruct_path(came_from, start, goal), g_score[current]

        closed.add(current)

        for edge in graph.neighbors(current):
            neighbor = edge.dst
            tentative_g = g_score[current] + edge.base_travel_time
            if neighbor in g_score and tentative_g >= g_score[neighbor]:
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score = tentative_g + graph.heuristic_time(neighbor, goal)
            heapq.heappush(open_set, (f_score, neighbor))

    return None, float("inf")
