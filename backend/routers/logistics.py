from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from models import MedicalResource, RouteRequest
from algorithms import calculate_medical_score, compute_route


router = APIRouter(prefix="/api", tags=["logistics"])


@router.post("/plan_route")
def plan_route(request: RouteRequest, session: Session = Depends(get_session)):
    """
    多因子决策接口：比较无人机 vs 救护车的综合评分。
    """
    resource = session.get(MedicalResource, request.resource_id)
    if not resource:
        return {"error": "物资不存在"}

    drone_result = calculate_medical_score(resource, "DRONE")
    ambulance_result = calculate_medical_score(resource, "AMBULANCE")

    # 顶层推荐方案（True = 推荐无人机，False = 推荐地面救护车）
    recommend_drone = drone_result["score"] > ambulance_result["score"]

    # 结合路网计算一条物理路径，前端可以直接用来画线
    path_points = compute_route(request.start_node, request.end_node)
    path = [[p["lng"], p["lat"]] for p in path_points]

    return {
        # 前端同学要求的简洁字段
        "resource_id": request.resource_id,
        "recommend": recommend_drone,
        "path": path,

        # 为了给评委/日志看的完整信息，保留原有结构
        "resource_info": resource,
        "analysis": [
            {
                "type": "无人机急送",
                "score": drone_result["score"],
                "logs": drone_result["logs"],
                "recommend": drone_result["score"] > ambulance_result["score"],
            },
            {
                "type": "地面救护车",
                "score": ambulance_result["score"],
                "logs": ambulance_result["logs"],
                "recommend": ambulance_result["score"] > drone_result["score"],
            },
        ],
    }


@router.post("/route")
def route(request: RouteRequest):
    """
    路径规划接口：根据路网返回一串经纬度路径点。

    当前约定：start_node / end_node 使用 road_nodes.json 里的节点名称，
    例如 \"西直门桥\" -> \"东直门桥\"。
    """
    path_points = compute_route(request.start_node, request.end_node)
    return {"path_points": path_points}

