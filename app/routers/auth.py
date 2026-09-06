from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import User
from app.security import verify_password, get_password_hash, is_password_strong_enough

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request}
    )


@router.post("/login")
async def login_post(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "error": "Ungültige Anmeldedaten"}
        )

    request.session["user_id"] = user.id

    if user.must_change_password:
        return RedirectResponse(url="/first-login", status_code=303)

    return RedirectResponse(url="/", status_code=303)


@router.get("/first-login", response_class=HTMLResponse)
async def first_login_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        request=request,
        name="first_login.html",
        context={"request": request}
    )


@router.post("/first-login")
async def first_login_post(
        request: Request,
        old_password: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    # 1. Altes Passwort prüfen
    if not verify_password(old_password, user.password_hash):
        error = "Das alte Passwort ist nicht korrekt."
        return templates.TemplateResponse(
            request=request,
            name="first_login.html",
            context={"request": request, "error": error}
        )

    # 2. Prüfen, ob neues Passwort und Bestätigung übereinstimmen
    if new_password != confirm_password:
        error = "Die neuen Passwörter stimmen nicht überein."
        return templates.TemplateResponse(
            request=request,
            name="first_login.html",
            context={"request": request, "error": error}
        )

    # 3. Kriterien prüfen
    if not is_password_strong_enough(new_password):
        error = "Das neue Passwort erfüllt die Kriterien nicht."
        return templates.TemplateResponse(
            request=request,
            name="first_login.html",
            context={"request": request, "error": error}
        )

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")