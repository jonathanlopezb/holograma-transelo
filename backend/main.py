import os
import json
import base64
import tempfile
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Adaptación de rutas para Vercel o Local
try:
    from services.ai_service import transcribe_audio, get_llm_response
    from services.tts_service import generate_speech
except ImportError:
    from .services.ai_service import transcribe_audio, get_llm_response
    from .services.tts_service import generate_speech

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Transelo Hologram AI 2.0"}

@app.post("/api/chat")
async def chat_api(
    audio: UploadFile = File(...),
    session_id: str = Form("demo_guest"),
    context: str = Form("{}")
):
    """
    API Unificada (Vercel-Ready)
    Recibe audio -> Transcribe -> Piensa -> Habla -> Retorna JSON con Audio en Base64.
    """
    try:
        # 1. Analizar contexto (Nombre, Mesa, Evento)
        parsed_context = json.loads(context)
        
        # 2. Guardar audio temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            shutil.copyfileobj(audio.file, temp_file)
            temp_path = temp_file.name

        # 3. Escuchar (Speech-to-Text)
        text = transcribe_audio(temp_path)
        os.remove(temp_path)

        if not text or text.strip() == "":
            return JSONResponse({"type": "error", "content": "Audio vacío."})

        # 4. Pensar (LLM con contexto dinámico)
        ai_response = get_llm_response(text, session_id, parsed_context)

        # 5. Hablar (Text-to-Speech)
        tts_audio_path = await generate_speech(ai_response)

        # 6. Codificar a Base64 para enviar al navegador
        with open(tts_audio_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        os.remove(tts_audio_path)

        return {
            "type": "success",
            "transcription": text,
            "response": ai_response,
            "audio": audio_data
        }

    except Exception as e:
        print(f"API Error: {e}")
        return JSONResponse({"type": "error", "content": str(e)}, status_code=500)
