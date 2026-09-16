from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from app.core.deps import get_current_user
from app.core.config import settings

router = APIRouter()

# 获取 MaintainWise_V2 根目录下的 docs/ 路径
DOCS_DIR = settings.BASE_DIR.parent / "docs"

# 预置设计文档元数据与分类呈现顺序
DOC_METADATA = [
    {
        "id": "crs",
        "file_name": "1_customer_requirements_specification.md",
        "title": "1. 客户需求说明书 (CRS)",
        "category": "需求规格",
        "badge": "业务需求",
        "badge_type": "primary",
        "description": "车间一线维护场景、痛点诉求、业务用户角色与高层业务功能清单 (CRS)"
    },
    {
        "id": "sdd",
        "file_name": "2_system_design_document.md",
        "title": "2. 系统设计说明书 (SDD)",
        "category": "系统设计",
        "badge": "系统架构",
        "badge_type": "success",
        "description": "全栈架构拓扑、领域模型、单端口全栈服务、数据流图与高可用设计 (SDD)"
    },
    {
        "id": "srs",
        "file_name": "3_system_design_requirements_specification.md",
        "title": "3. 系统设计需求规格说明书 (SysRS)",
        "category": "需求规格",
        "badge": "系统需求清单",
        "badge_type": "info",
        "description": "SYSR-XXX 系统功能性与非功能性需求条目清单，双向可追溯性索引 (SysRS)"
    },
    {
        "id": "swdd",
        "file_name": "4_software_design_document.md",
        "title": "4. 软件设计说明书 (SwDD)",
        "category": "软件设计",
        "badge": "模块实现",
        "badge_type": "warning",
        "description": "FastAPI REST 接口契约、SQLite WAL 存储设计、状态机跃迁与安全设计 (SwDD)"
    },
    {
        "id": "swdrs",
        "file_name": "5_software_design_requirements_specification.md",
        "title": "5. 软件设计需求规格说明书 (SwDRS)",
        "category": "软件设计",
        "badge": "软件需求清单",
        "badge_type": "danger",
        "description": "SWR-XXX 软件模块细化功能需求、测试用例映射与验收准则 (SwDRS)"
    },
    {
        "id": "windows_deploy",
        "file_name": "windows_deployment_guide.md",
        "title": "6. Windows 生产部署与运维指南",
        "category": "部署运维",
        "badge": "运维实战",
        "badge_type": "success",
        "description": "全自动部署向导、Windows Service 后台自启守护、车间平板网络及灾备恢复"
    },
    {
        "id": "intermittent_sop",
        "file_name": "intermittent_equipment_operations_guide.md",
        "title": "7. 车间间歇设备工时与维保实操指南 (SOP)",
        "category": "现场实操",
        "badge": "现场管理",
        "badge_type": "warning",
        "description": "浮动工时设备伴随式采集、动态负荷预测、分级预警处理流程及防作弊管理机制"
    }
]

@router.get("", response_model=List[Dict[str, Any]])
def list_system_docs(
    current_user: dict = Depends(get_current_user)
):
    """
    在线浏览系统设计文档目录列表：
    管理员与员工均可在线检索全套需求规格、系统设计与部署实战文档
    """
    result = []
    for doc in DOC_METADATA:
        file_path = DOCS_DIR / doc["file_name"]
        size_bytes = 0
        updated_at = ""
        exists = file_path.exists()
        if exists:
            stat = file_path.stat()
            size_bytes = stat.st_size
            updated_at = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
        result.append({
            "id": doc["id"],
            "title": doc["title"],
            "category": doc["category"],
            "badge": doc["badge"],
            "badge_type": doc["badge_type"],
            "description": doc["description"],
            "file_name": doc["file_name"],
            "exists": exists,
            "size_bytes": size_bytes,
            "updated_at": updated_at
        })
    return result

@router.get("/{doc_id}")
def get_system_doc_content(
    doc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    获取指定系统设计文档的 Markdown 原文内容
    """
    target = None
    for doc in DOC_METADATA:
        if doc["id"] == doc_id:
            target = doc
            break
            
    if not target:
        raise HTTPException(status_code=404, detail=f"未找到该文档 ID: {doc_id}")
        
    file_path = DOCS_DIR / target["file_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文档物理文件不存在: {target['file_name']}")
        
    try:
        content = file_path.read_text(encoding="utf-8")
        return {
            "id": target["id"],
            "title": target["title"],
            "file_name": target["file_name"],
            "category": target["category"],
            "badge": target["badge"],
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
            "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")
