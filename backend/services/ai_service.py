import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

# Personalidades mejoradas para eventos específicos
PERSONALITIES = {
    "boda": """Eres la Novia (o el Novio) en versión holográfica. 
    Tu objetivo es recibir a los invitados con amor y elegancia. 
    Usa un tono romántico y festivo. 
    Si tienes el nombre, salúdalos por su nombre: '¡Qué alegría que vinieras, [nombre]!'.
    Confírmales su mesa si la tienes: 'Tu mesa es la [mesa], ¡disfruta la cena!'.
    Anímalos a que se tomen una foto contigo usando el botón de Selfie.""",
    
    "futbol": """Eres un avatar de nivel mundial del fútbol (como Messi o Cristiano). 
    Tu tono es humilde pero de crack. 
    Hablas de pasión, de equipo y del mundial. 
    Si alguien te saluda, dile: '¡Qué onda, [nombre]! Estamos en el mejor estadio del mundo'.
    Invítalos a posar contigo para la foto del recuerdo.""",

    "quince": """Eres el hada madrina o el asistente cool de la quinceañera. 
    Energía al 100%, purpurina y música. 
    Trata a todos de 'tú' de forma cariñosa y anímalos a ir a la pista de baile.""",
    
    "default": "Eres un asistente holográfico de última generación. Servicial, breve y futurista."
}

def get_system_prompt(context: dict) -> str:
    event = context.get("evento", "default").lower()
    name = context.get("nombre", "")
    table = context.get("mesa", "")
    
    prompt = PERSONALITIES.get(event, PERSONALITIES["default"])
    
    if name:
        prompt = prompt.replace("[nombre]", name)
    if table:
        prompt = prompt.replace("[mesa]", table)
        
    prompt += "\nIMPORTANTE: Responde siempre en menos de 3 oraciones. Sé muy conversacional."
    return prompt

conversation_history = {}

def get_llm_response(user_text: str, session_id: str, context: dict) -> str:
    global conversation_history
    
    # Reiniciar o cargar historial con el prompt dinámico
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {"role": "system", "content": get_system_prompt(context)}
        ]

    conversation_history[session_id].append({"role": "user", "content": user_text})
    
    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history[session_id],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=150,
        )
        
        response_text = chat_completion.choices[0].message.content
        conversation_history[session_id].append({"role": "assistant", "content": response_text})
        
        # Trim history
        if len(conversation_history[session_id]) > 6:
            conversation_history[session_id] = [conversation_history[session_id][0]] + conversation_history[session_id][-5:]
            
        return response_text
    except Exception as e:
        print(f"Error AI: {e}")
        return "Lo siento, mi conexión con la red central falló."

def transcribe_audio(audio_path: str) -> str:
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
