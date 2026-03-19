import edge_tts
import tempfile
import os
import asyncio

async def generate_speech(text: str, voice: str = "es-ES-AlvaroNeural") -> str:
    """
    Generates speech using Edge-TTS and saves it to a temporary file.
    Returns the path to the temporary audio file.
    """
    communicate = edge_tts.Communicate(text, voice)
    
    # Create a temporary file to store the audio
    fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    
    await communicate.save(temp_path)
    return temp_path
