from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class WorkOrderCreate(BaseModel):
    equipment_id: int
    title: str = Field(..., min_length=1, description="故障简述 (必填)")
    phenomenon: Optional[str] = ""
    urgency: Optional[str] = Field("NORMAL", pattern="^(NORMAL|MAJOR|CRITICAL)$")
    fault_photo_path: Optional[str] = ""

class WorkOrderDispatch(BaseModel):
    assignee_id: Optional[int] = None

class WorkOrderResolve(BaseModel):
    root_cause: str = Field(..., min_length=2, description="故障根本原因 (强制必填)")
    solution_steps: str = Field(..., min_length=2, description="详细排除步骤 (强制必填)")
    spare_parts: Optional[str] = ""
    repair_photos: Optional[str] = ""
    repair_duration_minutes: Optional[int] = 0

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    phenomenon: Optional[str] = None
    urgency: Optional[str] = None
    fault_photo_path: Optional[str] = None
    repair_photos: Optional[str] = None
    root_cause: Optional[str] = None
    solution_steps: Optional[str] = None
    spare_parts: Optional[str] = None
    repair_duration_minutes: Optional[int] = None

class WorkOrderOut(BaseModel):
    id: int
    order_no: str
    equipment_id: int
    equipment_name: Optional[str] = None
    source: str
    title: str
    phenomenon: Optional[str] = ""
    urgency: str
    fault_photo_path: Optional[str] = ""
    repair_photos: Optional[str] = ""
    reporter_id: int
    reporter_name: Optional[str] = None
    reported_at: str
    status: str
    assigned_by_engineer_id: Optional[int] = None
    assigned_by_name: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    claimed_at: Optional[str] = None
    root_cause: Optional[str] = ""
    solution_steps: Optional[str] = ""
    spare_parts: Optional[str] = ""
    repair_duration_minutes: Optional[int] = 0
    completed_at: Optional[str] = None
    is_featured_case: bool
    model_config = ConfigDict(from_attributes=True)

