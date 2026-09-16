from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

class ChecklistItem(BaseModel):
    item: str
    standard: Optional[str] = ""

class MaintenancePlanBase(BaseModel):
    equipment_id: int
    plan_name: str
    interval_days: Optional[int] = 30
    check_items: List[ChecklistItem]
    is_active: Optional[bool] = True

class MaintenancePlanCreate(MaintenancePlanBase):
    pass

class MaintenancePlanOut(BaseModel):
    id: int
    equipment_id: int
    plan_name: str
    created_by_engineer_id: int
    interval_days: int
    check_items_json: str
    last_completed_date: Optional[str] = None
    next_due_date: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ChecklistResultItem(BaseModel):
    item: str
    standard: Optional[str] = ""
    status: str = Field("NORMAL", pattern="^(NORMAL|ABNORMAL)$")
    remark: Optional[str] = ""

class MaintenanceRecordSubmit(BaseModel):
    equipment_id: int
    plan_id: Optional[int] = None
    checklist_results: List[ChecklistResultItem]
    is_normal: bool = True
    anomaly_desc: Optional[str] = ""
    log_runtime_hours: Optional[float] = Field(default=None, ge=0.0, description="现场打卡顺便填报今日开机运行工时 (小时)")

class MaintenanceRecordRevise(BaseModel):
    checklist_results: Optional[List[ChecklistResultItem]] = None
    revision_reason: str = Field(..., min_length=2, description="修改原因与复核批注 (强制必填)")
    is_normal: Optional[bool] = None
    anomaly_desc: Optional[str] = None

class MaintenanceRecordOut(BaseModel):
    id: int
    record_no: str
    equipment_id: int
    equipment_name: Optional[str] = None
    plan_id: Optional[int] = None
    technician_id: int
    technician_name: Optional[str] = None
    status: str
    is_locked_for_tech: bool
    submitted_at: Optional[str] = None
    revised_by_engineer_id: Optional[int] = None
    revised_by_name: Optional[str] = None
    revised_at: Optional[str] = None
    revision_reason: Optional[str] = ""
    is_normal: bool
    checklist_result_json: str
    anomaly_desc: Optional[str] = ""
    interlocked_work_order_id: Optional[int] = None
    created_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
