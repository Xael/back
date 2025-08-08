from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    name: str
    role: str = Field(default="OPERATOR")  # ADMIN, OPERATOR, FISCAL
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Location(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city: str
    name: str
    area: Optional[float] = Field(default=None)  # m²
    lat: Optional[float] = None
    lng: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Record(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    operator_id: int = Field(foreign_key="user.id")
    service_type: str
    location_id: Optional[int] = Field(default=None, foreign_key="location.id")
    location_name: Optional[str] = None
    location_city: Optional[str] = None
    location_area: Optional[float] = None
    gps_used: bool = True
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Photo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    record_id: int = Field(foreign_key="record.id")
    phase: str  # BEFORE, AFTER
    url_path: str
    width: Optional[int] = None
    height: Optional[int] = None
    bytes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
