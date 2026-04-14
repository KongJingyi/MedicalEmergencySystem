from fastapi import APIRouter, Depends
from sqlmodel import Session, SQLModel, select
from typing import Dict, List, Optional
import json
import math
import os
import sys
import time
import importlib.util
import requests  # 🌟 新增：用于调用高德API

# --- 🌟 新增：中国地图坐标系纠偏算法 (GCJ-02 to WGS-84) ---
# 定义椭球体参数
a = 6378245.0
ee = 0.00669342162296594323


def _transformlat(lng, lat):
    ret = (
        -100.0
        + 2.0 * lng
        + 3.0 * lat
        + 0.2 * lat * lat
        + 0.1 * lng * lat
        + 0.2 * math.sqrt(abs(lng))
    )
    ret += (
        (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi))
        * 2.0
        / 3.0
    )
    ret += (
        (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi))
        * 2.0
        / 3.0
    )
    ret += (
        (160.0 * math.sin(lat / 12.0 * math.pi) + 320 * math.sin(lat * math.pi / 30.0))
        * 2.0
        / 3.0
    )
    return ret


def _transformlng(lng, lat):
    ret = (
        300.0
        + lng
        + 2.0 * lat
        + 0.1 * lng * lng
        + 0.1 * lng * lat
        + 0.1 * math.sqrt(abs(lng))
    )
    ret += (
        (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi))
        * 2.0
        / 3.0
    )
    ret += (
        (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi))
        * 2.0
        / 3.0
    )
    ret += (
        (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi))
        * 2.0
        / 3.0
    )
    return ret


def gcj02_to_wgs84(lng, lat):
    """
    🌟 核心功能：将高德 GCJ-02 坐标转换为标准 Cesium WGS-84 坐标
    """
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    mglat = lat + dlat
    mglng = lng + dlng
    # 精确计算标准 WGS-84 坐标
    return lng * 2 - mglng, lat * 2 - mglat

from database import get_session
from models import MedicalResource, RouteRequest, Hospital, DispatchTask, RiskEvent, DecisionLog
from algorithms import (
    calculate_medical_score,
    compute_route,
    evaluate_risks,
    get_speed_kmh,
)

router = APIRouter(prefix="/api", tags=["logistics"])

# 🔥【核心修改】地址映射表 (Location Mapping)
# 作用：把前端传来的“业务名称”翻译成算法能识别的“路网节点名称”
# 你需要打开 backend/data/road_nodes.json，找几个真实的节点名字填在右边
LOCATION_MAPPING = {
    # 前端传的名字 : 路网里的真实节点名字
    "调度中心": "西直门桥",
    "目标医院": "积水潭医院",

    # 前端起点（桥）名称映射：这些名字在 road_nodes.json 中真实存在
    "西直门桥": "西直门桥",
    "北展桥": "北展桥",
    "复兴门桥": "复兴门桥",
    "建国门桥": "建国门桥",
    "东直门桥": "东直门桥",

    # 医院名称映射：把“业务名称/别名”映射到 road_nodes.json 中真实存在的节点
    "北京积水潭医院": "积水潭医院",
    "积水潭医院": "积水潭医院",
    "北京大学人民医院": "北京大学人民医院",

    # 兼容测试
    "START": "西直门桥",
    "END": "东直门桥",
}

_ASTAR_MODULE = None


def _load_astar_module():
    global _ASTAR_MODULE
    if _ASTAR_MODULE is not None:
        return _ASTAR_MODULE

    module_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "routing", "path_astar.py")
    )
    module_dir = os.path.dirname(module_path)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location("path_astar_module", module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _ASTAR_MODULE = module
    return _ASTAR_MODULE


def _compute_route_astar(start_name: str, end_name: str) -> List[Dict]:
    """
    A* 路径规划（主路径）。如加载失败则回退旧算法。
    """
    astar_module = _load_astar_module()
    if not astar_module:
        return compute_route(start_name, end_name)

    weather = "sunny"
    try:
        from algorithms import get_weather
        weather = get_weather()
    except Exception:
        pass

    nodes_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "road_nodes.json"))
    edges_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "road_graph.json"))

    try:
        path = astar_module.compute_route_astar(
            start_name=start_name,
            end_name=end_name,
            nodes_file=nodes_file,
            edges_file=edges_file,
            weather=weather,
            traffic="green",
        )
        return path or []
    except Exception as e:
        print(f"⚠️ A* 路径规划失败，回退旧算法: {e}")
        return compute_route(start_name, end_name)


# ================================
#   医院名/坐标 -> 最近路网节点吸附
# ================================

_ROAD_NODES_CACHE: Optional[List[Dict]] = None
_VEHICLES_CACHE: Optional[List[Dict]] = None
_ROAD_NODE_BY_NAME_CACHE: Optional[Dict[str, Dict]] = None


def _load_road_nodes() -> List[Dict]:
    global _ROAD_NODES_CACHE
    if _ROAD_NODES_CACHE is not None:
        return _ROAD_NODES_CACHE
    try:
        with open("data/road_nodes.json", "r", encoding="utf-8") as f:
            _ROAD_NODES_CACHE = json.load(f)
    except Exception:
        _ROAD_NODES_CACHE = []
    return _ROAD_NODES_CACHE


def _load_road_node_by_name() -> Dict[str, Dict]:
    global _ROAD_NODE_BY_NAME_CACHE
    if _ROAD_NODE_BY_NAME_CACHE is not None:
        return _ROAD_NODE_BY_NAME_CACHE
    nodes = _load_road_nodes()
    _ROAD_NODE_BY_NAME_CACHE = {str(n.get("name")): n for n in nodes if n.get("name")}
    return _ROAD_NODE_BY_NAME_CACHE


def _load_vehicles() -> List[Dict]:
    global _VEHICLES_CACHE
    if _VEHICLES_CACHE is not None:
        return _VEHICLES_CACHE
    try:
        with open("data/vehicles.json", "r", encoding="utf-8") as f:
            _VEHICLES_CACHE = json.load(f)
    except Exception:
        _VEHICLES_CACHE = []
    return _VEHICLES_CACHE


def _get_vehicle_battery_start(vehicle_id: Optional[str]) -> float:
    if not vehicle_id:
        return 100.0
    vehicles = _load_vehicles()
    for v in vehicles:
        if v.get("id") == vehicle_id:
            try:
                return float(v.get("battery_start", 100.0))
            except Exception:
                return 100.0
    return 100.0


def _nearest_road_node_name(lng: float, lat: float) -> Optional[str]:
    nodes = _load_road_nodes()
    if not nodes:
        return None
    best_name = None
    best_d = float("inf")
    for n in nodes:
        d = _haversine_distance_m(lng, lat, float(n["lng"]), float(n["lat"]))
        if d < best_d:
            best_d = d
            best_name = n["name"]
    return best_name


def _parse_lng_lat_text(text: str) -> Optional[tuple]:
    """
    解析 "lng,lat" 字符串，成功则返回 (lng, lat)。
    """
    if not text or "," not in text:
        return None
    try:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 2:
            return None
        lng = float(parts[0])
        lat = float(parts[1])
        if not (-180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0):
            return None
        return (lng, lat)
    except Exception:
        return None


def _resolve_to_road_node(name: str, session: Session) -> str:
    """
    将传入的业务名称解析为 road_nodes.json 中存在的节点名：
    - 优先走 LOCATION_MAPPING
    - 再尝试把 name 当作医院名，从 Hospital 表查坐标并吸附最近路网节点
    - 最后返回原名（由 compute_route 决定是否可用）
    """
    node_map = _load_road_node_by_name()
    candidates: List[str] = []
    for c in [name, LOCATION_MAPPING.get(name, name)]:
        if c and c not in candidates:
            candidates.append(c)

    # 1) 传入的是坐标字符串 "lng,lat" -> 最近路网节点
    for c in candidates:
        lng_lat = _parse_lng_lat_text(c)
        if lng_lat:
            nearest = _nearest_road_node_name(lng_lat[0], lng_lat[1])
            if nearest:
                return nearest

    # 2) 传入值本身就是路网节点名（如 bj_123）
    for c in candidates:
        if c in node_map:
            return c

    # 3) 按医院名查坐标再吸附
    for c in candidates:
        hosp = session.exec(select(Hospital).where(Hospital.name == c)).first()
        if hosp:
            nearest = _nearest_road_node_name(hosp.lng, hosp.lat)
            if nearest:
                return nearest

    # 4) 保持兼容：让下游算法兜底
    return candidates[0] if candidates else name


# ================================
#   机队状态内存缓存 (ACTIVE_FLEET)
# ================================

class FleetState(SQLModel):
    id: str
    type: str  # DRONE / AMBULANCE
    status: str  # FLYING / ARRIVED
    current_lng: float
    current_lat: float
    battery: float
    eta_seconds: float


ACTIVE_FLEET: Dict[str, Dict] = {}


# ================================
#   空域高度层动态分配 (Altitude Allocation)
# ================================
def _allocate_drone_altitude() -> float:
    """
    动态分配无人机飞行高度。
    设定 5 个高度层 (300m - 500m)，间隔 50m。
    算法：找出当前天空中被占用最少的高度层，实现“负载均衡”防撞。
    """
    available_layers = [300.0, 350.0, 400.0, 450.0, 500.0]
    usage = {layer: 0 for layer in available_layers}

    # 统计当前在途飞机的层级占用情况
    for fleet in ACTIVE_FLEET.values():
        if fleet.get("type") == "DRONE" and fleet.get("status") == "FLYING":
            alt = fleet.get("altitude", 0.0)
            if alt in usage:
                usage[alt] += 1

    # 返回占用数最少的高度层
    return min(usage, key=usage.get)


# ================================
#   高德 API 真实路网寻路
# ================================

def _get_coords_by_name(name: str, session: Session):
    """
    根据前端传来的名字，获取它真实的经纬度 (用于传给高德 API)
    """
    mapped_name = LOCATION_MAPPING.get(name, name)

    # 0. 允许前端直接传 "lng,lat"
    lng_lat = _parse_lng_lat_text(name)
    if lng_lat:
        return lng_lat

    lng_lat = _parse_lng_lat_text(mapped_name)
    if lng_lat:
        return lng_lat

    # 1. 尝试从医院表获取精确坐标
    hosp = session.exec(select(Hospital).where(Hospital.name == mapped_name)).first()
    if hosp:
        return hosp.lng, hosp.lat

    # 2. 尝试从路网节点 json 获取节点坐标
    node_map = _load_road_node_by_name()
    node = node_map.get(mapped_name) or node_map.get(name)
    if node:
        return float(node["lng"]), float(node["lat"])

    return None, None


def get_amap_driving_route(start_lng, start_lat, end_lng, end_lat):
    """
    调用高德地图 Web服务 API，获取真实的驾车轨迹点阵
    """
    # 必须通过环境变量提供 Web 服务 Key，禁止硬编码进仓库
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        print("⚠️ 未配置环境变量 AMAP_API_KEY，将跳过高德寻路并回退到本地路网 compute_route。")
        return []

    url = (
        "https://restapi.amap.com/v3/direction/driving"
        f"?origin={start_lng},{start_lat}&destination={end_lng},{end_lat}&key={api_key}"
    )

    try:
        response = requests.get(url, timeout=5).json()
        if response.get("status") == "1" and response.get("route", {}).get("paths"):
            path_points = []
            steps = response["route"]["paths"][0]["steps"]
            for step in steps:
                # 高德返回的 polyline 是长这样的："116.1,39.1;116.2,39.2"
                polyline = step["polyline"].split(";")
                for point in polyline:
                    lng, lat = map(float, point.split(","))
                    # 🌟 关键修改：将加密的 GCJ-02 转换为标准 WGS-84
                    wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                    path_points.append([wgs_lng, wgs_lat])
            return path_points  # 返回几百个密集坐标点
    except Exception as e:
        print(f"❌ 高德API请求失败: {e}")

    return []  # 失败兜底返回空


def _haversine_distance_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """简易球面距离计算，单位：米。"""
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _compute_segment_lengths(path: List[List[float]]) -> List[float]:
    """返回每一段的长度数组，单位：米。len = len(path) - 1"""
    segs: List[float] = []
    for i in range(1, len(path)):
        lng1, lat1 = path[i - 1]
        lng2, lat2 = path[i]
        segs.append(_haversine_distance_m(lng1, lat1, lng2, lat2))
    return segs


def _register_fleet(
    resource_id: int,
    path: List[List[float]],
    use_drone: bool,
    vehicle_id: Optional[str] = None,
    battery_start: float = 100.0,
) -> None:
    """
    在内存中登记一个新的在途载具。
    """
    if not path:
        return

    # 生成唯一 ID（优先用真实载具编号，便于前端锁定/追踪）
    if vehicle_id:
        fleet_id = f"{vehicle_id}-{int(time.time())}"
    else:
        fleet_id = f"{'drone' if use_drone else 'car'}-{resource_id}-{int(time.time())}"

    # 设定不同载具的平均速度（m/s），结合当前天气
    speed_kmh = get_speed_kmh("DRONE" if use_drone else "AMBULANCE")
    speed_mps = speed_kmh * 1000.0 / 3600.0

    seg_lengths = _compute_segment_lengths(path)
    total_distance = sum(seg_lengths) if seg_lengths else 0.0

    ACTIVE_FLEET[fleet_id] = {
        "id": fleet_id,
        "type": "DRONE" if use_drone else "AMBULANCE",
        "status": "FLYING",
        "vehicle_id": vehicle_id,
        "resource_id": resource_id,
        "path": path,
        "segment_lengths": seg_lengths,
        "distance_total": total_distance,
        "speed_mps": speed_mps,
        "start_time": time.time(),
        "battery_start": float(battery_start),
    }


def _interpolate_position(
    path: List[List[float]],
    seg_lengths: List[float],
    target_distance: float,
) -> Dict[str, float]:
    """
    在多段路径上按照累计距离插值，返回当前位置经纬度。
    """
    if not path:
        return {"lng": 0.0, "lat": 0.0}
    if len(path) == 1 or not seg_lengths:
        lng, lat = path[0]
        return {"lng": lng, "lat": lat}

    remaining = target_distance
    for i, seg_len in enumerate(seg_lengths):
        if remaining > seg_len and i < len(seg_lengths) - 1:
            remaining -= seg_len
            continue

        # 当前段内插值
        start_lng, start_lat = path[i]
        end_lng, end_lat = path[i + 1]
        if seg_len <= 0:
            return {"lng": end_lng, "lat": end_lat}
        t = max(0.0, min(1.0, remaining / seg_len))
        lng = start_lng + (end_lng - start_lng) * t
        lat = start_lat + (end_lat - start_lat) * t
        return {"lng": lng, "lat": lat}

    # 超出终点：返回最后一个点
    lng, lat = path[-1]
    return {"lng": lng, "lat": lat}

@router.post("/plan_route")
def plan_route(request: RouteRequest, session: Session = Depends(get_session)):
    """
    多因子决策接口：比较无人机 vs 救护车的综合评分。
    """
    resource = session.get(MedicalResource, request.resource_id)
    if not resource:
        return {"error": "物资不存在"}

    # 3. 起终点解析：业务名/医院名 -> 路网节点名（必要时做最近节点吸附）
    real_start = _resolve_to_road_node(request.start_node, session)
    real_end = _resolve_to_road_node(request.end_node, session)

    print(f"🗺️ 路径规划: {request.start_node}({real_start}) -> {request.end_node}({real_end})")

    # 🌟 🌟 🌟 从这里开始插入碰撞检测逻辑 🌟 🌟 🌟
    start_lng, start_lat = _get_coords_by_name(request.start_node, session)
    end_lng, end_lat = _get_coords_by_name(request.end_node, session)

    rain_collision = False
    if request.rain_zone and start_lng and end_lng:
        rz_lng = request.rain_zone.get("lng")
        rz_lat = request.rain_zone.get("lat")
        if rz_lng and rz_lat:
            from algorithms import point_to_segment_distance
            dist_m = point_to_segment_distance(start_lng, start_lat, end_lng, end_lat, rz_lng, rz_lat)

            # 雨区半径判定为 600 米（前端视觉大概是这个范围，放宽一点增加触发率）
            if dist_m <= 600.0:
                rain_collision = True
                print(f"⚠️ 触发天气炸弹碰撞检测！距离雨区中心 {dist_m:.1f} 米")

    # 1. 计算评分 (🌟 把 rain_collision 传进去)
    drone_result = calculate_medical_score(resource, "DRONE", rain_collision)
    ambulance_result = calculate_medical_score(resource, "AMBULANCE", rain_collision)

    # 2. 顶层推荐方案（True = 推荐无人机）
    recommend_drone = drone_result["score"] > ambulance_result["score"]
    if request.forced_type in {"DRONE", "AMBULANCE"}:
        recommend_drone = request.forced_type == "DRONE"

    total_distance_km = 0.0
    assigned_altitude = 0.0

    try:
        # 4. 🌟 实施“水陆双轨制”真实寻路！
        if recommend_drone:
            # 【无人机路线】：走直线/简易拓扑图，拉高高度
            path_points = _compute_route_astar(real_start, real_end)
            path = [[p["lng"], p["lat"]] for p in path_points]
            assigned_altitude = _allocate_drone_altitude()  # 动态分配高空航道
        else:
            # 【救护车路线】：获取精确坐标，调用高德 API，贴地行驶
            start_lng, start_lat = _get_coords_by_name(request.start_node, session)
            end_lng, end_lat = _get_coords_by_name(request.end_node, session)

            if start_lng and end_lng:
                print(f"🚑 触发高德真实路网计算: ({start_lng},{start_lat}) -> ({end_lng},{end_lat})")
                path = get_amap_driving_route(start_lng, start_lat, end_lng, end_lat)
            else:
                # 兜底：如果找不到坐标，用原来的简易路网
                path_points = _compute_route_astar(real_start, real_end)
                path = [[p["lng"], p["lat"]] for p in path_points]

            assigned_altitude = 0.0  # 救护车高度分配为0 (前端会垫高2米)

        # 在内存中登记一个新的在途载具，供 /api/fleet 实时查询
        if path:
            # 计算总距离（km），用于风险评估和机队 ETA
            for i in range(1, len(path)):
                lng1, lat1 = path[i - 1]
                lng2, lat2 = path[i]
                total_distance_km += _haversine_distance_m(lng1, lat1, lng2, lat2) / 1000.0

            battery_start = _get_vehicle_battery_start(request.vehicle_id)
            _register_fleet(
                resource_id=request.resource_id,
                path=path,
                use_drone=recommend_drone,
                vehicle_id=request.vehicle_id,
                battery_start=battery_start,
            )
            # 把高度记入内存（便于后续调度统计层级占用）
            for f in ACTIVE_FLEET.values():
                if (
                    f.get("resource_id") == request.resource_id
                    and f.get("type") == ("DRONE" if recommend_drone else "AMBULANCE")
                ):
                    f["altitude"] = assigned_altitude

    except Exception as e:
        print(f"❌ 寻路失败: {e}")
        # 如果寻路失败（比如节点名字不对），返回一个空的路径，防止前端崩溃
        # 或者返回一条只有起终点的直线作为兜底
        path = []
        assigned_altitude = 0.0

    # 基于推荐方案做一次风险评估
    chosen_type = "DRONE" if recommend_drone else "AMBULANCE"
    chosen_score = drone_result if recommend_drone else ambulance_result
    bad_weather = chosen_score.get("bad_weather", 0.0)
    warnings = evaluate_risks(
        resource=resource,
        route_type=chosen_type,
        distance_km=total_distance_km,
        bad_weather=bad_weather,
        rain_collision=rain_collision,
    )
    # ================================
    #   持久化：调度任务 / 风险事件 / 决策日志
    # ================================

    task = DispatchTask(
        resource_id=request.resource_id,
        qty=1,  # 当前前端未传数量，默认一次调度 1 单位
        start_node=real_start,
        end_node=real_end,
        status="CREATED",
        recommended_mode=chosen_type,
        planned_distance_km=total_distance_km or None,
        planned_eta_seconds=None,
        path_json=json.dumps(path or []),
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    # 库存扣减闭环：每次成功规划路径，代表一次调度机会，先扣减一次库存
    if resource and getattr(resource, "stock", None) is not None:
        if resource.stock > 0:
            resource.stock -= 1
            session.add(resource)
            session.commit()
            session.refresh(resource)

    # 将风险评估结果写入 RiskEvent
    for w in warnings:
        session.add(
            RiskEvent(
                task_id=task.id,
                code=w.get("code", "UNKNOWN"),
                level=w.get("level", "WARNING"),
                msg=w.get("msg", ""),
                details_json=json.dumps(w, ensure_ascii=False),
            )
        )

    # 决策日志：记录输入/输出与解释
    decision = DecisionLog(
        task_id=task.id,
        algorithm_version="v1",
        params_json=None,
        input_json=json.dumps(
            {
                "resource_id": request.resource_id,
                "start_node": request.start_node,
                "end_node": request.end_node,
                "weather": chosen_score.get("bad_weather", None),
            },
            ensure_ascii=False,
        ),
        output_json=json.dumps(
            {
                "recommend": chosen_type,
                "distance_km": total_distance_km,
                "warnings": warnings,
            },
            ensure_ascii=False,
        ),
        explanation=f"推荐使用{'无人机' if recommend_drone else '地面救护车'}执行本次调度。",
    )
    session.add(decision)
    session.commit()

    return {
        "task_id": task.id,
        "resource_id": request.resource_id,
        "recommend": recommend_drone,
        "path": path,  # 这里返回的是真实的路径点
        "altitude": assigned_altitude,
        "warnings": warnings,
        # 完整信息
        "resource_info": resource,
        "analysis": [
            {
                "type": "无人机急送",
                "score": drone_result["score"],
                "logs": drone_result["logs"],
                "recommend": recommend_drone,
            },
            {
                "type": "地面救护车",
                "score": ambulance_result["score"],
                "logs": ambulance_result["logs"],
                "recommend": not recommend_drone,
            },
        ],
    }

@router.post("/route")
def route(request: RouteRequest, session: Session = Depends(get_session)):
    """
    简单路径接口
    """
    real_start = _resolve_to_road_node(request.start_node, session)
    real_end = _resolve_to_road_node(request.end_node, session)
    
    try:
        path_points = _compute_route_astar(real_start, real_end)
        return {"path_points": path_points}
    except:
        return {"path_points": []}


@router.get("/fleet", response_model=List[FleetState])
def get_fleet():
    """
    机队实时状态接口。

    基于内存中的 ACTIVE_FLEET，按当前时间计算每个载具的经纬度、电量和剩余时间。
    """
    now = time.time()
    result: List[FleetState] = []

    for fleet in ACTIVE_FLEET.values():
        path: List[List[float]] = fleet["path"]
        seg_lengths: List[float] = fleet["segment_lengths"]
        total_dist: float = fleet["distance_total"]
        speed_mps: float = fleet["speed_mps"]
        start_time: float = fleet["start_time"]

        if not path or total_dist <= 0 or speed_mps <= 0:
            continue

        elapsed = max(0.0, now - start_time)
        travelled = min(total_dist, elapsed * speed_mps)

        status = "ARRIVED" if travelled >= total_dist else "FLYING"
        eta = 0.0 if status == "ARRIVED" else (total_dist - travelled) / speed_mps

        # 简单电量模型：每公里消耗固定百分比
        km_travelled = travelled / 1000.0
        consumption_per_km = 2.0  # 每公里约 2%
        battery = max(0.0, fleet["battery_start"] - km_travelled * consumption_per_km)

        pos = _interpolate_position(path, seg_lengths, travelled)

        result.append(
            FleetState(
                id=fleet["id"],
                type=fleet["type"],
                status=status,
                current_lng=pos["lng"],
                current_lat=pos["lat"],
                battery=round(battery, 1),
                eta_seconds=round(eta, 1),
            )
        )

    return result


# ================================
#   调度任务查询接口
# ================================

@router.get("/tasks")
def list_tasks(
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    调度任务列表（简要信息，用于前端表格或日志列表）。
    """
    stmt = select(DispatchTask).order_by(DispatchTask.created_at.desc())
    if status:
        stmt = stmt.where(DispatchTask.status == status)
    tasks = session.exec(stmt).all()
    return tasks


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, session: Session = Depends(get_session)):
    """
    调度任务详情：聚合任务本身 + 风险事件 + 决策日志。
    """
    task = session.get(DispatchTask, task_id)
    if not task:
        return {"error": "task not found"}

    risks = session.exec(
        select(RiskEvent).where(RiskEvent.task_id == task_id).order_by(RiskEvent.created_at)
    ).all()

    decisions = session.exec(
        select(DecisionLog)
        .where(DecisionLog.task_id == task_id)
        .order_by(DecisionLog.created_at)
    ).all()

    return {
        "task": task,
        "risks": risks,
        "decisions": decisions,
    }