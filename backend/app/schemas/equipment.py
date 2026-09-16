from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

class EquipmentBase(BaseModel):
    factory: str = Field(..., min_length=1, description="所属工厂 (零前置建树)")
    department: str = Field(..., min_length=1, description="所属部门/车间 (零前置建树)")
    system_name: str = Field(..., min_length=1, description="所属系统/工段 (零前置建树)")
    equipment_name: str = Field(..., min_length=1, description="设备名称 (强制必填)")
    model_spec: str = Field(..., min_length=1, description="规格型号 (强制必填)")
    quantity: Optional[int] = Field(default=1, ge=1, description="数量 (选填，默认1)")
    parameters: Optional[str] = Field(default="", description="工况参数 (选填)")
    equipment_code: Optional[str] = Field(default="", description="设备编号 (可自动生成或自定义)")
    running_mode: Optional[str] = Field(default="CONTINUOUS", description="运行模式: CONTINUOUS (24h连续常开型) 或 INTERMITTENT (间歇开机/按需作业型)")
    maintenance_interval_hours: Optional[float] = Field(default=500.0, ge=1.0, description="维护倒计时周期 (小时，如 100h)")
    advance_warning_hours: Optional[float] = Field(default=20.0, ge=1.0, description="提前预警阈值 (小时，默认20h)")
    last_maintenance_hours: Optional[float] = Field(default=0.0, ge=0.0, description="上次完成维护时的运行工时")
    responsible_engineer_id: Optional[int] = None
    status: Optional[str] = "RUNNING"

class EquipmentCreate(EquipmentBase):
    initial_running_hours: Optional[float] = Field(default=0.0, ge=0.0, description="当前表盘读数/初始工时 (小时)")

class EquipmentUpdate(BaseModel):
    factory: Optional[str] = None
    department: Optional[str] = None
    system_name: Optional[str] = None
    equipment_name: Optional[str] = None
    model_spec: Optional[str] = None
    quantity: Optional[int] = None
    parameters: Optional[str] = None
    equipment_code: Optional[str] = None
    running_mode: Optional[str] = None
    maintenance_interval_hours: Optional[float] = None
    advance_warning_hours: Optional[float] = None
    last_maintenance_hours: Optional[float] = None
    responsible_engineer_id: Optional[int] = None
    status: Optional[str] = None

class EquipmentOut(EquipmentBase):
    id: int
    total_running_hours: float
    running_mode: str = "CONTINUOUS"
    maintenance_interval_hours: float = 500.0
    advance_warning_hours: float = 20.0
    last_maintenance_hours: float = 0.0
    countdown_hours: float = 500.0
    countdown_status: str = "HEALTHY"
    avg_daily_hours: Optional[float] = None
    estimated_days_left: Optional[float] = None
    last_runtime_updated_at: Optional[str] = None
    qr_code_url: Optional[str] = None
    is_deleted: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class HierarchyCreateRequest(BaseModel):
    factory: str = Field(..., min_length=1, description="工厂名称")
    department: str = Field(..., min_length=1, description="部门/车间名称")
    system_name: str = Field(..., min_length=1, description="系统/工段名称")

class HierarchyRenameRequest(BaseModel):
    level: str = Field(..., pattern="^(factory|department|system_name)$")
    old_name: str
    new_name: str

class HierarchyDeleteRequest(BaseModel):
    level: str = Field(..., pattern="^(factory|department|system_name)$")
    name: str
    factory: Optional[str] = None
    department: Optional[str] = None

class HierarchyDeletePreviewOut(BaseModel):
    level: str
    name: str
    affected_equipments: int
    affected_systems: int
    affected_departments: int
    retained_work_orders: int
    retained_maintenance_records: int
    warning_message: str

class HierarchyNode(BaseModel):
    name: str
    count: int
    children: Optional[List[Any]] = []

class RuntimeLogCreate(BaseModel):
    mode: Optional[str] = Field(default="AUTO", description="录入模式: DELTA (今日增量开机时长) 或 READING (表盘当前总读数)")
    reading_hours: Optional[float] = Field(default=None, ge=0.0, description="当前表盘累计读数 (小时)")
    delta_hours: Optional[float] = Field(default=None, ge=0.0, description="今日实际开机运行工时 (小时)")
    remark: Optional[str] = ""

class RuntimeLogOut(BaseModel):
    id: int
    equipment_id: int
    recorded_by: int
    reading_hours: float
    delta_hours: float
    remark: Optional[str] = ""
    recorded_at: str
    model_config = ConfigDict(from_attributes=True)
