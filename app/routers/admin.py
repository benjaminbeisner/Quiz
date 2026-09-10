from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv

from app.database import get_quiz_session
from app.dependencies import get_db, get_current_user
from app.models import User, Quiz, Question, Category, RegistrationRequest
from app.security import get_password_hash
from app.mailer import send_email

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
    categories = db.query(Category).all()
    requests = db.query(RegistrationRequest).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"request": request, "users": users, "quizzes": quizzes, "categories": categories, "requests": requests}
    )


@router.post("/approve-request/{req_id}")
async def approve_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse("/login")

    form_data = await request.form()
    category_ids = form_data.getlist("category_ids")

    req = db.query(RegistrationRequest).filter(RegistrationRequest.id == req_id).first()
    if req:
        new_user = User(
            username=req.username,
            first_name=req.first_name,
            last_name=req.last_name,
            email=req.email,
            usage_intent=req.usage_intent,
            password_hash=req.password_hash,
            is_admin=False,
            must_change_password=False
        )
        if category_ids:
            new_user.categories = db.query(Category).filter(Category.id.in_(category_ids)).all()

        db.add(new_user)
        db.delete(req)
        db.commit()

        subject = "Dein Quiz-Account wurde freigeschaltet!"
        body = f"Hallo {req.first_name},\n\ndein Account ({req.username}) wurde freigeschaltet. Du kannst dich nun einloggen und loslegen!"
        send_email(req.email, subject, body)

    return RedirectResponse("/admin", status_code=303)


@router.post("/reject-request/{req_id}")
async def reject_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse("/login")

    req = db.query(RegistrationRequest).filter(RegistrationRequest.id == req_id).first()
    if req:
        db.delete(req)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/create-category")
async def create_category(request: Request, name: str = Form(...), is_for_guests: bool = Form(False),
                          db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")
    new_cat = Category(name=name, is_for_guests=is_for_guests)
    db.add(new_cat)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/edit-category/{category_id}")
async def edit_category(request: Request, category_id: int, name: str = Form(...), is_for_guests: bool = Form(False),
                        db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")
    category = db.query(Category).filter(Category.id == category_id).first()
    if category:
        category.name = name
        category.is_for_guests = is_for_guests
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/create-user")
async def create_user(request: Request, username: str = Form(...), is_admin: bool = Form(False),
                      db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")
    new_user = User(
        username=username,
        password_hash=get_password_hash("QuizMaster#112"),
        is_admin=is_admin,
        must_change_password=True
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/edit-user-categories/{target_user_id}")
async def edit_user_categories(request: Request, target_user_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")

    form_data = await request.form()
    category_ids = form_data.getlist("category_ids")

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if target_user:
        target_user.categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        db.commit()

        cat_names = [c.name for c in target_user.categories]
        subject = "Update deiner Quiz-Freigaben"
        body = f"Hallo {target_user.first_name},\n\ndeine Themen-Freigaben wurden aktualisiert. Du hast nun Zugriff auf:\n" + "\n".join(
            cat_names)
        if target_user.email:
            send_email(target_user.email, subject, body)

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/create-quiz")
async def create_quiz(request: Request, title: str = Form(...), time_limit: int = Form(0),
                      category_id: int = Form(None), db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")
    new_quiz = Quiz(title=title, time_limit_minutes=time_limit, db_file="", category_id=category_id)
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    new_quiz.db_file = f"quiz_{new_quiz.id}.db"
    db.commit()
    quiz_session = get_quiz_session(new_quiz.db_file)
    quiz_session.close()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/edit-quiz/{quiz_id}")
async def edit_quiz(request: Request, quiz_id: int, title: str = Form(...), time_limit: int = Form(...),
                    category_id: int = Form(None), db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz:
        quiz.title = title
        quiz.time_limit_minutes = time_limit
        quiz.category_id = category_id if category_id else None
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/upload-csv")
async def upload_csv(request: Request, quiz_id: int = Form(...), file: UploadFile = File(...),
                     db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not check_admin(current_user): return RedirectResponse(url="/login")
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz: return RedirectResponse(url="/admin", status_code=303)
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
    if decoded is None: decoded = contents.decode('utf-8', errors='replace')
    lines = [line for line in decoded.splitlines() if line.strip()]
    if not lines: return RedirectResponse(url="/admin", status_code=303)
    header = lines[0]
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    csv_reader = csv.reader(lines, delimiter=delimiter)
    quiz_session = get_quiz_session(quiz.db_file)
    next(csv_reader, None)
    for row in csv_reader:
        if len(row) > 0 and ";" in row[0] and len(row[0].split(";")) > 2:
            row = row[0].split(";")
        if len(row) >= 2:
            while len(row) < 11: row.append("-")
            clean_text = row[0].replace("[cite: 1]", "").replace("[cite: 2]", "").replace("[cite: 3]", "").strip()
            q = Question(
                text=clean_text, q_type=row[1].strip(), opt_a=row[2].strip() if row[2].strip() else "-",
                opt_b=row[3].strip() if row[3].strip() else "-", opt_c=row[4].strip() if row[4].strip() else "-",
                opt_d=row[5].strip() if row[5].strip() else "-", opt_e=row[6].strip() if row[6].strip() else "-",
                opt_f=row[7].strip() if row[7].strip() else "-", opt_g=row[8].strip() if row[8].strip() else "-",
                opt_h=row[9].strip() if row[9].strip() else "-", correct_answers=row[10].strip()
            )
            quiz_session.add(q)
    quiz_session.commit()
    quiz_session.close()
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/quiz/{quiz_id}/questions", response_class=HTMLResponse)
async def manage_questions(request: Request, quiz_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not check_admin(user): return RedirectResponse(url="/login")
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz: return RedirectResponse(url="/admin")
    quiz_session = get_quiz_session(quiz.db_file)
    questions = quiz_session.query(Question).all()
    quiz_session.close()
    return templates.TemplateResponse(request=request, name="admin_questions.html",
                                      context={"request": request, "quiz": quiz, "questions": questions})


@router.post("/quiz/{quiz_id}/edit-question/{question_id}")
async def edit_question(
        request: Request, quiz_id: int, question_id: int, text: str = Form(...), opt_a: str = Form(...),
        opt_b: str = Form(...), opt_c: str = Form(...), opt_d: str = Form(...), opt_e: str = Form("-"),
        opt_f: str = Form("-"), opt_g: str = Form("-"), opt_h: str = Form("-"), correct_answers: str = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not check_admin(user): return RedirectResponse(url="/login")
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz: return RedirectResponse(url="/admin")
    quiz_session = get_quiz_session(quiz.db_file)
    q = quiz_session.query(Question).filter(Question.id == question_id).first()
    if q:
        q.text = text;
        q.opt_a = opt_a;
        q.opt_b = opt_b;
        q.opt_c = opt_c;
        q.opt_d = opt_d
        q.opt_e = opt_e;
        q.opt_f = opt_f;
        q.opt_g = opt_g;
        q.opt_h = opt_h;
        q.correct_answers = correct_answers
        quiz_session.commit()
    quiz_session.close()
    return RedirectResponse(url=f"/admin/quiz/{quiz_id}/questions", status_code=303)