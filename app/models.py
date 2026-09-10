from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import UserBase, QuizBase

user_categories = Table(
    "user_categories",
    UserBase.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("category_id", Integer, ForeignKey("categories.id"))
)

class Category(UserBase):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_for_guests = Column(Boolean, default=False)
    quizzes = relationship("Quiz", back_populates="category")
    users = relationship("User", secondary=user_categories, back_populates="categories")

class User(UserBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    usage_intent = Column(String, nullable=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=True)
    categories = relationship("Category", secondary=user_categories, back_populates="users")

class RegistrationRequest(UserBase):
    __tablename__ = "registration_requests"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    usage_intent = Column(String)
    requested_categories = Column(String)
    password_hash = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Quiz(UserBase):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    time_limit_minutes = Column(Integer, default=0)
    db_file = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", back_populates="quizzes")

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
    error_count = Column(Integer, default=1)

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