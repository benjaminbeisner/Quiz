from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.database import user_engine, UserSessionLocal
from app import models
from app.dependencies import get_db, get_current_user
from app.routers import auth, dashboard, quiz, admin, register
from app.security import get_password_hash

# Tabellen automatisch generieren
models.UserBase.metadata.create_all(bind=user_engine)

# Standard-Admin "Benny" anlegen, falls er nicht existiert
db_session = UserSessionLocal()
if not db_session.query(models.User).filter(models.User.username == "Benny").first():
    default_admin = models.User(
        username="Benny",
        password_hash=get_password_hash("QuizMaster#112"),
        is_admin=True,
        must_change_password=True
    )
    db_session.add(default_admin)
    db_session.commit()
db_session.close()

app = FastAPI(title="Quiz Server")

app.add_middleware(SessionMiddleware, secret_key="super-secret-quiz-key-112")
templates = Jinja2Templates(directory="templates")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(quiz.router)
app.include_router(admin.router)
app.include_router(register.router)

# 100% sicherer Fallback für leere Quiz-Aufrufe direkt auf App-Ebene
@app.get("/quiz", include_in_schema=False)
@app.get("/quiz/", include_in_schema=False)
async def redirect_quiz_base():
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    all_quizzes = db.query(models.Quiz).all()

    if user:
        if user.is_admin:
            visible_quizzes = all_quizzes
        else:
            user_cat_ids = [c.id for c in user.categories]
            visible_quizzes = [q for q in all_quizzes if q.category_id in user_cat_ids]
    else:
        visible_quizzes = [q for q in all_quizzes if q.category and q.category.is_for_guests]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "quizzes": visible_quizzes, "user": user}
    )