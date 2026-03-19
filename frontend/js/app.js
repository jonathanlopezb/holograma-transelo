// 🧪 Proto Hologram 2.0 - Experience Logic
const API_URL = '/api/chat'; // Cambia a http://localhost:8000/api/chat si pruebas local sin Vercel
const micBtn = document.getElementById('mic-btn');
const selfieBtn = document.getElementById('selfie-btn');
const transcriptBox = document.getElementById('transcript-box');
const userLabel = document.getElementById('user-label');
const eventLabel = document.getElementById('event-label');
const audioBars = document.querySelectorAll('.audio-wave .bar');
const avatarVideo = document.getElementById('avatar-video');
const webcamFeed = document.getElementById('webcam-feed');

// State
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let audioCtx, analyser, dataArray;
let context = {};

// 1. Inicialización y Lectura de Parámetros (QR Magic)
function initContext() {
    const params = new URLSearchParams(window.location.search);
    context = {
        nombre: params.get('nombre') || 'Invitado Especial',
        mesa: params.get('mesa') || 'VIP',
        evento: params.get('evento') || 'default'
    };

    // Actualizar HUD
    userLabel.textContent = context.nombre.toUpperCase();
    eventLabel.textContent = context.evento.toUpperCase();

    // Aplicar Tema Visual
    if (context.evento === 'boda') document.body.className = 'theme-boda';
    if (context.evento === 'futbol') document.body.className = 'theme-futbol';

    // Iniciar Webcam para Selfie (silenciosamente)
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => { webcamFeed.srcObject = stream; })
        .catch(e => console.error("Sin acceso a cámara:", e));
}

// 2. Visualizador de Audio Adaptativo
function setupVisualizer(streamOrElement) {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        dataArray = new Uint8Array(analyser.frequencyBinCount);
    }
    
    try {
        const source = (streamOrElement instanceof MediaStream) 
            ? audioCtx.createMediaStreamSource(streamOrElement)
            : audioCtx.createMediaElementSource(streamOrElement);
        
        source.connect(analyser);
        if (!(streamOrElement instanceof MediaStream)) analyser.connect(audioCtx.destination);
        
        requestAnimationFrame(renderFrame);
    } catch(e) { console.warn("Visualizer link error (likely already connected)"); }
}

function renderFrame() {
    if (!analyser) return;
    requestAnimationFrame(renderFrame);
    analyser.getByteFrequencyData(dataArray);
    audioBars.forEach((bar, i) => {
        const height = (dataArray[i] / 255) * 30 + 2;
        bar.style.height = `${height}px`;
    });
}

// 3. Sistema de Captura de Voz (Push to Talk)
async function toggleRecording() {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        setupVisualizer(stream); // Activar barritas con la voz del usuario
        
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = sendAudioData;
        
        mediaRecorder.start();
        isRecording = true;
        transcriptBox.textContent = "[ ESCUCHANDO... ]";
    } else {
        mediaRecorder.stop();
        isRecording = false;
        transcriptBox.textContent = "[ PROCESANDO FRECUENCIAS... ]";
    }
}

// 4. Comunicación con la IA (Vercel-Ready)
async function sendAudioData() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('context', JSON.stringify(context));
    formData.append('session_id', 'user_session_1');

    try {
        const response = await fetch(API_URL, { method: 'POST', body: formData });
        const data = await response.json();

        if (data.type === 'success') {
            typeWriter(transcriptBox, data.response_text);
            playResponse(data.audio);
        } else {
            transcriptBox.textContent = "[ ERROR: REINTENTAR ]";
        }
    } catch (e) {
        console.error("Fetch error:", e);
        transcriptBox.textContent = "[ ERROR DE CONEXIÓN CON LA MATRIZ ]";
    }
}

function playResponse(base64Audio) {
    const audio = new Audio("data:audio/mp3;base64," + base64Audio);
    setupVisualizer(audio); // Activar barritas con la respuesta de la IA
    audio.play();
}

function typeWriter(element, text) {
    element.innerHTML = '';
    let i = 0;
    const interval = setInterval(() => {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
        } else { clearInterval(interval); }
    }, 30);
}

// 5. Módulo de Selfie "In-Event"
function takeSelfie() {
    const flash = document.getElementById('flash-overlay');
    const canvas = document.getElementById('screenshot-canvas');
    const captureZone = document.getElementById('capture-zone');
    
    // Efecto de Flash
    flash.classList.add('flash-active');
    setTimeout(() => flash.classList.remove('flash-active'), 800);

    // Captura básica (Canvas)
    const context = canvas.getContext('2d');
    canvas.width = 1080;
    canvas.height = 1920; // Formato vertical para redes sociales

    // 1. Pintar fondo de cámara
    context.drawImage(webcamFeed, 0, 0, canvas.width, canvas.height);
    
    // 2. Pintar Holograma (podemos añadir una marca de agua o logo del evento aquí)
    context.fillStyle = "rgba(0, 255, 255, 0.2)";
    context.font = "bold 40px Share Tech Mono";
    context.fillText("EVENTO: " + eventLabel.textContent, 50, canvas.height - 100);

    // Descargar/Imprimir
    const link = document.createElement('a');
    link.download = `Selfie_Hologram_${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
}

// Event Listeners
micBtn.addEventListener('mousedown', toggleRecording);
micBtn.addEventListener('mouseup', toggleRecording);
selfieBtn.addEventListener('click', takeSelfie);

// Init
initContext();
