from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


# ==== Auth ====
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str     # relaxado para aceitar qualquer string
    password: str


# ==== Users ====
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "OPERATOR"
    assigned_city: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    assigned_city: Optional[str] = None

class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    assigned_city: Optional[str] = None

    class Config:
        from_attributes = True


# ==== Locations ====
class LocationCreate(BaseModel):
    city: str
    name: str
    area: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class LocationUpdate(BaseModel):
    city: Optional[str] = None
    name: Optional[str] = None
    area: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class LocationRead(LocationCreate):
    id: int

    class Config:
        from_attributes = True


# ==== Records ====
class RecordCreate(BaseModel):
    operator_id: int
    service_type: str
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    location_city: Optional[str] = None
    location_area: Optional[float] = None
    gps_used: bool = True
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class RecordRead(RecordCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Versão detalhada (para GET /api/records/{id}) com URLs das fotos
class RecordDetail(RecordRead):
    before_photos: List[str] = []
    after_photos: List[str] = []


# ==== Photos ====
class PhotoRead(BaseModel):
    id: int
    record_id: int
    phase: str
    url_path: str
    width: Optional[int]
    height: Optional[int]
    bytes: Optional[int]

    class Config:
        from_attributes = True
