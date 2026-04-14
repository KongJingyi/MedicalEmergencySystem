"""
从 OSM roads shapefile 构建路网（真实道路），导出为项目现有 A* 可用格式。

输入：
- 例如：beijing/beijing-251105-free.shp/gis_osm_roads_free_1.shp

输出：
- data/road_nodes.json
- data/road_graph.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--shp", required=True, type=str, help="roads shapefile 路径")
    p.add_argument("--out-dir", default="data", type=str, help="输出目录")
    p.add_argument("--target-nodes", default=1500, type=int, help="目标节点数（约）")
    p.add_argument("--precision", default=6, type=int, help="坐标量化精度（小数位）")
    return p.parse_args()


def _quantize(lng: float, lat: float, precision: int) -> Tuple[float, float]:
    return (round(float(lng), precision), round(float(lat), precision))


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    r = 6371.0
    lon1, la1 = math.radians(lng1), math.radians(lat1)
    lon2, la2 = math.radians(lng2), math.radians(lat2)
    dlon = lon2 - lon1
    dlat = la2 - la1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _estimate_speed_kmh(fclass: Optional[str]) -> float:
    if not fclass:
        return 35.0
    v = fclass.lower()
    if v in {"motorway", "motorway_link", "trunk", "trunk_link"}:
        return 75.0
    if v in {"primary", "primary_link"}:
        return 60.0
    if v in {"secondary", "secondary_link"}:
        return 50.0
    if v in {"tertiary", "tertiary_link"}:
        return 40.0
    return 30.0


def _is_highway(fclass: Optional[str]) -> bool:
    if not fclass:
        return False
    v = fclass.lower()
    return v in {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"}


def _iter_lines(geom):
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, LineString):
        yield geom
    elif isinstance(geom, MultiLineString):
        for line in geom.geoms:
            yield line


def build_from_shp(shp_path: str, out_dir: str, target_nodes: int, precision: int) -> Dict[str, int]:
    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise RuntimeError("shapefile 为空，无法构建路网。")

    # 统一到 WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    elif str(gdf.crs).lower() not in {"epsg:4326", "wgs 84"}:
        gdf = gdf.to_crs("EPSG:4326")

    coord_to_id: Dict[Tuple[float, float], int] = {}
    id_to_coord: List[Tuple[float, float]] = []
    adjacency: Dict[int, set] = defaultdict(set)
    edge_attrs: Dict[Tuple[int, int], Dict] = {}

    def get_node_id(lng: float, lat: float) -> int:
        key = _quantize(lng, lat, precision)
        if key in coord_to_id:
            return coord_to_id[key]
        nid = len(id_to_coord)
        coord_to_id[key] = nid
        id_to_coord.append(key)
        return nid

    has_fclass = "fclass" in gdf.columns

    for row in gdf.itertuples(index=False):
        geom = getattr(row, "geometry", None)
        fclass = getattr(row, "fclass", None) if has_fclass else None
        speed_kmh = _estimate_speed_kmh(fclass)
        is_hw = _is_highway(fclass)

        for line in _iter_lines(geom):
            coords = list(line.coords)
            if len(coords) < 2:
                continue
            for i in range(1, len(coords)):
                lng1, lat1 = coords[i - 1][0], coords[i - 1][1]
                lng2, lat2 = coords[i][0], coords[i][1]
                u = get_node_id(lng1, lat1)
                v = get_node_id(lng2, lat2)
                if u == v:
                    continue

                dist_km = _haversine_km(id_to_coord[u][0], id_to_coord[u][1], id_to_coord[v][0], id_to_coord[v][1])
                time_minutes = (dist_km / max(1e-6, speed_kmh)) * 60.0

                # 双向边（roads shp 通常不含严格方向信息）
                adjacency[u].add(v)
                adjacency[v].add(u)
                edge_attrs[(u, v)] = {
                    "distance_km": round(dist_km, 6),
                    "time_minutes": round(time_minutes, 3),
                    "is_highway": is_hw,
                }
                edge_attrs[(v, u)] = {
                    "distance_km": round(dist_km, 6),
                    "time_minutes": round(time_minutes, 3),
                    "is_highway": is_hw,
                }

    if not id_to_coord:
        raise RuntimeError("未解析到任何有效道路节点。")

    # 找最大连通子图
    unvisited = set(range(len(id_to_coord)))
    components: List[List[int]] = []
    while unvisited:
        start = next(iter(unvisited))
        q = deque([start])
        comp = []
        unvisited.remove(start)
        while q:
            x = q.popleft()
            comp.append(x)
            for nb in adjacency.get(x, []):
                if nb in unvisited:
                    unvisited.remove(nb)
                    q.append(nb)
        components.append(comp)
    largest = max(components, key=len)

    # 按目标节点数截取（BFS 保证子图尽量连通）
    if target_nodes > 0 and len(largest) > target_nodes:
        deg = {n: len(adjacency.get(n, [])) for n in largest}
        start = max(largest, key=lambda n: deg[n])
        selected = set()
        q = deque([start])
        while q and len(selected) < target_nodes:
            x = q.popleft()
            if x in selected:
                continue
            selected.add(x)
            for nb in adjacency.get(x, []):
                if nb in largest and nb not in selected:
                    q.append(nb)
        chosen = list(selected)
    else:
        chosen = largest

    chosen_set = set(chosen)
    old_to_new: Dict[int, int] = {}
    nodes_out: List[Dict] = []
    for old_id in chosen:
        new_id = len(nodes_out)
        old_to_new[old_id] = new_id
        lng, lat = id_to_coord[old_id]
        nodes_out.append(
            {"name": f"bj_{new_id}", "lng": lng, "lat": lat, "node_type": "osm_road"}
        )

    edges_out: List[Dict] = []
    for u in chosen:
        for v in adjacency.get(u, []):
            if v not in chosen_set:
                continue
            attrs = edge_attrs.get((u, v))
            if not attrs:
                continue
            edges_out.append(
                {
                    "from": old_to_new[u],
                    "to": old_to_new[v],
                    "distance_km": attrs["distance_km"],
                    "time_minutes": attrs["time_minutes"],
                    "is_highway": attrs["is_highway"],
                }
            )

    os.makedirs(out_dir, exist_ok=True)
    nodes_path = os.path.join(out_dir, "road_nodes.json")
    graph_path = os.path.join(out_dir, "road_graph.json")

    with open(nodes_path, "w", encoding="utf-8") as f:
        json.dump(nodes_out, f, ensure_ascii=False, indent=2)
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "description": "Real Beijing road network derived from OSM shapefile",
                "edges": edges_out,
                "note": f"nodes={len(nodes_out)}, edges={len(edges_out)}",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return {"nodes": len(nodes_out), "edges": len(edges_out)}


def main() -> None:
    args = _parse_args()
    result = build_from_shp(
        shp_path=args.shp,
        out_dir=args.out_dir,
        target_nodes=args.target_nodes,
        precision=args.precision,
    )
    print(f"done nodes={result['nodes']} edges={result['edges']}")


if __name__ == "__main__":
    main()

