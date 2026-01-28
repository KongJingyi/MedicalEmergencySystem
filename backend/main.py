# backend/main.py
from fastapi import FastAPI, Depends
from sqlmodel import Session, SQLModel, create_engine, select, delete
from models import MedicalResource, RouteRequest # 导入刚才定义的模型
from fastapi.middleware.cors import CORSMiddleware # 解决跨域问题
from algorithms import calculate_medical_score # 导入刚才写的算法

# 1. 设置数据库 (直接生成一个文件，无需安装软件)
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(title="医疗应急联运系统核心API")

# 2. 允许前端跨域请求 (Vue端口通常是5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许所有来源，演示方便
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # 可以在这里写代码：如果数据库是空的，自动插入几条假数据

# 3. 写一个接口：获取所有医疗资源
@app.get("/api/resources")
def get_resources():
    with Session(engine) as session:
        resources = session.exec(select(MedicalResource)).all()
        return resources

# 4. 写一个接口：初始化测试数据 (由前端按钮触发)
@app.post("/api/seed")
def seed_data():
    with Session(engine) as session:
        # 先清空旧数据 (防止重复点击生成多份)
        session.exec(delete(MedicalResource))
        
        # 1. 娇贵的 "O型Rh阴性血" (怕震、怕热、很急)
        blood = MedicalResource(
            name="O型Rh阴性血浆 (稀有)", 
            category="BLOOD",
            min_temp=2, max_temp=6,         # 必须冷藏
            shock_sensitivity=2,            # 极度怕震！(不能走颠簸路)
            urgency_level=5,                # 人命关天
            weight_kg=0.5, volume_L=0.5
        )
        
        # 2. 娇气的 "辉瑞mRNA疫苗" (极度怕热、不那么急)
        vaccine = MedicalResource(
            name="辉瑞mRNA疫苗 (极寒)", 
            category="VACCINE",
            min_temp=-80, max_temp=-60,     # 超低温！(普通车送不了)
            shock_sensitivity=6,            # 相对耐震
            urgency_level=3,                # 紧急但非立刻致命
            weight_kg=0.2, volume_L=0.1
        )
        
        # 3. 皮实的 "医用防护服" (随便送)
        suit = MedicalResource(
            name="医用防护服 Level-D", 
            category="EQUIPMENT",
            min_temp=-30, max_temp=50,      # 没啥要求
            shock_sensitivity=10,           # 随便震
            urgency_level=2,
            weight_kg=1.0, volume_L=5.0
        )
        
        session.add(blood)
        session.add(vaccine)
        session.add(suit)
        session.commit()
    return {"message": "✅ 3种典型医疗资源已注入数据库"}

@app.post("/api/plan_route")
def plan_route(request: RouteRequest):
    with Session(engine) as session:
        # 1. 从数据库找物资
        resource = session.get(MedicalResource, request.resource_id)
        if not resource:
            return {"error": "物资不存在"}
            
        # 2. 模拟运行两种方案的算法对比
        # 方案 A: 无人机
        drone_result = calculate_medical_score(resource, 'DRONE')
        
        # 方案 B: 救护车
        ambulance_result = calculate_medical_score(resource, 'AMBULANCE')
        
        # 3. 返回给前端（给评委看的对比结果）
        return {
            "resource_info": resource,
            "analysis": [
                {
                    "type": "无人机急送",
                    "score": drone_result['score'],
                    "logs": drone_result['logs'],
                    "recommend": drone_result['score'] > ambulance_result['score']
                },
                {
                    "type": "地面救护车",
                    "score": ambulance_result['score'],
                    "logs": ambulance_result['logs'],
                    "recommend": ambulance_result['score'] > drone_result['score']
                }
            ]
        }