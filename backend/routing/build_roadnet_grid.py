"""
离线快速生成“完整路网”用于算法演示/联调：规则网格图（几千节点秒级生成）。

输出格式与现有 A* 完全兼容：
- backend/data/road_nodes.json   (list[{"name","lng","lat","node_type"}])
- backend/data/road_graph.json   ({"description","edges":[{"from","to","distance_km","time_minutes","is_highway"}]})

用法（在 backend 目录）：
  python -m routing.build_roadnet_grid --bbox 39.85 39.98 116.25 116.48 --nx 70 --ny 70 --out-dir data
"""

from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, List, Tuple


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        required=True,
        metavar=("SOUTH", "NORTH", "WEST", "EAST"),
        help="边界框：south north west east（WGS84 经纬度）",
    )
    p.add_argument("--nx", type=int, default=60, help="经度方向网格数（列数）")
    p.add_argument("--ny", type=int, default=60, help="纬度方向网格数（行数）")
    p.add_argument("--out-dir", type=str, default="data", help="输出目录（相对 backend 目录）")
    p.add_argument("--speed-kmh", type=float, default=40.0, help="用于估算 time_minutes 的平均速度")
    return p.parse_args()


def _ensure_out_dir(out_dir: str) -> str:
    out_dir_abs = os.path.abspath(out_dir)
    os.makedirs(out_dir_abs, exist_ok=True)
    return out_dir_abs


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    r = 6371.0
    lon1, la1 = math.radians(lng1), math.radians(lat1)
    lon2, la2 = math.radians(lng2), math.radians(lat2)
    dlon = lon2 - lon1
    dlat = la2 - la1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def build_grid(
    *,
    bbox: Tuple[float, float, float, float],
    nx: int,
    ny: int,
    out_dir: str,
    speed_kmh: float,
) -> Dict[str, str]:
    south, north, west, east = bbox
    if nx < 2 or ny < 2:
        raise ValueError("nx/ny 至少为 2")
    if not (south < north and west < east):
        raise ValueError("bbox 参数不合法：需要 south<north 且 west<east")

    dx = (east - west) / (nx - 1)
    dy = (north - south) / (ny - 1)

    nodes: List[Dict] = []
    # index = y*nx + x
    for y in range(ny):
        lat = south + y * dy
        for x in range(nx):
            lng = west + x * dx
            nodes.append(
                {
                    "name": f"g_{x}_{y}",
                    "lng": round(lng, 7),
                    "lat": round(lat, 7),
                    "node_type": "grid",
                }
            )

    edges: List[Dict] = []
    def add_edge(i: int, j: int, is_highway: bool) -> None:
        n1 = nodes[i]
        n2 = nodes[j]
        dist_km = _haversine_km(float(n1["lng"]), float(n1["lat"]), float(n2["lng"]), float(n2["lat"]))
        time_minutes = (dist_km / max(1e-6, speed_kmh)) * 60.0
        edges.append(
            {
                "from": i,
                "to": j,
                "distance_km": round(dist_km, 6),
                "time_minutes": round(time_minutes, 3),
                "is_highway": bool(is_highway),
            }
        )

    # 连接相邻点（双向）。每隔 5 行/列设置“主干道”用于 is_highway 示例
    for y in range(ny):
        for x in range(nx):
            i = y * nx + x
            if x + 1 < nx:
                j = y * nx + (x + 1)
                highway = (y % 5 == 0)
                add_edge(i, j, highway)
                add_edge(j, i, highway)
            if y + 1 < ny:
                j = (y + 1) * nx + x
                highway = (x % 5 == 0)
                add_edge(i, j, highway)
                add_edge(j, i, highway)

    out_dir_abs = _ensure_out_dir(out_dir)
    nodes_path = os.path.join(out_dir_abs, "road_nodes.json")
    graph_path = os.path.join(out_dir_abs, "road_graph.json")

    with open(nodes_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "description": f"grid road network bbox={bbox} nx={nx} ny={ny}",
                "edges": edges,
                "note": f"nodes={len(nodes)} edges={len(edges)}",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return {
        "nodes_path": nodes_path,
        "graph_path": graph_path,
        "nodes": str(len(nodes)),
        "edges": str(len(edges)),
    }


def main() -> None:
    args = _parse_args()
    result = build_grid(
        bbox=tuple(args.bbox),
        nx=int(args.nx),
        ny=int(args.ny),
        out_dir=args.out_dir,
        speed_kmh=float(args.speed_kmh),
    )
    print(
        f"已生成路网：nodes={result['nodes']} edges={result['edges']}\n"
        f"- road_nodes: {result['nodes_path']}\n"
        f"- road_graph: {result['graph_path']}"
    )


if __name__ == "__main__":
    main()

