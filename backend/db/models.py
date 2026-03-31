from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(50), primary_key=True) # session_id from WebSocket
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="session")
    messages = relationship("Message", back_populates="session")
    artifacts = relationship("Artifact", back_populates="session")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id"))
    goal = Column(Text)
    status = Column(String(20)) # pending, running, complete, failed
    plan = Column(JSON) # Store current plan phases here
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="tasks")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id"))
    role = Column(String(20)) # user, assistant, system, tool
    content = Column(Text)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="messages")

class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("sessions.id"))
    name = Column(String(255))
    type = Column(String(50)) # file, screenshot, presentation
    path = Column(String(511))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("Session", back_populates="artifacts")
