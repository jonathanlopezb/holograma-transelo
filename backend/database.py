import os
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import datetime

# 🚩 LÓGICA DE CONEXIÓN HÍBRIDA (Local / Neon PostgreSQL)
DATABASE_URL = os.getenv("POSTGRES_URL")

# Si no hay URL de Postgres (Local), usamos SQLite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./transelo_events.db"
    # Ajuste para SQLite
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Ajuste para PostgreSQL (Neon)
    # Vercel a veces da la URL como postgres:// pero SQLAlchemy prefiere postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MODELOS
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    host_name = Column(String)
    event_type = Column(String)
    event_date = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)

class Guest(Base):
    __tablename__ = "guests"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    table_number = Column(String)
    special_message = Column(String, nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
