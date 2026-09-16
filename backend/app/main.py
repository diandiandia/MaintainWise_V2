from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保目录结构存在并初始化数据库
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    settings.QR_DIR.mkdir(parents=True, exist_ok=True)
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MaintainWise 2.0 智能工厂设备在线化便利系统单端口微核心",
    lifespan=lifespan
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载多媒体目录 (/uploads)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOADS_DIR)), name="uploads")

# 挂载主 API 路由 (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

# 静态资产挂载 (Vue 3 SPA 预编译静态包)
assets_dir = settings.STATIC_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """
    单端口全栈核心：SPA HTML5 History 路由回退处理器
    未匹配 API 的请求统一返回 frontend/dist/index.html 由 Vue 接管
    """
    if full_path.startswith("api/") or full_path.startswith("uploads/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
        
    index_file = settings.STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
        
    return JSONResponse(
        content={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "message": "MaintainWise 2.0 后端微核心运行中，前端尚未构建或处于 API 调试模式",
            "api_docs": "/docs"
        }
    )
