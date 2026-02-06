"""
根据 road_nodes.json 中的真实经纬度，自动计算 road_graph.json 里每条边的 distance_km。

用法（在 backend 目录下执行）::

    python update_road_graph_distances.py

更新逻辑：
- 对于每条 edge:
    - 如果 from/to 索引在 road_nodes.json 的范围内，则用 Haversine 公式计算两点间直线距离 (km)
    - 将 distance_km 更新为计算值（保留 3 位小数）
    - time_minutes 暂时保留原值（你也可以按需要在这里基于速度估算）
"""

import json
import math
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """Haversine 公式计算两点间球面距离（单位：公里）。"""
    # 地球半径（km）
    R = 6371.0

    lon1, lat1_r = math.radians(lng1), math.radians(lat1)
    lon2, lat2_r = math.radians(lng2), math.radians(lat2)

    dlon = lon2 - lon1
    dlat = lat2_r - lat1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(
        dlon / 2
    ) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def main() -> None:
    nodes_path = DATA_DIR / "road_nodes.json"
    graph_path = DATA_DIR / "road_graph.json"

    with nodes_path.open("r", encoding="utf-8") as f:
        nodes: List[Dict] = json.load(f)

    with graph_path.open("r", encoding="utf-8") as f:
        graph = json.load(f)

    edges = graph.get("edges", [])

    updated = 0
    skipped = 0

    for e in edges:
        u = int(e["from"])
        v = int(e["to"])

        # 防止引用了不存在的节点索引
        if u < 0 or v < 0 or u >= len(nodes) or v >= len(nodes):
            skipped += 1
            continue

        n1 = nodes[u]
        n2 = nodes[v]

        dist_km = haversine_km(
            float(n1["lng"]),
            float(n1["lat"]),
            float(n2["lng"]),
            float(n2["lat"]),
        )

        e["distance_km"] = round(dist_km, 3)
        updated += 1

    graph["edges"] = edges

    with graph_path.open("w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"✅ 更新完成：{updated} 条边的 distance_km 已按真实坐标计算，跳过 {skipped} 条无效边。")


if __name__ == "__main__":
    main()

