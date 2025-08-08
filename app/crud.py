from typing import Optional, List
from sqlmodel import Session, select
from .models import User, Location, Record, Photo

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()

def create_user(session: Session, email: str, name: str, role: str, password_hash: str) -> User:
    user = User(email=email, name=name, role=role, password_hash=password_hash)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def list_users(session: Session) -> List[User]:
    return session.exec(select(User).order_by(User.id.desc())).all()

def create_location(session: Session, **data) -> Location:
    loc = Location(**data)
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc

def list_locations(session: Session) -> List[Location]:
    return session.exec(select(Location).order_by(Location.id.desc())).all()

def create_record(session: Session, **data) -> Record:
    rec = Record(**data)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec

def list_records(session: Session, city: Optional[str] = None) -> List[Record]:
    stmt = select(Record).order_by(Record.id.desc())
    if city:
        stmt = stmt.where(Record.location_city == city)
    return session.exec(stmt).all()

def add_photo(session: Session, **data) -> Photo:
    ph = Photo(**data)
    session.add(ph)
    session.commit()
    session.refresh(ph)
    return ph
