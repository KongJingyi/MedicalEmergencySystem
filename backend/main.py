# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 解决跨域问题

from database import create_db_and_tables
from routers.resources import router as resources_router
from routers.logistics import router as logistics_router


app = FastAPI(title="医疗应急联运系统核心API")

# 允许前端跨域请求 (Vue 端口通常是 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，演示方便
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """应用启动时统一建表。"""
    create_db_and_tables()


# 挂载路由模块
app.include_router(resources_router)
app.include_router(logistics_router)