from fastapi import APIRouter, Depends
from sqlmodel import Session, SQLModel, select
from typing import Dict, List, Optional
import json
import math
import time

from database import get_session
from models import MedicalResource, RouteRequest, DispatchTask, RiskEvent, DecisionLog
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
    "调度中心": "西直门桥",          # 假设调度中心在西直门
    "目标医院": "积水潭医院",        # 如果路网里有积水潭这个点最好，没有就找最近的路口
    "北京大学人民医院": "官园桥",    # 示例映射
    "积水潭医院": "新街口豁口",      # 示例映射
    "START": "西直门桥",            # 兼容测试
    "END": "德胜门桥"               # 兼容测试
}


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


def _register_fleet(resource_id: int, path: List[List[float]], use_drone: bool) -> None:
    """
    在内存中登记一个新的在途载具。
    """
    if not path:
        return

    # 生成唯一 ID
    fleet_id = f"{'drone' if use_drone else 'car'}-{resource_id}-{int(time.time())}"

    # 设定不同载具的平均速度（m/s），结合当前天气
    speed_kmh = get_speed_kmh("DRONE" if use_drone else "AMBULANCE")
    speed_mps = speed_kmh * 1000.0 / 3600.0

    seg_lengths = _compute_segment_lengths(path)
    total_distance = sum(seg_lengths) if seg_lengths else 0.0

    ACTIVE_FLEET[fleet_id] = {
        "id": fleet_id,
        "type": "DRONE" if use_drone else "AMBULANCE",
        "resource_id": resource_id,
        "path": path,
        "segment_lengths": seg_lengths,
        "distance_total": total_distance,
        "speed_mps": speed_mps,
        "start_time": time.time(),
        "battery_start": 100.0,
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

    # 1. 计算评分
    drone_result = calculate_medical_score(resource, "DRONE")
    ambulance_result = calculate_medical_score(resource, "AMBULANCE")
    
    # 2. 顶层推荐方案（True = 推荐无人机）
    recommend_drone = drone_result["score"] > ambulance_result["score"]

    # 3. 🔥【关键修改】处理起终点映射
    # 如果前端传来的名字在映射表里，就用映射后的；如果不在，就尝试直接用原名
    real_start = LOCATION_MAPPING.get(request.start_node, request.start_node)
    real_end = LOCATION_MAPPING.get(request.end_node, request.end_node)

    print(f"🗺️ 路径规划: {request.start_node}({real_start}) -> {request.end_node}({real_end})")

    total_distance_km = 0.0

    try:
        # 4. 结合路网计算路径
        path_points = compute_route(real_start, real_end)

        # 格式化为前端需要的 [[lng, lat], ...]
        path = [[p["lng"], p["lat"]] for p in path_points]

        # 在内存中登记一个新的在途载具，供 /api/fleet 实时查询
        if path:
            # 计算总距离（km），用于风险评估和机队 ETA
            for i in range(1, len(path)):
                lng1, lat1 = path[i - 1]
                lng2, lat2 = path[i]
                total_distance_km += _haversine_distance_m(lng1, lat1, lng2, lat2) / 1000.0

            _register_fleet(
                resource_id=request.resource_id,
                path=path,
                use_drone=recommend_drone,
            )

    except Exception as e:
        print(f"❌ 寻路失败: {e}")
        # 如果寻路失败（比如节点名字不对），返回一个空的路径，防止前端崩溃
        # 或者返回一条只有起终点的直线作为兜底
        path = []

    # 基于推荐方案做一次风险评估
    chosen_type = "DRONE" if recommend_drone else "AMBULANCE"
    chosen_score = drone_result if recommend_drone else ambulance_result
    bad_weather = chosen_score.get("bad_weather", 0.0)
    warnings = evaluate_risks(
        resource=resource,
        route_type=chosen_type,
        distance_km=total_distance_km,
        bad_weather=bad_weather,
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
def route(request: RouteRequest):
    """
    简单路径接口
    """
    real_start = LOCATION_MAPPING.get(request.start_node, request.start_node)
    real_end = LOCATION_MAPPING.get(request.end_node, request.end_node)
    
    try:
        path_points = compute_route(real_start, real_end)
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