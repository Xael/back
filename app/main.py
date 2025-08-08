import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session

from .database import init_db, get_session
from .models import User, Location, Record, Photo
from .schemas import (
    Token, LoginRequest, UserCreate, UserRead,
    LocationCreate, LocationRead,
    RecordCreate, RecordRead, PhotoRead
)
from .auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin
)
from .crud import (
    get_user_by_email, create_user, list_users,
    create_location, list_locations,
    create_record, list_records, add_photo
)

UPLOAD_DIR = "/app/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="CRB Serviços API (v3)")

# CORS
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Static uploads
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.on_event("startup")
def on_startup():
    init_db()
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        from .database import engine
        with Session(engine) as session:
            user = get_user_by_email(session, admin_email)
            pwd = hash_password(admin_password)
            if user:
                user.password_hash = pwd
                user.role = "ADMIN"
                session.add(user)
                session.commit()
            else:
                create_user(session, admin_email, name="Admin", role="ADMIN", password_hash=pwd)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# Auth (accept JSON or FormData)
@app.post("/api/auth/login", response_model=Token)
def login(
    payload: Optional[LoginRequest] = Body(default=None),
    form_email: Optional[str] = Form(default=None),
    form_password: Optional[str] = Form(default=None),
    session: Session = Depends(get_session),
):
    email = (payload.email if payload else form_email)
    password = (payload.password if payload else form_password)
    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password are required")
    user = get_user_by_email(session, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token}

# Users (admin)
@app.get("/api/users", response_model=List[UserRead], dependencies=[Depends(require_admin)])
def users_list(session: Session = Depends(get_session)):
    return list_users(session)

@app.post("/api/users", response_model=UserRead, dependencies=[Depends(require_admin)])
def users_create(payload: UserCreate, session: Session = Depends(get_session)):
    if get_user_by_email(session, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = create_user(session, payload.email, payload.name, payload.role, hash_password(payload.password))
    return user

# Locations
@app.get("/api/locations", response_model=List[LocationRead], dependencies=[Depends(get_current_user)])
def locations_list(session: Session = Depends(get_session)):
    return list_locations(session)

@app.post("/api/locations", response_model=LocationRead, dependencies=[Depends(require_admin)])
def locations_create(payload: LocationCreate, session: Session = Depends(get_session)):
    return create_location(session, **payload.model_dump())

# Records
@app.get("/api/records", response_model=List[RecordRead], dependencies=[Depends(get_current_user)])
def records_list(city: Optional[str] = None, session: Session = Depends(get_session)):
    return list_records(session, city=city)

@app.post("/api/records", response_model=RecordRead, dependencies=[Depends(get_current_user)])
def records_create(payload: RecordCreate, session: Session = Depends(get_session)):
    return create_record(session, **payload.model_dump())

# Photos upload
@app.post("/api/records/{record_id}/photos", response_model=List[PhotoRead], dependencies=[Depends(get_current_user)])
async def upload_photos(
    record_id: int,
    phase: str = Form(...),
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session)
):
    rec = session.get(Record, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    saved = []
    import uuid, pathlib
    for f in files:
        contents = await f.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"{f.filename} too large")
        ext = pathlib.Path(f.filename).suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(status_code=400, detail="Invalid image format")
        name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(UPLOAD_DIR, name)
        with open(path, "wb") as out:
            out.write(contents)
        try:
            from PIL import Image
            with Image.open(path) as im:
                width, height = im.size
        except Exception:
            width = height = None
        ph = add_photo(session,
            record_id=record_id,
            phase=phase.upper(),
            url_path=f"/uploads/{name}",
            width=width, height=height, bytes=len(contents)
        )
        saved.append(ph)
    return saved
