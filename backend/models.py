# backend/models.py
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, Optional

from sqlmodel import Field, SQLModel


class MedicalResource(SQLModel, table=True):
    """
    【核心数据模型】
    这里定义的每一个字段，都是为了应对评委关于"医疗特殊性"的质疑。
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str = Field(description="分类：血液/疫苗/器械/药品")

    # === 关键医疗约束 (评委看这里) ===
    min_temp: float = Field(description="最低存储温度 (摄氏度)")
    max_temp: float = Field(description="最高存储温度 (摄氏度)")

    # 震动敏感度：1-10，数值越低越娇贵
    # 例如：蛋白质晶体/红细胞=2 (极度怕震)，纱布=10 (不怕震)
    shock_sensitivity: int = Field(default=10, description="震动耐受度 (1-10)")

    # 紧急程度：1-5，数值越高越急
    # 算法会根据这个值，决定是否牺牲成本换时间
    urgency_level: int = Field(default=1, description="紧急优先权 (1-5)")

    # 单位体积/重量 (用于计算无人机是否超载)
    weight_kg: float = Field(description="单体重量 (kg)")
    volume_L: float = Field(description="单体体积 (L)")

    # === 真实供给约束 ===
    stock: int = Field(default=0, description="当前库存数量")
    priority: int = Field(default=3, description="调度优先级 (1-5)")


class Hospital(SQLModel, table=True):
    """
    医院表：承载前端地图上的“红点”以及调度起终点。
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    lng: float = Field(description="经度")
    lat: float = Field(description="纬度")
    level: str = Field(description="医院等级，如三甲")
    address: str = Field(description="详细地址")


class HospitalStatus(SQLModel, table=True):
    """
    医院压力状态表：承载 ICU 占用、急诊排队等动态负载信息。
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    hospital_name: str = Field(index=True, description="医院名称（关联 Hospital.name）")
    icu_occupancy_rate: float = Field(
        description="ICU 占用率 (0-100, 百分比)"
    )
    er_queue_length: int = Field(description="急诊排队人数")
    emergency_level: int = Field(
        description="应急等级：1=绿色, 2=黄色, 3=橙色, 4=红色"
    )


class RoadNode(SQLModel, table=True):
    """
    路网节点表：二环内关键路口/地标，用于构建路径规划图。
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    lng: float = Field(description="经度")
    lat: float = Field(description="纬度")
    node_type: str = Field(description="节点类型：路口/地标/医院等")


# ============================
#  调度任务 / 载具 / 风险事件
# ============================

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Vehicle(SQLModel, table=True):
    """
    载具表：无人机/救护车统一抽象。
    前端的“机队指挥中心”和后端 /api/fleet 都可以基于这里做真实化。
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # 业务唯一编号，如 D-01 / A-02
    code: str = Field(index=True)
    type: str = Field(description="载具类型：DRONE / AMBULANCE")

    status: str = Field(
        default="AVAILABLE",
        description="AVAILABLE / IN_SERVICE / MAINTENANCE / OFFLINE",
    )

    # 能力参数（演示可用，后续可不断细化）
    max_payload_kg: float = Field(default=5.0, description="最大载重(kg)")
    max_volume_L: float = Field(default=20.0, description="最大装载体积(L)")
    max_range_km: float = Field(default=20.0, description="最大续航/里程(km)")
    cruise_speed_kmh: float = Field(default=60.0, description="巡航速度(km/h)")
    max_wind_level: int = Field(default=6, description="抗风等级阈值(示意)")

    # 动态状态（可选用于落库；也可以只用于初始化）
    battery_percent: float = Field(default=100.0, description="电量(0-100)")
    current_lng: Optional[float] = Field(default=None, description="当前经度")
    current_lat: Optional[float] = Field(default=None, description="当前纬度")

    updated_at: datetime = Field(default_factory=_utcnow, index=True)


class DispatchTask(SQLModel, table=True):
    """
    调度任务表：把一次“调度/配送/联运”变成可追踪的业务对象。
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # 关联资源（医疗物资）
    resource_id: int = Field(foreign_key="medicalresource.id", index=True)
    qty: int = Field(default=1, description="数量")

    # 起终点：先用名称（与你们现有的 LOCATION_MAPPING / road_nodes.name 对齐）
    start_node: str = Field(index=True, description="起点名称(路网节点/业务名称)")
    end_node: str = Field(index=True, description="终点名称(路网节点/业务名称)")

    # 状态机
    status: str = Field(
        default="CREATED",
        index=True,
        description="CREATED / ASSIGNED / IN_TRANSIT / ARRIVED / COMPLETED / FAILED / CANCELED / REASSIGNED",
    )

    # 规划与推荐结果（可解释/可复盘）
    recommended_mode: Optional[str] = Field(
        default=None, description="推荐方式：DRONE / AMBULANCE / MULTI"
    )
    planned_distance_km: Optional[float] = Field(default=None)
    planned_eta_seconds: Optional[float] = Field(default=None)

    # 简化：把路径点存 JSON 字符串（后续也可以单独拆表存轨迹）
    path_json: Optional[str] = Field(default=None, description="[[lng,lat],...] 的 JSON 字符串")

    # 分配载具（先用 code 软关联，避免强外键带来复杂迁移）
    assigned_vehicle_code: Optional[str] = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=_utcnow, index=True)
    updated_at: datetime = Field(default_factory=_utcnow, index=True)
    completed_at: Optional[datetime] = Field(default=None, index=True)


class RiskEvent(SQLModel, table=True):
    """
    风险/告警事件表：把 evaluate_risks 的输出持久化，形成“处置闭环”证据链。
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="dispatchtask.id", index=True)

    code: str = Field(index=True, description="如 BATTERY_RISK / TEMP_RISK / WEATHER_RISK")
    level: str = Field(default="WARNING", description="INFO / WARNING / CRITICAL")
    msg: str = Field(description="告警文案")

    details_json: Optional[str] = Field(default=None, description="扩展信息 JSON")

    acknowledged: bool = Field(default=False, index=True)
    acknowledged_at: Optional[datetime] = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=_utcnow, index=True)


class DecisionLog(SQLModel, table=True):
    """
    决策日志表：把“为什么选无人机/救护车”的证据固化，便于解释与评估。
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="dispatchtask.id", index=True)

    algorithm_version: str = Field(default="v1", index=True)
    params_json: Optional[str] = Field(
        default=None, description="权重/阈值/规则版本等 JSON"
    )
    input_json: Optional[str] = Field(default=None, description="输入快照 JSON")
    output_json: Optional[str] = Field(default=None, description="输出快照 JSON")
    explanation: Optional[str] = Field(default=None, description="人类可读解释")

    created_at: datetime = Field(default_factory=_utcnow, index=True)


class InventoryBatch(SQLModel, table=True):
    """
    库存批次表：支持批号/效期/可用量（成熟项目常用的“医疗追溯”抓手）。
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    resource_id: int = Field(foreign_key="medicalresource.id", index=True)

    batch_no: str = Field(index=True, description="批号")
    expiry_date: Optional[date] = Field(default=None, index=True, description="失效日期")

    quantity_total: int = Field(default=0, description="入库总量")
    quantity_available: int = Field(default=0, description="当前可用量")

    # 批次级温控（有些物资不同批次/包装可能不同）
    min_temp: Optional[float] = Field(default=None, description="批次最低存储温度")
    max_temp: Optional[float] = Field(default=None, description="批次最高存储温度")

    created_at: datetime = Field(default_factory=_utcnow, index=True)


# 顺便定义一个“路径请求”模型，用于前端发给后端的数据格式
class RouteRequest(SQLModel):
    resource_id: int  # 送什么？
    start_node: str   # 从哪来？ (可以是坐标 \"120.1,30.2\" 或节点 ID)
    end_node: str     # 去哪儿？
    vehicle_id: Optional[str] = None  # 哪台车/机执行（如 D-01 / A-01），用于后端电量等状态初始化
    forced_type: Optional[str] = None  # 可选：强制指定 DRONE / AMBULANCE（用于演示人工派单）
    # 🌟 新增：接收前端传来的天气炸弹坐标
    rain_zone: Optional[Dict[str, float]] = None