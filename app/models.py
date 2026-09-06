from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import UserBase, QuizBase

# --- ZENTRALE DATENBANK (users.db) ---

class User(UserBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=True)

class Quiz(UserBase):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    time_limit_minutes = Column(Integer, default=0)
    db_file = Column(String)

class Result(UserBase):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    score = Column(Integer)
    total = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Mistake(UserBase):
    __tablename__ = "mistakes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    question_id = Column(Integer)

# --- THEMEN-DATENBANK (quiz_X.db) ---

class Question(QuizBase):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    q_type = Column(String)
    text = Column(String)
    opt_a = Column(String)
    opt_b = Column(String)
    opt_c = Column(String)
    opt_d = Column(String)
    opt_e = Column(String, default="-")
    opt_f = Column(String, default="-")
    opt_g = Column(String, default="-")
    opt_h = Column(String, default="-")
    correct_answers = Column(String)