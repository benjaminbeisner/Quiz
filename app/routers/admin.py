from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
import io

from app.database import get_quiz_session
from app.dependencies import get_db, get_current_user
from app.models import User, Quiz, Question
from app.security import get_password_hash

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


def check_admin(user: User):
    if not user or not user.is_admin:
        return False
    return True


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not check_admin(user):
        return RedirectResponse(url="/login")

    users = db.query(User).all()
    quizzes = db.query(Quiz).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"request": request, "users": users, "quizzes": quizzes}
    )


@router.post("/create-user")
async def create_user(
        request: Request,
        username: str = Form(...),
        is_admin: bool = Form(False),
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not check_admin(current_user):
        return RedirectResponse(url="/login")

    new_user = User(
        username=username,
        password_hash=get_password_hash("QuizMaster#112"),
        is_admin=is_admin,
        must_change_password=True
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/create-quiz")
async def create_quiz(
        request: Request,
        title: str = Form(...),
        time_limit: int = Form(0),
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not check_admin(current_user):
        return RedirectResponse(url="/login")

    new_quiz = Quiz(title=title, time_limit_minutes=time_limit, db_file="")
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)

    new_quiz.db_file = f"quiz_{new_quiz.id}.db"
    db.commit()

    quiz_session = get_quiz_session(new_quiz.db_file)
    quiz_session.close()

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/edit-quiz/{quiz_id}")
async def edit_quiz(
        request: Request,
        quiz_id: int,
        title: str = Form(...),
        time_limit: int = Form(...),
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not check_admin(current_user):
        return RedirectResponse(url="/login")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz:
        quiz.title = title
        quiz.time_limit_minutes = time_limit
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/upload-csv")
async def upload_csv(
        request: Request,
        quiz_id: int = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not check_admin(current_user):
        return RedirectResponse(url="/login")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(url="/admin", status_code=303)

    if not quiz.db_file:
        quiz.db_file = f"quiz_{quiz.id}.db"
        db.commit()

    contents = await file.read()

    decoded = None
    for encoding in ['utf-8-sig', 'utf-8', 'windows-1252', 'cp850', 'iso-8859-1']:
        try:
            decoded = contents.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded is None:
        decoded = contents.decode('utf-8', errors='replace')

    lines = [line for line in decoded.splitlines() if line.strip()]
    if not lines:
        return RedirectResponse(url="/admin", status_code=303)

    # Dynamische Erkennung des Trennzeichens
    header = lines[0]
    delimiter = ";" if header.count(";") >= header.count(",") else ","

    csv_reader = csv.reader(lines, delimiter=delimiter)
    quiz_session = get_quiz_session(quiz.db_file)

    next(csv_reader, None)

    for row in csv_reader:
        # Brutal-Force Excel Workaround: Bricht die Zeile auf, falls Excel alles in row[0] packt
        if len(row) > 0 and ";" in row[0] and len(row[0].split(";")) > 2:
            row = row[0].split(";")

        if len(row) >= 2:
            # Fehlende Spalten sicher auffüllen
            while len(row) < 11:
                row.append("-")

            # Fehlerhafte Zitate restlos entfernen
            clean_text = row[0].replace("[cite: 1]", "").replace("[cite: 2]", "").replace("[cite: 3]", "").strip()

            q = Question(
                text=clean_text,
                q_type=row[1].strip(),
                opt_a=row[2].strip() if row[2].strip() else "-",
                opt_b=row[3].strip() if row[3].strip() else "-",
                opt_c=row[4].strip() if row[4].strip() else "-",
                opt_d=row[5].strip() if row[5].strip() else "-",
                opt_e=row[6].strip() if row[6].strip() else "-",
                opt_f=row[7].strip() if row[7].strip() else "-",
                opt_g=row[8].strip() if row[8].strip() else "-",
                opt_h=row[9].strip() if row[9].strip() else "-",
                correct_answers=row[10].strip()
            )
            quiz_session.add(q)

    quiz_session.commit()
    quiz_session.close()

    return RedirectResponse(url="/admin", status_code=303)


@router.get("/quiz/{quiz_id}/questions", response_class=HTMLResponse)
async def manage_questions(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not check_admin(user):
        return RedirectResponse(url="/login")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(url="/admin")

    quiz_session = get_quiz_session(quiz.db_file)
    questions = quiz_session.query(Question).all()
    quiz_session.close()

    return templates.TemplateResponse(
        request=request,
        name="admin_questions.html",
        context={"request": request, "quiz": quiz, "questions": questions}
    )


@router.post("/quiz/{quiz_id}/edit-question/{question_id}")
async def edit_question(
        request: Request,
        quiz_id: int,
        question_id: int,
        text: str = Form(...),
        opt_a: str = Form(...),
        opt_b: str = Form(...),
        opt_c: str = Form(...),
        opt_d: str = Form(...),
        opt_e: str = Form("-"),
        opt_f: str = Form("-"),
        opt_g: str = Form("-"),
        opt_h: str = Form("-"),
        correct_answers: str = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not check_admin(user):
        return RedirectResponse(url="/login")

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(url="/admin")

    quiz_session = get_quiz_session(quiz.db_file)
    q = quiz_session.query(Question).filter(Question.id == question_id).first()

    if q:
        q.text = text
        q.opt_a = opt_a
        q.opt_b = opt_b
        q.opt_c = opt_c
        q.opt_d = opt_d
        q.opt_e = opt_e
        q.opt_f = opt_f
        q.opt_g = opt_g
        q.opt_h = opt_h
        q.correct_answers = correct_answers
        quiz_session.commit()

    quiz_session.close()
    return RedirectResponse(url=f"/admin/quiz/{quiz_id}/questions", status_code=303)