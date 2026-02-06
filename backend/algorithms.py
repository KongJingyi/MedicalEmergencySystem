# backend/algorithms.py
import json
import math
import os
import random
from typing import Dict, List, Tuple


# ===============================
#  多因子决策评分（无人机 vs 救护车）
# ===============================

def calculate_medical_score(resource, route_type: str) -> Dict:
    """
    核心算法：根据【物资属性 + 运输方式 + 天气】计算【路径得分】

    Score = 速度评分 * 0.4 + 防震评分 * 0.3 - 天气恶劣系数 * 0.2
    """
    logs: List[str] = []

    # 1. 速度评分：无人机更快
    # 这里简单做成常数，后续可以接入真实 ETA
    if route_type == "DRONE":
        speed_score = 95
        logs.append("🕒 速度：无人机平均时效更快，基础速度评分 95")
    else:
        speed_score = 75
        logs.append("🕒 速度：地面救护车受路况影响，基础速度评分 75")

    # 2. 防震评分：看运输震动 vs 物资耐受度
    vehicle_shock = 8 if route_type == "DRONE" else 2
    # shock_sensitivity 越大越不怕震，这里做一个简单线性映射
    if vehicle_shock <= resource.shock_sensitivity:
        shock_score = 95
        logs.append(
            f"🛟 震动：运输震动({vehicle_shock}) ≤ 物资耐受度({resource.shock_sensitivity})，震动风险低，评分 95"
        )
    else:
        overload = vehicle_shock - resource.shock_sensitivity
        shock_score = max(40, 95 - overload * 10)
        logs.append(
            f"⚠️ 震动：运输震动({vehicle_shock}) 高于物资耐受度({resource.shock_sensitivity})，存在风险，评分 {shock_score}"
        )

    # 3. 天气恶劣系数：这里用随机数模拟，后续可接真实天气 API
    bad_weather = random.uniform(0, 100)  # 0=晴朗，100=极端恶劣
    logs.append(f"🌦 天气：模拟天气恶劣系数 {bad_weather:.1f}（0=晴朗，100=恶劣）")

    # 4. 紧急程度：越紧急越看重速度
    urgency_factor = 1.0 + (resource.urgency_level - 3) * 0.1  # Lv3 为基准，每级 ±10%
    effective_speed_score = speed_score * urgency_factor
    logs.append(
        f"🚨 紧急度：Lv{resource.urgency_level}，速度权重调整为 {urgency_factor:.2f} 倍，有效速度评分 {effective_speed_score:.1f}"
    )

    # 5. 最终综合评分
    score = (
        effective_speed_score * 0.4
        + shock_score * 0.3
        - bad_weather * 0.2
    )

    logs.append(
        f"📊 综合评分 = 速度({effective_speed_score:.1f})*0.4 + "
        f"防震({shock_score})*0.3 - 天气({bad_weather:.1f})*0.2 = {score:.1f}"
    )

    return {"score": score, "logs": logs}


# ===============================
#  路网 & 路径规划（Dijkstra）
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load_road_data() -> Tuple[List[Dict], List[Dict]]:
    """从 JSON 文件加载路网节点和边信息。"""
    nodes_path = os.path.join(DATA_DIR, "road_nodes.json")
    graph_path = os.path.join(DATA_DIR, "road_graph.json")

    with open(nodes_path, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    edges = graph.get("edges", [])
    return nodes, edges


def _build_adjacency(
    nodes: List[Dict], edges: List[Dict]
) -> Dict[int, List[Tuple[int, float]]]:
    """
    根据 edges 构建邻接表。
    返回: {from_index: [(to_index, weight), ...], ...}
    """
    adj: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(len(nodes))}
    for e in edges:
        u = int(e["from"])
        v = int(e["to"])
        # 如果边引用了不存在的节点索引（例如手动删减了 road_nodes.json）则直接跳过
        if u not in adj or v not in adj:
            continue
        # 这里暂时用距离做权重，后续可以换成 time_minutes
        w = float(e.get("distance_km") or 1.0)
        adj[u].append((v, w))
        adj[v].append((u, w))  # 假设双向道路
    return adj


def _dijkstra(
    start_idx: int, end_idx: int, adj: Dict[int, List[Tuple[int, float]]]
) -> List[int]:
    """简单 Dijkstra，返回节点索引路径。"""
    import heapq

    dist = {i: math.inf for i in adj.keys()}
    prev: Dict[int, int] = {}
    dist[start_idx] = 0.0

    heap: List[Tuple[float, int]] = [(0.0, start_idx)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        if u == end_idx:
            break
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    if end_idx not in prev and start_idx != end_idx:
        # 不连通，返回空路径
        return []

    # 回溯路径
    path = [end_idx]
    cur = end_idx
    while cur != start_idx:
        cur = prev[cur]
        path.append(cur)
    path.reverse()
    return path


def compute_route(start_name: str, end_name: str) -> List[Dict]:
    """
    对外暴露的路径规划函数：输入起终点名称，输出经纬度路径点数组。

    start_name / end_name 需要与 road_nodes.json 中的 name 对应，
    例如："西直门桥" -> "东直门桥"。
    """
    nodes, edges = _load_road_data()

    # 构造 name -> index 映射
    name_to_idx: Dict[str, int] = {n["name"]: idx for idx, n in enumerate(nodes)}

    if start_name not in name_to_idx or end_name not in name_to_idx:
        # 找不到名字时，直接返回空列表，交由上层处理
        return []

    start_idx = name_to_idx[start_name]
    end_idx = name_to_idx[end_name]

    adj = _build_adjacency(nodes, edges)
    idx_path = _dijkstra(start_idx, end_idx, adj)

    path_points: List[Dict] = []
    for idx in idx_path:
        node = nodes[idx]
        path_points.append(
            {
                "name": node["name"],
                "lng": node["lng"],
                "lat": node["lat"],
            }
        )

    return path_points