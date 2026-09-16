from typing import Optional, Dict, List, Any
from pydantic import BaseModel, ConfigDict

class SystemSettingBase(BaseModel):
    factory_name: str
    smtp_host: Optional[str] = ""
    smtp_port: Optional[int] = 465
    smtp_user: Optional[str] = ""
    smtp_pass: Optional[str] = ""
    smtp_enabled: Optional[bool] = False
    notify_lead_days: Optional[int] = 3

class SystemSettingUpdate(SystemSettingBase):
    pass

class SystemSettingOut(SystemSettingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DashboardOut(BaseModel):
    equipment_stats: Dict[str, int]
    work_order_stats: Dict[str, int]
    role_todos: List[Dict[str, Any]]
    total_equipments: int
    countdown_stats: Optional[Dict[str, Any]] = None
    executive_kpis: Optional[Dict[str, Any]] = None
    department_issue_stats: Optional[List[Dict[str, Any]]] = None

class SmtpTestRequest(BaseModel):
    host: str
    port: int = 465
    user: str
    password: str
    to_email: Optional[str] = ""

