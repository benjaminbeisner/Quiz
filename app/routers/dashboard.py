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

    quiz_dict = {q.id: q.title for q in db.query(Quiz).all()}

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


@router.post("/repeat/{quiz_id}", response_class=HTMLResponse)
async def repeat_mistakes(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(url="/")

    mistakes = db.query(Mistake).filter(Mistake.user_id == user.id, Mistake.quiz_id == quiz_id).all()
    if not mistakes:
        return RedirectResponse(url="/dashboard")

    question_ids_to_repeat = [m.question_id for m in mistakes]

    quiz_session = get_quiz_session(quiz.db_file)
    questions = quiz_session.query(Question).filter(Question.id.in_(question_ids_to_repeat)).all()
    quiz_session.close()

    question_ids = ",".join([str(q.id) for q in questions])

    return templates.TemplateResponse(
        request=request,
        name="quiz.html",
        context={"request": request, "quiz": quiz, "questions": questions, "question_ids": question_ids}
    )