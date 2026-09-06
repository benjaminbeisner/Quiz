from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.database import user_engine, UserBase
from app.dependencies import get_db, get_current_user
from app.models import User, Quiz
from app.security import get_password_hash
from app.routers import auth, admin, quiz, dashboard

UserBase.metadata.create_all(bind=user_engine)

app = FastAPI(title="Quiz Webanwendung")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key-112")
templates = Jinja2Templates(directory="templates")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(quiz.router)
app.include_router(dashboard.router)


def init_admin():
    db = next(get_db())
    if not db.query(User).filter(User.username == "admin").first():
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("QuizMaster#112"),
            is_admin=True,
            must_change_password=True
        )
        db.add(admin_user)
        db.commit()


init_admin()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    quizzes = db.query(Quiz).all()

    if user and user.must_change_password:
        return RedirectResponse(url="/first-login")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "user": user, "quizzes": quizzes}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)