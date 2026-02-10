from fastapi import APIRouter, Depends
from sqlmodel import Session
from database import get_session
from models import MedicalResource, RouteRequest
from algorithms import calculate_medical_score, compute_route

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

    try:
        # 4. 结合路网计算路径
        path_points = compute_route(real_start, real_end)
        
        # 格式化为前端需要的 [[lng, lat], ...]
        path = [[p["lng"], p["lat"]] for p in path_points]
        
    except Exception as e:
        print(f"❌ 寻路失败: {e}")
        # 如果寻路失败（比如节点名字不对），返回一个空的路径，防止前端崩溃
        # 或者返回一条只有起终点的直线作为兜底
        path = []

    return {
        "resource_id": request.resource_id,
        "recommend": recommend_drone,
        "path": path, # 这里返回的是真实的路径点

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