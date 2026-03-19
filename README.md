# Proto Hologram MVP

¡Bienvenido al código fuente de tu clon de Proto Hologram! 🚀

Este proyecto está dividido en dos partes principales para mantener la flexibilidad y el rendimiento: el **Frontend** (interfaz de usuario holográfica) y el **Backend** (motor conversacional de inteligencia artificial).

## 1. Configuración del Backend (El Cerebro)

El backend está construido con Python y FastAPI. Utiliza WebSockets para recibir tu audio en tiempo real, Groq (Whisper + Llama 3) para procesarlo ultra rápido, y Edge-TTS para generar una voz realista y natural de forma gratuita.

### Instrucciones para correr el Backend localmente:

1. Abre una terminal y navega a la carpeta del backend:
   ```bash
   cd e:\Sites\protoHologram\backend
   ```
2. (Recomendado) Crea un entorno virtual:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. **IMPORTANTE:** Configura tu API Key:
   - Renombra el archivo `e:\Sites\protoHologram\backend\.env.example` a `.env`
   - Abre el archivo `.env` y pega tu clave API de Groq (puedes sacarla gratis desde [console.groq.com](https://console.groq.com/keys)).
5. Inicia el servidor:
   ```bash
   uvicorn main:app --reload
   ```
   Verás un mensaje indicando que el servidor está corriendo en `ws://localhost:8000/ws`.

---

## 2. Configuración del Frontend (El Holograma)

El frontend es un diseño ultra realista hecho en HTML/CSS/JS puro, optimizado para correr a pantalla completa.

### Instrucciones para correr el Frontend:

1. El frontend no usa frameworks complejos (como React o Next.js) para asegurar la máxima fluidez del video holográfico. 
2. Solo necesitas abrir el archivo `e:\Sites\protoHologram\frontend\index.html` en tu navegador de preferencia (recomendado Chrome o Edge).
   - Alternativamente, puedes usar una extensión como "Live Server" en VSCode.
3. Para la mejor experiencia visual: presiona `F11` en tu navegador para ponerlo en pantalla completa.
4. Asegúrate de dar permisos de micrófono al navegador cuando la aplicación te lo pida al intentar hablar.

## ¿Cómo interactuar?

1. Con el backend corriendo y el frontend abierto, verás en la interfaz (esquina superior izquierda) que el `LINK_STATUS` dice **ONLINE**.
2. Mantén presionado el botón que dice **"🎙️ SOSTÉN PARA HABLAR"** y habla de forma natural.
3. Suelta el botón. Verás en el HUD cómo el sistema procesa tu voz y enseguida escucharás la respuesta del avatar de forma fluida.

---

> **Nota sobre el Avatar:** En `index.html` hay una etiqueta `<video id="avatar-video">`. Para hacer que se vea como un verdadero Proto, graba un video tuyo o de alguien más con fondo verde, quítale el fondo usando cualquier herramienta online gratuita (como Unscreen o CapCut) y expórtalo con fondo negro o transparente. Pon la ruta de ese video en el atributo `src` de la etiqueta video. Mientras tanto, verás una silueta brillante que sirve como prueba térmica conceptual.
