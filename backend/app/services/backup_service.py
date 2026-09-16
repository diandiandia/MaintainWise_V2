import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from app.core.config import settings

def execute_system_backup() -> Dict[str, Any]:
    """
    单文件 SQLite WAL 模式在线纯 Python 热备份
    将 maintainwise.db 与 uploads/ 目录无阻塞打包为带时间戳的标准 ZIP 归档包
    """
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"maintainwise_backup_{timestamp}.zip"
    zip_path = settings.BACKUP_DIR / zip_filename
    
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. 打包 SQLite 数据库文件 (WAL 模式支持在线并发读取)
        if settings.DB_PATH.exists():
            zipf.write(str(settings.DB_PATH), arcname="maintainwise.db")
            
        # 2. 递归打包 uploads 目录下的所有二维码、图纸与照片
        if settings.UPLOADS_DIR.exists():
            for root, _, files in os.walk(str(settings.UPLOADS_DIR)):
                for file in files:
                    file_full_path = Path(root) / file
                    arcname = Path("uploads") / file_full_path.relative_to(settings.UPLOADS_DIR)
                    zipf.write(str(file_full_path), arcname=str(arcname))
                    
    size_bytes = zip_path.stat().st_size
    return {
        "backup_file": zip_filename,
        "backup_path": str(zip_path),
        "size_bytes": size_bytes,
        "created_at": datetime.now().isoformat()
    }
