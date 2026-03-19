import os
import json
import base64
import tempfile
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Importar servicios
try:
    from services.ai_service import transcribe_audio, get_llm_response
    from services.tts_service import generate_speech
except ImportError:
    # Ajuste para rutas en Vercel si es necesario
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
    return {"status": "ok", "service": "Proto Hologram AI"}

@app.post("/api/chat")
async def chat_endpoint(
    audio: UploadFile = File(...),
    session_id: str = Form("default_session"),
    context: str = Form("{}")
):
    """
    Endpoint POST (Vercel Ready) para procesar el audio del holograma.
    """
    try:
        # 1. Parsear el contexto enviado por el QR o URL
        parsed_context = json.loads(context)
        
        # 2. Guardar el audio temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            shutil.copyfileobj(audio.file, temp_audio)
            temp_audio_path = temp_audio.name

        # 3. Escuchar (Speech-to-Text)
        text = transcribe_audio(temp_audio_path)
        os.remove(temp_audio_path)

        if not text or text.strip() == "":
            return JSONResponse({"type": "error", "content": "No entendí lo que dijiste."})

        # 4. Pensar (LLM con contexto de evento)
        response_text = get_llm_response(text, session_id, parsed_context)

        # 5. Hablar (Text-to-Speech)
        response_audio_path = await generate_speech(response_text)

        # 6. Codificar y Enviar (Base64 para compatibilidad total)
        with open(response_audio_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        os.remove(response_audio_path)

        return {
            "type": "success",
            "user_text": text,
            "response_text": response_text,
            "audio": audio_base64
        }

    except Exception as e:
        print(f"❌ Error API: {e}")
        return JSONResponse({"type": "error", "content": str(e)}, status_code=500)
