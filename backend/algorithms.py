import json
import math
import os
import random
from typing import Dict, List, Tuple


# ===============================
#  业务规则常量（风险阈值 & 天气）
# ===============================

# 电量安全下限（%）
MIN_BATTERY_SAFE = 20.0
# 假定无人机抗风极限（当前仅为示意）
MAX_DRONE_WIND = 6
# 温度敏感物资关键字
TEMP_SENSITIVE_ITEMS = ["血浆", "疫苗"]

# 全局当前天气状态（由 /api/weather/set 更新）
CURRENT_WEATHER: str = "sunny"


def set_weather(weather: str) -> None:
    """
    更新当前天气（后端全局）。
    允许值：sunny / rain / snow / fog
    """
    global CURRENT_WEATHER
    if weather in {"sunny", "rain", "snow", "fog"}:
        CURRENT_WEATHER = weather


def get_weather() -> str:
    return CURRENT_WEATHER


def get_speed_kmh(route_type: str) -> float:
    """
    根据运输方式 + 当前天气，给出用于 ETA 的平均速度（km/h）。
    """
    weather = get_weather()

    if route_type == "DRONE":
        base = 120.0
        if weather == "fog":
            base *= 0.7  # 大雾降速
        # 大雪时我们主要通过评分一票否决，速度仍保持以便做 ETA 估算
        return base

    # AMBULANCE
    base = 60.0
    if weather == "rain":
        base *= 0.8  # 雨天路滑
    elif weather == "snow":
        base *= 0.5  # 大雪严重减速
    return base


# ===============================
#  多因子决策评分（无人机 vs 救护车）
# ===============================

def calculate_medical_score(resource, route_type: str) -> Dict:
    """
    核心算法：根据【物资属性 + 运输方式 + 天气】计算【路径得分】

    Score = 速度评分 * 0.4 + 防震评分 * 0.3 - 天气恶劣系数 * 0.2
    """
    logs: List[str] = []

    # 1. 速度评分：无人机更快（基础分）
    if route_type == "DRONE":
        speed_score = 95
        logs.append("🕒 速度：无人机平均时效更快，基础速度评分 95")
    else:
        speed_score = 75
        logs.append("🕒 速度：地面救护车受路况影响，基础速度评分 75")

    # 1.1 天气对速度/安全的影响（基于 CURRENT_WEATHER）
    weather = get_weather()
    if route_type == "DRONE":
        if weather == "rain":
            speed_score -= 20
            logs.append("🌧 雨天：无人机受降水和风切变影响，速度评分 -20")
        elif weather == "snow":
            # 大雪禁飞：一票否决
            speed_score = 0
            logs.append("❄ 大雪：当前策略为无人机禁飞，速度评分直接降为 0")
        elif weather == "fog":
            speed_score *= 0.7
            logs.append("🌫 大雾：能见度下降，无人机速度评分降至 70%")
    else:
        if weather == "rain":
            speed_score *= 0.8
            logs.append("🌧 雨天：路面湿滑，地面救护车速度评分降至 80%")
        elif weather == "snow":
            speed_score *= 0.5
            logs.append("❄ 大雪：道路阻塞严重，救护车速度评分降至 50%")

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

    # 返回时额外带上天气恶劣系数，后续用于风险评估
    return {"score": score, "logs": logs, "bad_weather": bad_weather}


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


# ===============================
#  路径风险评估（电量 / 温控 等）
# ===============================

def evaluate_risks(
    resource, route_type: str, distance_km: float, bad_weather: float
) -> List[Dict]:
    """
    根据路径长度、物资属性和天气，给出风险告警列表。
    """
    warnings: List[Dict] = []

    if distance_km <= 0:
        return warnings

    # 粗略 ETA 估算（考虑天气后的速度）
    speed_kmh = get_speed_kmh(route_type)
    eta_hours = distance_km / speed_kmh if speed_kmh > 0 else 0.0
    eta_minutes = eta_hours * 60.0

    # 规则 1：无人机续航检查（到达时预期电量是否低于安全阈值）
    if route_type == "DRONE":
        # 假设每公里约耗电 2%（与前端机队状态模型保持大致一致）
        consumption_per_km = 2.0
        estimated_battery = max(0.0, 100.0 - distance_km * consumption_per_km)
        if estimated_battery < MIN_BATTERY_SAFE:
            warnings.append(
                {
                    "code": "BATTERY_RISK",
                    "msg": "无人机预期电量将低于20%，极度危险！",
                    "level": "CRITICAL",
                }
            )

        # 示例：极端恶劣天气下的附加告警（如果 bad_weather 非常大）
        if bad_weather >= 80.0:
            warnings.append(
                {
                    "code": "WEATHER_RISK",
                    "msg": "当前天气条件对无人机飞行极不利，存在失联风险。",
                    "level": "WARNING",
                }
            )

    # 规则 2：冷链超时检查（极寒疫苗/血浆）
    # 简单根据名称或类别中是否包含敏感关键字来判断
    name = getattr(resource, "name", "") or ""
    category = getattr(resource, "category", "") or ""
    is_temp_sensitive = any(key in name for key in TEMP_SENSITIVE_ITEMS) or any(
        key in category for key in TEMP_SENSITIVE_ITEMS
    )

    if is_temp_sensitive:
        # 假定保温箱极限时长 60 分钟
        max_cold_chain_minutes = 60.0
        if eta_minutes > max_cold_chain_minutes:
            warnings.append(
                {
                    "code": "TEMP_RISK",
                    "msg": "冷链预计运输时间超过安全时限，存在温控失效风险。",
                    "level": "CRITICAL",
                }
            )

    return warnings