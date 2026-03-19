import os
import sys
import json
import base64
import tempfile
import shutil
import uuid
import datetime
import requests
from typing import Optional, List

# 🔧 FIX DE RUTAS PARA VERCEL
# Forzamos que la carpeta actual esté en el PATH
current_dir = os.path.dirname(os.path.realpath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

# Importar arquitectura de datos y AI con rutas robustas
try:
    import database
    from services import ai_service, tts_service
except ImportError:
    import backend.database as database
    from backend.services import ai_service, tts_service

app = FastAPI()

# Directorio para Avatares y Feed Social
AVATAR_DIR = os.path.join(tempfile.gettempdir(), "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)
# Solo montamos static si estamos en local, en Vercel usamos Blob
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicializar DB
database.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌐 LÓGICA DE VERCEL BLOB
BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

async def upload_to_vercel_blob(file_content, filename):
    if not BLOB_TOKEN:
        local_path = os.path.join(AVATAR_DIR, filename)
        with open(local_path, "wb") as f: f.write(file_content)
        return f"/static/avatars/{filename}"
    url = f"https://blob.vercel-storage.com/{filename}"
    headers = {"Authorization": f"Bearer {BLOB_TOKEN}", "x-api-version": "2023-01-01"}
    response = requests.put(url, data=file_content, headers=headers)
    return response.json().get("url")

# --- AVATAR FACTORY ---

@app.post("/api/admin/upload-avatar")
async def upload_avatar(selfie: UploadFile = File(...), db: Session = Depends(database.get_db)):
    event = db.query(database.Event).filter(database.Event.active == True).first()
    if not event: raise HTTPException(status_code=400, detail="Configura el evento")
    selfie_content = await selfie.read()
    filename = f"avatar_{event.id}.jpg"
    cloud_url = await upload_to_vercel_blob(selfie_content, filename)
    return {"status": "success", "url": cloud_url}

@app.get("/api/event/current-avatar")
async def get_current_avatar(db: Session = Depends(database.get_db)):
    event = db.query(database.Event).filter(database.Event.active == True).first()
    if not event: return {"video_url": "assets/default_avatar.mp4"}
    return {"video_url": "/static/avatars/default.mp4", "host_name": event.host_name}

# --- ADMIN API ---

@app.post("/api/admin/setup-event")
async def setup_event(host_name: str, event_type: str, db: Session = Depends(database.get_db)):
    db.query(database.Event).update({database.Event.active: False})
    new_event = database.Event(host_name=host_name, event_type=event_type, active=True)
    db.add(new_event)
    db.commit()
    return {"status": "success", "event_id": new_event.id}

@app.get("/api/admin/guests")
async def list_guests(db: Session = Depends(database.get_db)):
    active_event = db.query(database.Event).filter(database.Event.active == True).first()
    if not active_event: return []
    return db.query(database.Guest).filter(database.Guest.event_id == active_event.id).all()

@app.post("/api/admin/guests")
async def add_guest(name: str, table: str, db: Session = Depends(database.get_db)):
    active_event = db.query(database.Event).filter(database.Event.active == True).first()
    if not active_event: raise HTTPException(status_code=400)
    qr_id = str(uuid.uuid4())[:8]
    new_guest = database.Guest(id=qr_id, name=name, table_number=table, event_id=active_event.id)
    db.add(new_guest)
    db.commit()
    return {"status": "success", "qr_id": qr_id}

# --- CHAT ENGINE ---

@app.post("/api/chat")
async def chat_api(audio: Optional[UploadFile] = File(None), text_trigger: Optional[str] = Form(None), session_id: str = Form("demo"), context: str = Form("{}")):
    try:
        parsed_context = json.loads(context)
        user_input = text_trigger
        if audio and not user_input:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                shutil.copyfileobj(audio.file, temp_file)
                temp_path = temp_file.name
            user_input = ai_service.transcribe_audio(temp_path)
            os.remove(temp_path)
        
        ai_response = ai_service.get_llm_response(user_input, session_id, parsed_context)
        tts_audio_path = await tts_service.generate_speech(ai_response)
        with open(tts_audio_path, "rb") as f: audio_data = base64.b64encode(f.read()).decode('utf-8')
        os.remove(tts_audio_path)
        return {"type": "success", "response": ai_response, "audio": audio_data}
    except Exception as e: return JSONResponse({"type": "error", "content": str(e)}, status_code=500)
