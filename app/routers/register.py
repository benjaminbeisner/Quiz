from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User, RegistrationRequest, Category
from app.security import get_password_hash
from app.mailer import send_email, ADMIN_EMAIL

router = APIRouter(prefix="/register")
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def register_form(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return templates.TemplateResponse(request=request, name="register.html",
                                      context={"request": request, "categories": categories})


@router.post("/", response_class=HTMLResponse)
async def submit_registration(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        first_name: str = Form(...),
        last_name: str = Form(...),
        email: str = Form(...),
        usage_intent: str = Form(""),
        db: Session = Depends(get_db)
):
    form_data = await request.form()
    category_ids = form_data.getlist("category_ids")
    requested_cats_str = ",".join(category_ids)

    existing_user = db.query(User).filter(User.username == username).first()
    existing_req = db.query(RegistrationRequest).filter(RegistrationRequest.username == username).first()

    if existing_user or existing_req:
        categories = db.query(Category).all()
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"request": request, "categories": categories,
                     "error": "Dieser Benutzername ist bereits vergeben oder befindet sich in Prüfung."}
        )

    new_req = RegistrationRequest(
        username=username,
        password_hash=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        email=email,
        usage_intent=usage_intent,
        requested_categories=requested_cats_str
    )
    db.add(new_req)
    db.commit()

    user_subject = "Deine Registrierungsanfrage beim Quiz"
    user_body = f"Hallo {first_name},\n\ndeine Anfrage wurde gespeichert. Das Projekt wird ehrenamtlich verwaltet, weshalb Accounts manuell freigeschaltet werden. Sobald wir deinen Account geprüft haben, erhältst du eine Bestätigung."
    send_email(email, user_subject, user_body)

    admin_subject = "Neue Quiz-Registrierung"
    admin_body = f"Neuer Nutzer wartet auf Freischaltung:\nName: {first_name} {last_name}\nUsername: {username}\nEmail: {email}\nNutzungsgrund: {usage_intent}"
    send_email(ADMIN_EMAIL, admin_subject, admin_body)

    return templates.TemplateResponse(request=request, name="register.html",
                                      context={"request": request, "success": True})