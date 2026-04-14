"""
从 OpenStreetMap (OSM) 快速构建“可用于路径规划”的路网，并导出为：
- backend/data/road_nodes.json   (list[{"name","lng","lat","node_type"}])
- backend/data/road_graph.json   ({"description","edges":[{"from","to","distance_km","time_minutes","is_highway"}]})

目标：几千~几十万节点都可（取决于区域大小）。

用法示例（PowerShell，在 backend 目录下）：
  python -m routing.build_roadnet_osm --place "北京市, 中国" --network-type drive --out-dir data

或使用 bbox：
  python -m routing.build_roadnet_osm --bbox 39.85 39.98 116.25 116.48 --network-type drive --out-dir data
"""

from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, Iterable, List, Optional, Tuple

import requests


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--place", type=str, help="OSM 地名查询，例如：北京市, 中国")
    g.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("SOUTH", "NORTH", "WEST", "EAST"),
        help="边界框：south north west east（WGS84 经纬度）",
    )

    p.add_argument(
        "--network-type",
        type=str,
        default="drive",
        choices=["drive", "drive_service", "walk", "bike", "all"],
        help="路网类型（越开放节点越多）",
    )
    p.add_argument(
        "--simplify",
        action="store_true",
        default=True,
        help="简化拓扑（推荐开启，去除冗余形状点）",
    )
    p.add_argument(
        "--no-simplify",
        action="store_false",
        dest="simplify",
        help="关闭简化拓扑（会产生更多节点）",
    )
    p.add_argument(
        "--out-dir",
        type=str,
        default="data",
        help="输出目录（相对 backend 目录）",
    )
    p.add_argument(
        "--min-nodes",
        type=int,
        default=2000,
        help="节点数低于该值则报错（避免取区太小）",
    )
    p.add_argument(
        "--target-nodes",
        type=int,
        default=0,
        help="目标节点数（>0 时会在真实路网中截取约该数量节点）",
    )
    return p.parse_args()


def _ensure_out_dir(out_dir: str) -> str:
    out_dir_abs = os.path.abspath(out_dir)
    os.makedirs(out_dir_abs, exist_ok=True)
    return out_dir_abs


def _km_from_m(m: float) -> float:
    return float(m) / 1000.0


def _estimate_speed_kmh(highway: Optional[str]) -> float:
    """
    非严格估算，用于填充 time_minutes（你们现有算法主要吃 distance_km）。
    """
    if not highway:
        return 40.0

    hw = highway if isinstance(highway, str) else str(highway)
    hw = hw.lower()
    if hw in {"motorway", "motorway_link"}:
        return 90.0
    if hw in {"trunk", "trunk_link"}:
        return 70.0
    if hw in {"primary", "primary_link"}:
        return 60.0
    if hw in {"secondary", "secondary_link"}:
        return 50.0
    if hw in {"tertiary", "tertiary_link"}:
        return 45.0
    if hw in {"residential", "unclassified", "living_street"}:
        return 30.0
    return 40.0


def _is_highway(highway: Optional[str]) -> bool:
    if not highway:
        return False
    hw = highway if isinstance(highway, str) else str(highway)
    hw = hw.lower()
    return hw in {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"}


def _safe_first(value):
    # osmnx/networkx 的边属性有时是 list（多个 OSM way 叠加），取第一个即可
    if isinstance(value, list) and value:
        return value[0]
    return value


def build_and_export(
    *,
    place: Optional[str],
    bbox: Optional[Tuple[float, float, float, float]],
    network_type: str,
    simplify: bool,
    out_dir: str,
    min_nodes: int,
    target_nodes: int = 0,
) -> Dict[str, str]:
    try:
        import osmnx as ox  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "缺少依赖 osmnx。请先在 backend 目录执行：pip install -r requirements.txt"
        ) from e

    # 让 osmnx 使用缓存，避免反复拉取
    ox.settings.use_cache = True
    ox.settings.log_console = False
    # Windows/校园网/公共 Overpass 容易慢：给足超时
    ox.settings.requests_timeout = 180

    # 选择一个可用的 Overpass 端点（不同网络环境下可用性差异很大）
    candidates = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.nchc.org.tw/api/interpreter",
    ]
    selected = None
    for url in candidates:
        try:
            r = requests.get(url, params={"data": "[out:json];node(0);out;"}, timeout=8)
            if r.status_code == 200:
                selected = url
                break
        except Exception:
            continue
    if selected:
        try:
            ox.settings.overpass_url = selected
        except Exception:
            pass

    if place:
        print(
            f"正在从 OSM 拉取路网（place={place}, type={network_type}, simplify={simplify}，overpass={selected or 'default'}）...",
            flush=True,
        )
        G = ox.graph_from_place(place, network_type=network_type, simplify=simplify)
        desc = f"OSM road network from place={place}, type={network_type}, simplify={simplify}"
    else:
        assert bbox is not None
        south, north, west, east = bbox
        print(
            f"正在从 OSM 拉取路网（bbox={bbox}, type={network_type}, simplify={simplify}，overpass={selected or 'default'}）...\n"
            "如果这里等待较久，通常是 Overpass 限流/网络较慢；可换小 bbox 或稍后重试。",
            flush=True,
        )
        # osmnx 2.x: graph_from_bbox(bbox=...) 使用关键字参数传入元组
        G = ox.graph_from_bbox(
            bbox=(north, south, east, west),
            network_type=network_type,
            simplify=simplify,
        )
        desc = f"OSM road network from bbox={bbox}, type={network_type}, simplify={simplify}"

    # 统一为有向图（osmnx 默认就是 MultiDiGraph）
    try:
        import networkx as nx  # type: ignore
    except Exception as e:
        raise RuntimeError("缺少依赖 networkx（通常随 osmnx 安装）。") from e

    if not isinstance(G, nx.MultiDiGraph):
        G = nx.MultiDiGraph(G)

    node_ids: List[int] = list(G.nodes())
    print(f"已获取原始图：nodes={len(node_ids)} edges={len(G.edges())}", flush=True)
    if len(node_ids) < min_nodes:
        raise RuntimeError(f"生成路网节点数过少：{len(node_ids)}（min_nodes={min_nodes}）。请扩大 place/bbox。")

    # 可选：从真实路网中截取约 target_nodes 节点，保证仍是“真实道路拓扑”的子图
    if target_nodes and target_nodes > 0 and len(node_ids) > target_nodes:
        wccs = list(nx.weakly_connected_components(G))
        largest = max(wccs, key=len)
        H = G.subgraph(largest).copy()
        # 从高连通节点开始 BFS，取连续子图，尽量保证可达性
        start_node = max(H.degree, key=lambda t: t[1])[0]
        visited = set()
        queue = [start_node]
        while queue and len(visited) < target_nodes:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            for nb in H.successors(cur):
                if nb not in visited:
                    queue.append(nb)
            for nb in H.predecessors(cur):
                if nb not in visited:
                    queue.append(nb)
        selected = list(visited)
        G = H.subgraph(selected).copy()
        node_ids = list(G.nodes())
        print(f"已截取子图：nodes={len(node_ids)} edges={len(G.edges())}", flush=True)

    # node_id -> index（你们的 A* 使用数组下标做节点 id）
    id_to_idx: Dict[int, int] = {nid: i for i, nid in enumerate(node_ids)}

    nodes_out: List[Dict] = []
    for nid in node_ids:
        data = G.nodes[nid]
        lng = float(data.get("x"))
        lat = float(data.get("y"))
        nodes_out.append(
            {
                "name": str(nid),  # 关键：保证唯一且可查找
                "lng": lng,
                "lat": lat,
                "node_type": "osm_node",
            }
        )

    edges_out: List[Dict] = []
    # MultiDiGraph: (u, v, key, data)
    edge_total = G.number_of_edges()
    edge_i = 0
    for u, v, _k, data in G.edges(keys=True, data=True):
        edge_i += 1
        if u not in id_to_idx or v not in id_to_idx:
            continue
        length_m = _safe_first(data.get("length", None))
        if length_m is None:
            # 兜底：没有 length 时，用欧式近似（很少见）
            ux, uy = float(G.nodes[u]["x"]), float(G.nodes[u]["y"])
            vx, vy = float(G.nodes[v]["x"]), float(G.nodes[v]["y"])
            length_m = math.hypot(ux - vx, uy - vy) * 111_000.0

        highway = _safe_first(data.get("highway", None))
        speed_kmh = _estimate_speed_kmh(highway if isinstance(highway, str) else None)
        dist_km = _km_from_m(float(length_m))
        time_minutes = (dist_km / max(1e-6, speed_kmh)) * 60.0

        edges_out.append(
            {
                "from": id_to_idx[int(u)],
                "to": id_to_idx[int(v)],
                "distance_km": round(dist_km, 6),
                "time_minutes": round(time_minutes, 3),
                "is_highway": _is_highway(highway if isinstance(highway, str) else None),
            }
        )
        if edge_i % 20000 == 0:
            print(f"正在导出边：{edge_i}/{edge_total}", flush=True)

    out_dir_abs = _ensure_out_dir(out_dir)
    nodes_path = os.path.join(out_dir_abs, "road_nodes.json")
    graph_path = os.path.join(out_dir_abs, "road_graph.json")

    with open(nodes_path, "w", encoding="utf-8") as f:
        json.dump(nodes_out, f, ensure_ascii=False, indent=2)

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "description": desc,
                "edges": edges_out,
                "note": f"nodes={len(nodes_out)}, edges={len(edges_out)}",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return {"nodes_path": nodes_path, "graph_path": graph_path, "nodes": str(len(nodes_out)), "edges": str(len(edges_out))}


def main() -> None:
    args = _parse_args()
    bbox = tuple(args.bbox) if args.bbox else None

    result = build_and_export(
        place=args.place,
        bbox=bbox,  # type: ignore[arg-type]
        network_type=args.network_type,
        simplify=bool(args.simplify),
        out_dir=args.out_dir,
        min_nodes=int(args.min_nodes),
        target_nodes=int(args.target_nodes),
    )
    print(
        f"✅ 已生成路网：nodes={result['nodes']} edges={result['edges']}\n"
        f"- road_nodes: {result['nodes_path']}\n"
        f"- road_graph: {result['graph_path']}"
    )


if __name__ == "__main__":
    main()

