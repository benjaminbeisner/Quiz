import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Trage hier später deine echten Daten ein
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "deine-email@example.com"
SMTP_PASSWORD = "dein-passwort"
ADMIN_EMAIL = "admin@deine-feuerwehr.de" # Hierhin gehen die Benachrichtigungen an dich

def send_email(to_email: str, subject: str, body: str):
    if SMTP_SERVER == "smtp.example.com":
        print(f"\n--- MOCK EMAIL ---")
        print(f"To: {to_email}\nSubject: {subject}\nBody:\n{body}")
        print(f"------------------\n")
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Fehler beim E-Mail-Versand: {e}")