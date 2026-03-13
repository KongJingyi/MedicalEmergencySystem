import json

from sqlmodel import Session, SQLModel, create_engine

from models import Hospital, RoadNode, MedicalResource, HospitalStatus


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)


def create_db_and_tables() -> None:
    """确保所有数据表已经创建。"""
    SQLModel.metadata.create_all(engine)


def seed_hospitals() -> None:
    """从 data/hospitals.json 写入医院数据。"""
    with open("data/hospitals.json", "r", encoding="utf-8") as f:
        hospitals = json.load(f)

    with Session(engine) as session:
        # 可选：清空旧数据，防止重复插入
        session.query(Hospital).delete()
        for h in hospitals:
            session.add(Hospital(**h))
        session.commit()


def seed_road_nodes() -> None:
    """从 data/road_nodes.json 写入路网节点数据。"""
    with open("data/road_nodes.json", "r", encoding="utf-8") as f:
        nodes = json.load(f)

    with Session(engine) as session:
        session.query(RoadNode).delete()
        for n in nodes:
            session.add(RoadNode(**n))
        session.commit()


def seed_demo_resources() -> None:
    """保留原来的 3 个典型医疗资源，便于前端调试。"""
    with Session(engine) as session:
        session.query(MedicalResource).delete()

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


def seed_resources_from_file(path: str = "data/resources.json") -> None:
    """
    从 JSON 文件批量写入医疗物资数据。

    文件格式：数组，每一项字段需与 MedicalResource 对齐：
    name/category/min_temp/max_temp/shock_sensitivity/urgency_level/weight_kg/volume_L/stock/priority
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            resources = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ 未找到 {path}，将回退到 3 条演示物资。")
        seed_demo_resources()
        return

    if not isinstance(resources, list) or len(resources) == 0:
        print(f"⚠️ {path} 内容为空或格式不正确，回退到 3 条演示物资。")
        seed_demo_resources()
        return

    with Session(engine) as session:
        session.query(MedicalResource).delete()
        for item in resources:
            session.add(MedicalResource(**item))
        session.commit()
    print(f"✅ 已从 {path} 导入 {len(resources)} 条医疗物资。")


if __name__ == "__main__":
    create_db_and_tables()
    seed_hospitals()
    seed_road_nodes()
    # 优先导入专业物资库；若文件缺失则回退到演示数据
    seed_resources_from_file()

    # 为所有医院注入一份初始压力数据
    with Session(engine) as session:
        session.query(HospitalStatus).delete()
        hospitals = session.query(Hospital).all()
        for hosp in hospitals:
            # 默认中等压力
            icu = 70.0
            er_queue = 10
            level = 2
            # 为积水潭医院制造紧张感
            if "积水潭" in hosp.name:
                icu = 92.0
                er_queue = 25
                level = 4
            status = HospitalStatus(
                hospital_name=hosp.name,
                icu_occupancy_rate=icu,
                er_queue_length=er_queue,
                emergency_level=level,
            )
            session.add(status)
        session.commit()

    print("✅ Seed completed: hospitals, road nodes, demo medical resources and hospital status.")

