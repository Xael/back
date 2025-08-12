import os, json
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session, select

from .database import init_db, get_session
from .models import User, Location, Record, Photo
from .schemas import (
    Token, LoginRequest, UserCreate, UserRead,
    LocationCreate, LocationRead, LocationUpdate,   # LocationUpdate precisa existir no schemas
    RecordCreate, RecordRead, RecordDetail,         # RecordDetail precisa existir no schemas
    PhotoRead, UserUpdate                           # UserUpdate precisa existir no schemas
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

app = FastAPI(title="CRB Serviços API (v4)")

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

@app.get("/debug/ping", include_in_schema=False)
def debug_ping():
    return {"pong": True}

# -------------------------
# Auth
# -------------------------

# Aceita JSON, form-data, x-www-form-urlencoded, ou query params.
@app.post("/api/auth/login", response_model=Token)
async def login_any(
    request: Request,
    session: Session = Depends(get_session),
    q_email: Optional[str] = Query(default=None),
    q_password: Optional[str] = Query(default=None),
):
    email = None
    password = None

    # 1) JSON
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
            if isinstance(data, dict):
                email = data.get("email") or data.get("username") or data.get("user")
                password = data.get("password") or data.get("pass")
    except Exception:
        pass

    # 2) form (multipart ou x-www-form-urlencoded)
    if email is None or password is None:
        try:
            form = await request.form()
            if form:
                email = email or form.get("email") or form.get("username") or form.get("user")
                password = password or form.get("password") or form.get("pass")
        except Exception:
            pass

    # 3) query params
    if email is None or password is None:
        email = email or q_email
        password = password or q_password

    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password are required")

    user = get_user_by_email(session, str(email))
    if not user or not verify_password(str(password), user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token}

# Quem sou eu
@app.get("/api/auth/me", response_model=UserRead, dependencies=[Depends(get_current_user)])
def auth_me(current: User = Depends(get_current_user)):
    # UserRead: id, email, name, role
    return UserRead.model_validate(current, from_attributes=True)

# -------------------------
# Users (ADMIN)
# -------------------------

@app.get("/api/users", response_model=List[UserRead], dependencies=[Depends(require_admin)])
def users_list(session: Session = Depends(get_session)):
    return list_users(session)

@app.post("/api/users", response_model=UserRead, dependencies=[Depends(require_admin)])
def users_create(payload: UserCreate, session: Session = Depends(get_session)):
    if get_user_by_email(session, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    user = create_user(session, payload.email, payload.name, payload.role, hash_password(payload.password))
    return user

@app.put("/api/users/{user_id}", response_model=UserRead, dependencies=[Depends(require_admin)])
def users_update(user_id: int, payload: UserUpdate, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Atualiza campos básicos
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        # se quiser, valide duplicidade aqui
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role
    if payload.password is not None and payload.password.strip():
        user.password_hash = hash_password(payload.password)

    # assigned_city: só vai funcionar se existir no modelo/esquema
    if hasattr(user, "assigned_city") and getattr(payload, "assigned_city", None) is not None:
        setattr(user, "assigned_city", payload.assigned_city)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.delete("/api/users/{user_id}", dependencies=[Depends(require_admin)])
def users_delete(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"ok": True}

# -------------------------
# Locations
# -------------------------

@app.get("/api/locations", response_model=List[LocationRead], dependencies=[Depends(get_current_user)])
def locations_list(session: Session = Depends(get_session)):
    return list_locations(session)

@app.post("/api/locations", response_model=LocationRead, dependencies=[Depends(require_admin)])
def locations_create(payload: LocationCreate, session: Session = Depends(get_session)):
    return create_location(session, **payload.model_dump())

@app.put("/api/locations/{loc_id}", response_model=LocationRead, dependencies=[Depends(require_admin)])
def locations_update(loc_id: int, payload: LocationUpdate, session: Session = Depends(get_session)):
    loc = session.get(Location, loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(loc, k, v)

    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc

@app.delete("/api/locations/{loc_id}", dependencies=[Depends(require_admin)])
def locations_delete(loc_id: int, session: Session = Depends(get_session)):
    loc = session.get(Location, loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    session.delete(loc)
    session.commit()
    return {"ok": True}

# -------------------------
# Records
# -------------------------

@app.get("/api/records", response_model=List[RecordRead], dependencies=[Depends(get_current_user)])
def records_list(city: Optional[str] = None, session: Session = Depends(get_session)):
    return list_records(session, city=city)

@app.post("/api/records", response_model=RecordRead, dependencies=[Depends(get_current_user)])
def records_create(payload: RecordCreate, session: Session = Depends(get_session)):
    return create_record(session, **payload.model_dump())

@app.get("/api/records/{record_id}", response_model=RecordDetail, dependencies=[Depends(get_current_user)])
def records_get(record_id: int, session: Session = Depends(get_session)):
    rec = session.get(Record, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    # Busca fotos e separa por fase
    photos = session.exec(select(Photo).where(Photo.record_id == record_id).order_by(Photo.id.asc())).all()
    before_photos = [p.url_path for p in photos if (p.phase or "").upper() == "BEFORE"]
    after_photos  = [p.url_path for p in photos if (p.phase or "").upper() == "AFTER"]

    # Monta payload RecordDetail
    base = {
        "id": rec.id,
        "operator_id": rec.operator_id,
        "service_type": rec.service_type,
        "location_id": rec.location_id,
        "location_name": rec.location_name,
        "location_city": rec.location_city,
        "location_area": rec.location_area,
        "gps_used": rec.gps_used,
        "start_time": rec.start_time,
        "end_time": rec.end_time,
        "created_at": rec.created_at,
        "before_photos": before_photos,
        "after_photos": after_photos,
    }
    return base  # Pydantic v2 aceita dicts se o schema bate

@app.delete("/api/records/{record_id}", dependencies=[Depends(get_current_user)])
def records_delete(record_id: int, session: Session = Depends(get_session)):
    rec = session.get(Record, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    # Remove fotos do disco e do banco
    photos = session.exec(select(Photo).where(Photo.record_id == record_id)).all()
    for p in photos:
        # p.url_path vem tipo "/uploads/arquivo.jpg" — resolvemos no filesystem com segurança
        rel = p.url_path.lstrip("/").split("/", 1)
        file_name = rel[1] if len(rel) == 2 else rel[0]
        if file_name:
            abs_path = os.path.normpath(os.path.join(UPLOAD_DIR, os.path.basename(file_name)))
            try:
                if abs_path.startswith(UPLOAD_DIR) and os.path.exists(abs_path):
                    os.remove(abs_path)
            except Exception:
                pass
        session.delete(p)

    session.delete(rec)
    session.commit()
    return {"ok": True}

# -------------------------
# Photos upload
# -------------------------

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
