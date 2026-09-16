from typing import Optional
from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    username: str
    full_name: str
    employee_no: str
    role: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    is_active: Optional[bool] = True
    must_change_password: Optional[bool] = False
    is_frozen: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    must_change_password: Optional[bool] = None
    is_frozen: Optional[bool] = None

class UserOut(UserBase):
    id: int
    password_changed_at: Optional[str] = None
    created_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    password_expiring_soon: Optional[bool] = False
    days_remaining: Optional[int] = None

class ResetPasswordRequest(BaseModel):
    new_password: str

class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str

