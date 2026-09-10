from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import random

from app.database import get_quiz_session
from app.dependencies import get_db, get_current_user
from app.models import Quiz, Question, Result, Mistake

router = APIRouter(prefix="/quiz")
templates = Jinja2Templates(directory="templates")


@router.get("/{quiz_id}/setup", response_class=HTMLResponse)
async def quiz_setup(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(url="/")

    user = get_current_user(request, db)

    quiz_session = get_quiz_session(quiz.db_file)
    total_questions = quiz_session.query(Question).count()
    quiz_session.close()

    mistakes_count = 0
    frequent_mistakes_count = 0
    if user:
        mistakes = db.query(Mistake).filter(Mistake.user_id == user.id, Mistake.quiz_id == quiz_id).all()
        mistakes_count = len(mistakes)
        frequent_mistakes_count = len([m for m in mistakes if m.error_count > 1])

    return templates.TemplateResponse(
        request=request,
        name="quiz_setup.html",
        context={
            "request": request,
            "quiz": quiz,
            "total_questions": total_questions,
            "mistakes_count": mistakes_count,
            "frequent_mistakes_count": frequent_mistakes_count,
            "user": user
        }
    )


@router.get("/{quiz_id}/run")
async def quiz_run_get(quiz_id: int):
    return RedirectResponse(url=f"/quiz/{quiz_id}/setup", status_code=303)


@router.post("/{quiz_id}/run", response_class=HTMLResponse)
async def quiz_run(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    form_data = await request.form()
    limit = form_data.get("limit", "all")
    repeat_mode = form_data.get("repeat_mode", "all")  # 'all', 'mistakes_all', 'mistakes_frequent'
    immediate_solution = form_data.get("immediate_solution", "0") == "1"

    user = get_current_user(request, db)
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()

    if not quiz:
        return RedirectResponse(url="/")

    quiz_session = get_quiz_session(quiz.db_file)
    questions = quiz_session.query(Question).all()
    quiz_session.close()

    if not questions:
        return templates.TemplateResponse(
            request=request,
            name="quiz_setup.html",
            context={"request": request, "quiz": quiz, "total_questions": 0,
                     "error": "Dieses Quiz enthält noch keine Fragen."}
        )

    # Fragen filtern bei Fehler-Wiederholung
    if user and repeat_mode in ["mistakes_all", "mistakes_frequent"]:
        min_errors = 2 if repeat_mode == "mistakes_frequent" else 1
        mistakes = db.query(Mistake).filter(
            Mistake.user_id == user.id,
            Mistake.quiz_id == quiz_id,
            Mistake.error_count >= min_errors
        ).all()
        mistake_q_ids = [m.question_id for m in mistakes]
        questions = [q for q in questions if q.id in mistake_q_ids]

        if not questions:
            return RedirectResponse(url=f"/quiz/{quiz_id}/setup", status_code=303)

    if limit != "all" and repeat_mode == "all":
        limit_int = int(limit)
        if limit_int < len(questions):
            questions = random.sample(questions, limit_int)
    else:
        random.shuffle(questions)

    # Antworten mischen für die Darstellung
    for q in questions:
        options = []
        for letter, val in [('A', q.opt_a), ('B', q.opt_b), ('C', q.opt_c), ('D', q.opt_d),
                            ('E', q.opt_e), ('F', q.opt_f), ('G', q.opt_g), ('H', q.opt_h)]:
            if val and val != "-":
                options.append((letter, val))
        random.shuffle(options)
        q.shuffled_options = options

    question_ids = ",".join([str(q.id) for q in questions])

    return templates.TemplateResponse(
        request=request,
        name="quiz.html",
        context={
            "request": request,
            "quiz": quiz,
            "questions": questions,
            "question_ids": question_ids,
            "immediate_solution": immediate_solution
        }
    )


@router.get("/{quiz_id}/submit")
async def quiz_submit_get(quiz_id: int):
    return RedirectResponse(url=f"/quiz/{quiz_id}/setup", status_code=303)


@router.post("/{quiz_id}/submit", response_class=HTMLResponse)
async def quiz_submit(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    form_data = await request.form()
    user = get_current_user(request, db)

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(url="/")

    quiz_session = get_quiz_session(quiz.db_file)
    questions = quiz_session.query(Question).all()
    quiz_session.close()

    q_dict = {str(q.id): q for q in questions}
    score = 0
    mistakes = []
    user_answers_dict = {}

    submitted_q_ids = form_data.get("question_ids", "").split(",")
    submitted_q_ids = [q_id for q_id in submitted_q_ids if q_id]
    total = len(submitted_q_ids)

    if total == 0:
        return RedirectResponse(url=f"/quiz/{quiz_id}/setup", status_code=303)

    for q_id in submitted_q_ids:
        if q_id not in q_dict:
            continue

        q_obj = q_dict[q_id]
        correct_answers = set([ans.strip() for ans in q_obj.correct_answers.split(",")])
        user_answers = set(form_data.getlist(f"q_{q_id}"))

        user_answers_dict[q_id] = list(user_answers)

        if correct_answers == user_answers:
            score += 1
            if user:
                existing_mistake = db.query(Mistake).filter(
                    Mistake.user_id == user.id,
                    Mistake.quiz_id == quiz_id,
                    Mistake.question_id == int(q_id)
                ).first()
                if existing_mistake:
                    db.delete(existing_mistake)  # Gelöst -> aus der Fehlerliste löschen
        else:
            mistakes.append(q_obj)
            if user:
                existing = db.query(Mistake).filter(
                    Mistake.user_id == user.id,
                    Mistake.quiz_id == quiz_id,
                    Mistake.question_id == int(q_id)
                ).first()
                if existing:
                    existing.error_count += 1
                else:
                    db.add(Mistake(user_id=user.id, quiz_id=quiz_id, question_id=int(q_id), error_count=1))

    if user:
        db.add(Result(user_id=user.id, quiz_id=quiz_id, score=score, total=total))
        db.commit()

    return templates.TemplateResponse(
        request=request,
        name="quiz_result.html",
        context={
            "request": request,
            "score": score,
            "total": total,
            "mistakes": mistakes,
            "user_answers": user_answers_dict,
            "is_guest": user is None,
            "quiz_id": quiz_id
        }
    )