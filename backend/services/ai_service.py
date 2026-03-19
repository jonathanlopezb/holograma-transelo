import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# CONFIGURACIÓN DE PERSONALIDADES PARA TRANSELO EVENTOS
EVENT_PROMPTS = {
    "boda": """Eres el Anfitrión Holográfico de 'Transelo Eventos'. 
    Tu tono es sofisticado, cálido y elegante. 
    Dale la bienvenida a los invitados con mucha emoción. 
    Su nombre es [NOMBRE] y su mesa asignada es la [MESA]. 
    Diles que es un honor tenerlos en esta unión tan especial. 
    Invítalos a disfrutar de la cena y a tomarse una selfie contigo usando el botón de la derecha.""",
    
    "quince": """Eres Isabella, una joven de 15 años radiante y emocionada en tu fiesta de gala. 
    Tu tono es dulce, elegante y muy acogedor. 
    Cuando recibas a un invitado, agradécele con mucha emoción por venir. 
    Dile que su mesa es la [MESA] y que esta noche será inolvidable para ambos ✨💖.""",
    
    "mundial_messi": """¡Hola! Soy Leo Messi en modo holográfico de 'Transelo Eventos'. 
    Hablo con humildad y pasión por el fútbol. 
    Saluda a [NOMBRE] y dile que estamos en el mejor estadio. 
    Dile: 'Es un placer tenerte aquí, vení y sacate una foto conmigo'. 
    Menciona que estamos festejando como campeones.""",

    "mundial_cr7": """¡Siuuu! Soy Cristiano Ronaldo, el mejor, en el holograma de 'Transelo Eventos'. 
    Tono motivador, exigente y de éxito. 
    Saluda a [NOMBRE] y dile que para ganar hay que trabajar duro. 
    '¡Vení a sacarte una foto con el Bicho!'. """,

    "default": "Eres el Asistente Holográfico de 'Transelo Eventos'. Eres futurista, servicial y amable."
}

def get_system_prompt(context: dict) -> str:
    event_type = context.get("evento", "default").lower()
    name = context.get("nombre", "Invitado Especial")
    table = context.get("mesa", "VIP")
    
    prompt = EVENT_PROMPTS.get(event_type, EVENT_PROMPTS["default"])
    
    # Reemplazo de variables dinámicas
    prompt = prompt.replace("[NOMBRE]", name).replace("[MESA]", table)
    
    prompt += "\n\nREGLA CRÍTICA: Responde siempre en máximo 2 o 3 oraciones cortas. Tono muy conversacional."
    return prompt

# Historial de conversación liviano
history = {}

def get_llm_response(user_text: str, session_id: str, context: dict) -> str:
    global history
    
    # Reiniciar historial con el prompt contextual si es sesión nueva
    if session_id not in history:
        history[session_id] = [
            {"role": "system", "content": get_system_prompt(context)}
        ]

    history[session_id].append({"role": "user", "content": user_text})
    
    try:
        completion = client.chat.completions.create(
            messages=history[session_id],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=150,
        )
        
        response = completion.choices[0].message.content
        history[session_id].append({"role": "assistant", "content": response})
        
        # Mantener historial corto para evitar latencia
        if len(history[session_id]) > 6:
            history[session_id] = [history[session_id][0]] + history[session_id][-5:]
            
        return response
    except Exception as e:
        print(f"Error AI: {e}")
        return "Disculpa, la señal holográfica está inestable. ¿Puedes repetir?"

def transcribe_audio(audio_path: str) -> str:
    """Usa Groq Whisper para transcripción rápida."""
    try:
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                language="es",
            )
            return transcription.text
    except Exception as e:
        print(f"Error STT: {e}")
        return ""
