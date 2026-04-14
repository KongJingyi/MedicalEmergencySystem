import heapq
import math
from typing import Dict, List, Optional

try:
    # 作为包导入：python -m routing.path_astar
    from .graph_builder import TrafficGraph  # type: ignore
except Exception:
    # 作为脚本/动态加载导入：兼容现有 importlib 加载方式
    from graph_builder import TrafficGraph  # type: ignore


def haversine_distance(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    lon1, la1 = math.radians(lng1), math.radians(lat1)
    lon2, la2 = math.radians(lng2), math.radians(lat2)
    dlon = lon2 - lon1
    dlat = la2 - la1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371.0 * c


def reconstruct_path(came_from: Dict[int, int], current: int) -> List[int]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def a_star_search(
    graph: TrafficGraph,
    start_idx: int,
    end_idx: int,
    weather: str = "sunny",
    traffic: str = "green",
) -> List[int]:
    open_set: List[tuple] = []
    heapq.heappush(open_set, (0.0, 0.0, start_idx))

    came_from: Dict[int, int] = {}
    g_score: Dict[int, float] = {i: float("inf") for i in range(len(graph.nodes))}
    g_score[start_idx] = 0.0

    while open_set:
        _, current_g, current = heapq.heappop(open_set)
        if current == end_idx:
            return reconstruct_path(came_from, current)
        if current_g > g_score[current]:
            continue

        for neighbor, _ in graph.get_neighbors(current, weather=weather, traffic_level=traffic):
            dynamic_cost = graph.get_dynamic_weight(current, neighbor, weather, traffic)
            tentative_g = current_g + dynamic_cost
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h_cost = haversine_distance(
                    float(graph.nodes[neighbor]["lng"]),
                    float(graph.nodes[neighbor]["lat"]),
                    float(graph.nodes[end_idx]["lng"]),
                    float(graph.nodes[end_idx]["lat"]),
                )
                f_score = tentative_g + h_cost
                heapq.heappush(open_set, (f_score, tentative_g, neighbor))
    return []


def compute_route_astar(
    start_name: str,
    end_name: str,
    nodes_file: str,
    edges_file: str,
    weather: str = "sunny",
    traffic: str = "green",
) -> List[Dict]:
    graph = TrafficGraph(nodes_file, edges_file)
    start_idx: Optional[int] = graph.find_node_index_by_name(start_name)
    end_idx: Optional[int] = graph.find_node_index_by_name(end_name)
    if start_idx is None or end_idx is None:
        return []

    idx_path = a_star_search(graph, start_idx, end_idx, weather=weather, traffic=traffic)
    result: List[Dict] = []
    for idx in idx_path:
        n = graph.nodes[idx]
        result.append({"name": n["name"], "lng": n["lng"], "lat": n["lat"]})
    return result
