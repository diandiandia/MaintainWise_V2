from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, equipments, maintenance, work_orders, knowledge, system, docs
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
api_router.include_router(users.router, prefix="/users", tags=["人员管理"])
api_router.include_router(equipments.router, prefix="/equipments", tags=["设备与工时"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["维护单与保养"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["维修工单"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["排故知识库"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理与运维"])
api_router.include_router(docs.router, prefix="/docs", tags=["在线系统设计文档"])
