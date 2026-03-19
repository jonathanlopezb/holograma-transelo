import os
import json
import base64
import tempfile
import shutil
import uuid
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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

# Directorio para Avatares Generados
AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)
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

# --- AVATAR FACTORY (LA MAGIA DE LA 15ÑERA) ---

@app.post("/api/admin/upload-avatar")
async def upload_avatar(
    selfie: UploadFile = File(...),
    voice_sample: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Recibe la Selfie y Voz de la Quinceañera.
    En producción: Aquí se llama a HeyGen/Replicate para generar el video.
    Para la DEMO: Guardamos los archivos y preparamos el sistema.
    """
    event = db.query(Event).filter(Event.active == True).first()
    if not event:
        raise HTTPException(status_code=400, detail="Configura el evento primero")

    # Guardar Selfie
    selfie_path = os.path.join(AVATAR_DIR, f"selfie_{event.id}.jpg")
    with open(selfie_path, "wb") as buffer:
        shutil.copyfileobj(selfie.file, buffer)

    # Simulación de Procesamiento IA
    # En un caso real, aquí iría el código de sincronización labial.
    # Por ahora, usamos el video de la selfie como marcador de posición.
    
    return {
        "status": "processing",
        "message": "IA está editando el video con tu cara y voz...",
        "preview_url": f"/static/avatars/selfie_{event.id}.jpg"
    }

@app.get("/api/event/current-avatar")
async def get_current_avatar(db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.active == True).first()
    if not event: return {"video_url": "assets/default_avatar.mp4"}
    
    avatar_file = f"selfie_{event.id}.jpg" # O .mp4 si ya se generó
    return {"video_url": f"/static/avatars/{avatar_file}", "host_name": event.host_name}

# --- ENDPOINTS ADMINISTRATIVOS ---

@app.post("/api/admin/setup-event")
async def setup_event(host_name: str, event_type: str, db: Session = Depends(get_db)):
    db.query(Event).update({Event.active: False})
    new_event = Event(host_name=host_name, event_type=event_type, active=True)
    db.add(new_event)
    db.commit()
    return {"status": "success", "event_id": new_event.id}

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

# --- CHAT ENGINE ---

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
