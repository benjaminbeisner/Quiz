from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_quiz_session
from app.dependencies import get_db, get_current_user
from app.models import Result, Mistake, Quiz, Question

router = APIRouter(prefix="/dashboard")
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def view_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    results = db.query(Result).filter(Result.user_id == user.id).order_by(Result.timestamp.desc()).all()

    mistakes = db.query(Mistake).filter(Mistake.user_id == user.id).all()
    mistakes_by_quiz = {}

    for m in mistakes:
        quiz = db.query(Quiz).filter(Quiz.id == m.quiz_id).first()
        if quiz:
            if quiz not in mistakes_by_quiz:
                mistakes_by_quiz[quiz] = []
            mistakes_by_quiz[quiz].append(m.question_id)

    # Nur Quizzes laden, die in einer Kategorie liegen, auf die der User Zugriff hat (oder Admin)
    all_quizzes = db.query(Quiz).all()
    if user.is_admin:
        allowed_quizzes = all_quizzes
    else:
        user_cat_ids = [cat.id for cat in user.categories]
        allowed_quizzes = [q for q in all_quizzes if q.category_id in user_cat_ids]

    quiz_dict = {q.id: q.title for q in allowed_quizzes}

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "user": user,
            "results": results,
            "mistakes_by_quiz": mistakes_by_quiz,
            "quiz_dict": quiz_dict
        }
    )