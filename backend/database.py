from sqlalchemy import create_url
import os
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import datetime

# Database setup (SQLite for simplicity/portability, but ready for Postgres)
SQLALCHEMY_DATABASE_URL = "sqlite:///./transelo_events.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 1. MODELO DE EVENTO (Ej: Mis 15 Años de Lucía)
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    host_name = Column(String) # Nombre de la Quinceañera o Novios
    event_type = Column(String) # 'quince', 'boda', 'futbol'
    event_date = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)

# 2. MODELO DE INVITADO
class Guest(Base):
    __tablename__ = "guests"
    id = Column(String, primary_key=True, index=True) # ID único (para el QR)
    name = Column(String)
    table_number = Column(String)
    special_message = Column(String, nullable=True) # Ejemplo: "¡Hola abuela!"
    event_id = Column(Integer, ForeignKey("events.id"))

# Crear tablas
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
