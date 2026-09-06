from fastapi import Request
from sqlalchemy.orm import Session
from app.database import UserSessionLocal
from app.models import User

def get_db():
    db = UserSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None