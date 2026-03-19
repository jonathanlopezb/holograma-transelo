import os
import json
import base64
import tempfile
import shutil
import uuid
import requests
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

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

# Inicializar DB
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌐 LÓGICA DE VERCEL BLOB (SUBIR ARCHIVOS A LA NUBE)
BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

async def upload_to_vercel_blob(file_content, filename):
    """Sube un archivo a Vercel Blob usando su API de red"""
    if not BLOB_TOKEN:
        # Fallback local si no hay token
        os.makedirs("static/avatars", exist_ok=True)
        local_path = f"static/avatars/{filename}"
        with open(local_path, "wb") as f:
            f.write(file_content)
        return f"/static/avatars/{filename}"

    # API de Vercel Blob (PUT)
    url = f"https://blob.vercel-storage.com/{filename}"
    headers = {
        "Authorization": f"Bearer {BLOB_TOKEN}",
        "x-api-version": "2023-01-01"
    }
    response = requests.put(url, data=file_content, headers=headers)
    if response.status_code == 200:
        return response.json().get("url")
    else:
        raise Exception(f"Blob upload failed: {response.text}")

# --- AVATAR FACTORY (CON VERCEL BLOB) ---

@app.post("/api/admin/upload-avatar")
async def upload_avatar(
    selfie: UploadFile = File(...),
    voice_sample: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(Event.active == True).first()
    if not event: raise HTTPException(status_code=400, detail="Configura el evento")

    # 1. Subir Selfie a Vercel Blob
    selfie_content = await selfie.read()
    filename = f"avatar_{event.id}_{uuid.uuid4().hex[:6]}.jpg"
    cloud_url = await upload_to_vercel_blob(selfie_content, filename)
    
    # 2. Guardar URL en el host del evento (opcionalmente podrías tener un campo avatar_url en Event)
    # Por ahora la devolvemos para que el panel admin la confirme
    return {
        "status": "success",
        "message": "Avatar guardado en la nube (Vercel Blob)",
        "url": cloud_url
    }

@app.get("/api/event/current-avatar")
async def get_current_avatar(db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.active == True).first()
    if not event: return {"video_url": "assets/default_avatar.mp4"}
    
    # Aquí podríamos buscar en la base de datos la URL guardada del avatar
    # Por ahora, devolvemos un placeholder o la configuración activa
    return {"video_url": "/static/avatars/default.mp4", "host_name": event.host_name}

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
    return db.query(Guest).all()

@app.post("/api/admin/guests")
async def add_guest(name: str, table: str, special_msg: Optional[str] = None, db: Session = Depends(get_db)):
    active_event = db.query(Event).filter(Event.active == True).first()
    qr_id = str(uuid.uuid4())[:8]
    new_guest = Guest(id=qr_id, name=name, table_number=table, special_message=special_msg, event_id=active_event.id)
    db.add(new_guest)
    db.commit()
    return {"status": "success", "qr_id": qr_id}

@app.get("/api/guest/{qr_id}")
async def get_guest_info(qr_id: str, db: Session = Depends(get_db)):
    guest = db.query(Guest).filter(Guest.id == qr_id).first()
    if not guest: raise HTTPException(status_code=404)
    event = db.query(Event).filter(Event.id == guest.event_id).first()
    return {"name": guest.name, "table": guest.table_number, "special_msg": guest.special_message, "event_host": event.host_name, "event_type": event.event_type}

# --- CHAT ENGINE VERCEL ---

@app.post("/api/chat")
async def chat_api(
    audio: Optional[UploadFile] = File(None),
    text_trigger: Optional[str] = Form(None),
    session_id: str = Form("demo"),
    context: str = Form("{}")
):
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
        with open(tts_audio_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        os.remove(tts_audio_path)
        return {"type": "success", "response": ai_response, "audio": audio_data}
    except Exception as e:
        return JSONResponse({"type": "error", "content": str(e)}, status_code=500)
