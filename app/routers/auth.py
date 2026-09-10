from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import User, RegistrationRequest
from app.security import verify_password, get_password_hash

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...),
                     db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        # Prüfen, ob der User in der Warteschlange ist
        pending = db.query(RegistrationRequest).filter(RegistrationRequest.username == username).first()
        if pending:
            return templates.TemplateResponse(request=request, name="login.html", context={
                "request": request,
                "error": "Dein Account befindet sich noch in der manuellen Freischaltung. Bitte habe noch etwas Geduld."
            })
        return templates.TemplateResponse(request=request, name="login.html",
                                          context={"request": request, "error": "Falscher Benutzername oder Passwort."})

    if not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request=request, name="login.html",
                                          context={"request": request, "error": "Falscher Benutzername oder Passwort."})

    request.session["user_id"] = user.id

    if user.must_change_password:
        return RedirectResponse(url="/change-password", status_code=303)

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_get(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="change_password.html", context={"request": request})


@router.post("/change-password", response_class=HTMLResponse)
async def change_password_post(request: Request, new_password: str = Form(...), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")

    user = db.query(User).filter(User.id == user_id).first()
    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    db.commit()
    return RedirectResponse(url="/", status_code=303)