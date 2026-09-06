from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Hauptdatenbank für Nutzer und Einstellungen
USER_DB_URL = "sqlite:///./users.db"
user_engine = create_engine(USER_DB_URL, connect_args={"check_same_thread": False})
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)
UserBase = declarative_base()

# Basis für die dynamischen Quiz-Datenbanken
QuizBase = declarative_base()

def get_quiz_engine(db_filename: str):
    """Erstellt dynamisch eine Verbindung zur jeweiligen Themen-Datenbank."""
    url = f"sqlite:///./{db_filename}"
    return create_engine(url, connect_args={"check_same_thread": False})

def get_quiz_session(db_filename: str):
    """Liefert eine fertige Session für das jeweilige Quiz."""
    engine = get_quiz_engine(db_filename)
    QuizBase.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()