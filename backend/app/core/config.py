import os
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MaintainWise 2.0"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 路径中立性设计 (pathlib.Path)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT: Path = BASE_DIR.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    UPLOADS_DIR: Path = PROJECT_ROOT / "data" / "uploads"
    QR_DIR: Path = PROJECT_ROOT / "data" / "uploads" / "qrcodes"
    BACKUP_DIR: Path = PROJECT_ROOT / "data" / "backups"
    DB_PATH: Path = PROJECT_ROOT / "data" / "maintainwise.db"
    STATIC_DIR: Path = PROJECT_ROOT / "frontend" / "dist"
    
    # JWT 8小时免密长效会话
    SECRET_KEY: str = "maintainwise-v2-super-secret-key-for-jwt-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 小时
    
    model_config = ConfigDict(
        case_sensitive=True,
        extra="allow"
    )

settings = Settings()
