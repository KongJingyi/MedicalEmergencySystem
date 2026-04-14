import json
import math
from typing import Dict, List, Optional, Tuple


class TrafficGraph:
    WEATHER_FACTORS: Dict[str, float] = {
        "sunny": 1.0,
        "rain": 1.5,
        "snow": 3.0,
        "fog": 1.2,
    }

    TRAFFIC_FACTORS: Dict[str, float] = {
        "green": 1.0,
        "yellow": 1.3,
        "red": 2.5,
    }

    def __init__(self, nodes_file: str, edges_file: str):
        self.nodes = self._load_json(nodes_file)
        raw_edges = self._load_json(edges_file)
        self.edges = raw_edges.get("edges", [])
        self.adj_list: Dict[int, List[Tuple[int, float, bool]]] = {}
        self._base_dist_map: Dict[Tuple[int, int], float] = {}
        self._build_base_graph()

    def _load_json(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_base_graph(self):
        node_count = len(self.nodes)
        self.adj_list = {i: [] for i in range(node_count)}
        self._base_dist_map = {}

        for edge in self.edges:
            u = int(edge["from"])
            v = int(edge["to"])
            if u < 0 or v < 0 or u >= node_count or v >= node_count:
                continue

            base_distance = float(edge.get("distance_km", 1.0))
            is_highway = bool(edge.get("is_highway", base_distance >= 2.0))
            self.adj_list[u].append((v, base_distance, is_highway))
            self._base_dist_map[(u, v)] = base_distance

    def _get_base_distance(self, u: int, v: int) -> float:
        if (u, v) not in self._base_dist_map:
            raise ValueError(f"Edge not found: {u} -> {v}")
        return self._base_dist_map[(u, v)]

    def get_dynamic_weight(
        self,
        u: int,
        v: int,
        weather: str = "sunny",
        traffic_level: str = "green",
    ) -> float:
        """计算两点之间的动态权重"""
        base_dist = self._get_base_distance(u, v)
        weight = base_dist

        # 获取节点属性
        node_u = self.nodes[u]
        node_v = self.nodes[v]

        # 🌟 核心：高速公路畅通无阻，权重降低
        if node_u.get("node_type") == "高速" or node_v.get("node_type") == "高速":
            weight *= 0.5  # 模拟 120km/h 的高时效

        # 🌟 核心：收费站进城拦截！如果遇到城内拥堵，收费站就像个大闸
        if node_v.get("node_type") == "收费站" and traffic_level in ["yellow", "red"]:
            weight += 10.0  # 强行增加 10 公里的拥堵阻力代价！

        # 保留天气/交通整体惩罚
        weather_factor = self.WEATHER_FACTORS.get(weather, 1.0)
        traffic_factor = self.TRAFFIC_FACTORS.get(traffic_level, 1.0)
        weight *= weather_factor
        weight *= traffic_factor
        return max(weight, 0.001)

    def get_neighbors(
        self,
        node_idx: int,
        weather: str = "sunny",
        traffic_level: str = "green",
    ) -> List[Tuple[int, float]]:
        result: List[Tuple[int, float]] = []
        for target_idx, _base_dist, _is_highway in self.adj_list.get(node_idx, []):
            result.append(
                (
                    target_idx,
                    self.get_dynamic_weight(node_idx, target_idx, weather, traffic_level),
                )
            )
        return result

    def find_node_index_by_name(self, name: str) -> Optional[int]:
        for idx, node in enumerate(self.nodes):
            if node.get("name") == name:
                return idx
        return None

    def haversine_km(self, i: int, j: int) -> float:
        n1 = self.nodes[i]
        n2 = self.nodes[j]
        lon1, lat1 = math.radians(float(n1["lng"])), math.radians(float(n1["lat"]))
        lon2, lat2 = math.radians(float(n2["lng"])), math.radians(float(n2["lat"]))
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return 6371.0 * c
