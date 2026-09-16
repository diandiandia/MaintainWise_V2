from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

class KnowledgeCaseBase(BaseModel):
    title: str
    equipment_category: Optional[str] = "通用"
    phenomenon: str
    root_cause: str
    solution_steps: str
    tags: Optional[str] = ""
    is_featured: Optional[bool] = False

class KnowledgeCaseCreate(KnowledgeCaseBase):
    source_order_id: Optional[int] = None

class KnowledgeCaseUpdate(BaseModel):
    title: Optional[str] = None
    equipment_category: Optional[str] = None
    phenomenon: Optional[str] = None
    root_cause: Optional[str] = None
    solution_steps: Optional[str] = None
    tags: Optional[str] = None
    is_featured: Optional[bool] = None

class KnowledgeCaseOut(KnowledgeCaseBase):
    id: int
    source_order_id: Optional[int] = None
    created_by_engineer_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class TimelineItem(BaseModel):
    event_type: str  # 'WORK_ORDER', 'MAINTENANCE', 'RUNTIME_LOG'
    event_time: str
    title: str
    operator_id: int
    operator_name: str
    details: Dict[str, Any]
