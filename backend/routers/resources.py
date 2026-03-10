from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select, delete

from database import get_session
from models import MedicalResource, Hospital, RoadNode, HospitalStatus


router = APIRouter(prefix="/api", tags=["resources"])


@router.get("/resources")
def get_resources(session: Session = Depends(get_session)):
    """获取所有医疗物资，用于前端调度列表。"""
    return session.exec(select(MedicalResource)).all()


@router.get("/hospitals")
def get_hospitals(session: Session = Depends(get_session)):
    """获取所有医院点，用于前端在地图上画医院红点。"""
    return session.exec(select(Hospital)).all()


@router.get("/hospitals/status")
def get_hospital_status(session: Session = Depends(get_session)):
    """获取各医院的实时压力状态，用于 Dashboard 仪表盘。"""
    return session.exec(select(HospitalStatus)).all()


@router.get("/road_nodes")
def get_road_nodes(session: Session = Depends(get_session)):
    """获取路网关键节点，供前端做可视化或调试。"""
    return session.exec(select(RoadNode)).all()


@router.post("/seed")
def seed_demo_data(session: Session = Depends(get_session)):
    """
    初始化 3 个典型医疗资源（兼容原来的 /api/seed 按钮）。
    医院和路网节点建议使用 seed.py 脚本离线灌库。
    """
    # 先清空旧数据
    session.exec(delete(MedicalResource))

    blood = MedicalResource(
        name="O型Rh阴性血浆 (稀有)",
        category="BLOOD",
        min_temp=2,
        max_temp=6,
        shock_sensitivity=2,
        urgency_level=5,
        weight_kg=0.5,
        volume_L=0.5,
        stock=5,
        priority=5,
    )

    vaccine = MedicalResource(
        name="辉瑞mRNA疫苗 (极寒)",
        category="VACCINE",
        min_temp=-80,
        max_temp=-60,
        shock_sensitivity=6,
        urgency_level=3,
        weight_kg=0.2,
        volume_L=0.1,
        stock=10,
        priority=4,
    )

    suit = MedicalResource(
        name="医用防护服 Level-D",
        category="EQUIPMENT",
        min_temp=-30,
        max_temp=50,
        shock_sensitivity=10,
        urgency_level=2,
        weight_kg=1.0,
        volume_L=5.0,
        stock=100,
        priority=2,
    )

    session.add(blood)
    session.add(vaccine)
    session.add(suit)
    session.commit()

    return {"message": "✅ 3种典型医疗资源已注入数据库"}


class RelievePayload(BaseModel):
    hospital_name: str
    delta: int = 1


@router.post("/hospitals/relieve")
def relieve_hospital_pressure(payload: RelievePayload, session: Session = Depends(get_session)):
    """
    当任务完成、资源送达时，调用此接口以缓解对应医院的急诊压力。
    """
    status = session.exec(
        select(HospitalStatus).where(HospitalStatus.hospital_name == payload.hospital_name)
    ).first()
    if not status:
        return {"message": "hospital status not found"}

    status.er_queue_length = max(0, status.er_queue_length - payload.delta)
    session.add(status)
    session.commit()
    session.refresh(status)
    return status

