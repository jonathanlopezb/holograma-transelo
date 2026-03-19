import os
import json
import base64
import tempfile
import shutil
import uuid
import requests
import datetime
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

# Importar arquitectura de datos y AI
try:
    from database import get_db, init_db, Guest, Event
    from services.ai_service import transcribe_audio, get_llm_response
    from services.tts_service import generate_speech
except ImportError:
    from .database import get_db, init_db, Guest, Event
    from .services.ai_service import transcribe_audio, get_llm_response
    from .services.tts_service import generate_speech

app = FastAPI()

# Directorio para Avatares y Feed Social
AVATAR_DIR = "static/avatars"
SOCIAL_DIR = "static/social"
os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(SOCIAL_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicializar DB
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FEED SOCIAL EN VIVO (PARA PANTALLA GIGANTE) ---
live_feed = [] # In-memory feed de los últimos eventos

@app.get("/api/social/feed")
async def get_social_feed():
    """Retorna los últimos eventos para el Muro Social"""
    return live_feed[-10:] # Últimos 10

# --- AVATAR FACTORY & BLOB ---
BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

async def upload_to_vercel_blob(file_content, filename):
    if not BLOB_TOKEN:
        local_path = f"static/avatars/{filename}"
        with open(local_path, "wb") as f: f.write(file_content)
        return f"/static/avatars/{filename}"
    url = f"https://blob.vercel-storage.com/{filename}"
    headers = {"Authorization": f"Bearer {BLOB_TOKEN}", "x-api-version": "2023-01-01"}
    response = requests.put(url, data=file_content, headers=headers)
    return response.json().get("url")

@app.post("/api/admin/upload-avatar")
async def upload_avatar(selfie: UploadFile = File(...), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.active == True).first()
    if not event: raise HTTPException(status_code=400, detail="Configura el evento")
    selfie_content = await selfie.read()
    filename = f"avatar_{event.id}.jpg"
    cloud_url = await upload_to_vercel_blob(selfie_content, filename)
    return {"status": "success", "url": cloud_url}

# --- ADMIN API (PARA NEON POSTGRES) ---

@app.post("/api/admin/setup-event")
async def setup_event(host_name: str, event_type: str, db: Session = Depends(get_db)):
    db.query(Event).update({Event.active: False})
    new_event = Event(host_name=host_name, event_type=event_type, active=True)
    db.add(new_event)
    db.commit()
    return {"status": "success", "event_id": new_event.id}

@app.get("/api/admin/guests")
async def list_guests(db: Session = Depends(get_db)):
    active_event = db.query(Event).filter(Event.active == True).first()
    if not active_event: return []
    return db.query(Guest).filter(Guest.event_id == active_event.id).all()

@app.post("/api/admin/guests")
async def add_guest(name: str, table: str, db: Session = Depends(get_db)):
    active_event = db.query(Event).filter(Event.active == True).first()
    if not active_event: raise HTTPException(status_code=400)
    qr_id = str(uuid.uuid4())[:8]
    new_guest = Guest(id=qr_id, name=name, table_number=table, event_id=active_event.id)
    db.add(new_guest)
    db.commit()
    return {"status": "success", "qr_id": qr_id}

# --- TOTEM API ---

@app.get("/api/guest/{qr_id}")
async def get_guest_info(qr_id: str, db: Session = Depends(get_db)):
    guest = db.query(Guest).filter(Guest.id == qr_id).first()
    if not guest: raise HTTPException(status_code=404)
    event = db.query(Event).filter(Event.id == guest.event_id).first()
    
    # Notificar al Feed Social!
    live_feed.append({
        "type": "welcome",
        "name": guest.name,
        "host": event.host_name,
        "time": datetime.datetime.now().strftime("%H:%M")
    })
    
    return {"name": guest.name, "table": guest.table_number, "event_host": event.host_name, "event_type": event.event_type}

@app.post("/api/chat")
async def chat_api(audio: Optional[UploadFile] = File(None), text_trigger: Optional[str] = Form(None), session_id: str = Form("demo"), context: str = Form("{}")):
    try:
        parsed_context = json.loads(context)
        user_input = text_trigger
        if audio and not user_input:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                shutil.copyfileobj(audio.file, temp_file)
                temp_path = temp_file.name
            user_input = transcribe_audio(temp_path)
            os.remove(temp_path)
        
        ai_response = get_llm_response(user_input, session_id, parsed_context)
        tts_audio_path = await generate_speech(ai_response)
        with open(tts_audio_path, "rb") as f: audio_data = base64.b64encode(f.read()).decode('utf-8')
        os.remove(tts_audio_path)
        return {"type": "success", "response": ai_response, "audio": audio_data}
    except Exception as e: return JSONResponse({"type": "error", "content": str(e)}, status_code=500)
