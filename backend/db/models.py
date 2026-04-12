"""
Database models for Archimedes — SQLAlchemy ORM.
Supports PostgreSQL (production) and SQLite (dev fallback).
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    """User account for authentication."""
    __tablename__ = "users"
    id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, index=True, nullable=True)
    role = Column(String(20), default="user")  # user, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    usage_records = relationship("UsageRecord", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(50), primary_key=True)  # session_id from WebSocket
    user_id = Column(String(50), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")
    messages = relationship("Message", back_populates="session")
    artifacts = relationship("Artifact", back_populates="session")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id"))
    goal = Column(Text)
    status = Column(String(20))  # pending, running, complete, failed
    plan = Column(JSON)  # Store current plan phases here
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="tasks")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id"))
    role = Column(String(20))  # user, assistant, system, tool
    content = Column(Text)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")


class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id"))
    name = Column(String(255))
    type = Column(String(50))  # file, screenshot, presentation
    path = Column(String(511))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="artifacts")


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id = Column(String(50), ForeignKey("users.id"), primary_key=True)
    
    # Settings Screenshot 2
    language = Column(String(50), default="English")
    theme = Column(String(20), default="dark")  # light, dark, system
    product_updates = Column(Boolean, default=True)
    task_emails = Column(Boolean, default=True)
    
    # Personalization Screenshot 9
    nickname = Column(String(100), nullable=True)
    occupation = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    custom_instructions = Column(Text, nullable=True)
    
    # Account & Usage
    credits_remaining = Column(Integer, default=300)
    browser_persistence = Column(Boolean, default=True)
    
    # Mail Manus Screenshot 5
    manus_email = Column(String(255), nullable=True)
    workflow_email = Column(String(255), nullable=True)
    
    # Integrations Config (Storage for keys/tokens)
    integrations_json = Column(JSON, default=dict)
    skills_json = Column(JSON, default=dict)
    connectors_json = Column(JSON, default=dict)
    
    user = relationship("User", back_populates="settings")


class UsageRecord(Base):
    __tablename__ = "usage_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.id"))
    details = Column(String(255))
    credits_change = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="usage_records")
