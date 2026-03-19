// 🌌 TRANSELO EVENTOS ENGINE 2.0
// Libraries: GSAP, Canvas API, Web Media API

const API_ENDPOINT = '/api/chat'; 
const micBtn = document.getElementById('mic-btn');
const selfieBtn = document.getElementById('selfie-btn');
const transcriptBox = document.getElementById('transcript-box');
const vCanvas = document.getElementById('visualizer-canvas');
const vCtx = vCanvas.getContext('2d');
const avatarVideo = document.getElementById('avatar-video');
const userCamera = document.getElementById('user-camera');

// Context State
let appState = {
    isRecording: false,
    audioCtx: null,
    analyser: null,
    dataArray: null,
    context: {},
    mediaRecorder: null,
    audioChunks: [],
    audioElement: null
};

// 1. INITIALIZATION & QR PARSING
function init() {
    const params = new URLSearchParams(window.location.search);
    appState.context = {
        nombre: params.get('nombre') || 'Invitado Especial',
        mesa: params.get('mesa') || 'N/A',
        evento: params.get('evento') || 'default'
    };

    // Update UI Labels
    document.getElementById('guest-name').textContent = appState.context.nombre.toUpperCase();
    document.getElementById('guest-table').textContent = appState.context.mesa;
    document.getElementById('event-type').textContent = appState.context.evento.toUpperCase();
    document.getElementById('session-id').textContent = Math.random().toString(36).substr(2, 6).toUpperCase();

    // Set Theme
    document.body.className = `theme-${appState.context.evento}`;

    // Reveal UI with GSAP
    gsap.to(".guest-card", { opacity: 1, x: 0, duration: 1, delay: 0.5 });
    gsap.to(".transcript-container", { opacity: 1, y: 0, duration: 1, delay: 0.8 });
    
    // Setup Particles (Background decor)
    if (window.particlesJS) {
        initParticles(appState.context.evento);
    }

    // Startup Webcam
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => { userCamera.srcObject = stream; })
        .catch(e => console.error("Camera access denied:", e));
}

// 2. PRO AUDIO VISUALIZER
function setupVisualizer(sourceNode) {
    if (!appState.audioCtx) {
        appState.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        appState.analyser = appState.audioCtx.createAnalyser();
        appState.analyser.fftSize = 128;
        appState.dataArray = new Uint8Array(appState.analyser.frequencyBinCount);
    }
    
    sourceNode.connect(appState.analyser);
    if (!(sourceNode instanceof MediaStreamAudioSourceNode)) {
        appState.analyser.connect(appState.audioCtx.destination);
    }
    
    requestAnimationFrame(renderVisualizer);
}

function renderVisualizer() {
    if (!appState.analyser) return;
    requestAnimationFrame(renderVisualizer);
    
    appState.analyser.getByteFrequencyData(appState.dataArray);
    
    const width = vCanvas.width;
    const height = vCanvas.height;
    vCtx.clearRect(0, 0, width, height);
    
    const barWidth = (width / appState.dataArray.length) * 2;
    let x = 0;
    
    for (let i = 0; i < appState.dataArray.length; i++) {
        const barHeight = (appState.dataArray[i] / 255) * height;
        vCtx.fillStyle = getComputedStyle(document.body).getPropertyValue('--primary');
        vCtx.fillRect(x, height - barHeight, barWidth - 1, barHeight);
        x += barWidth;
    }
}

// 3. VOICE INTERACTION (FETCH / API)
async function toggleMic() {
    if (!appState.isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            appState.mediaRecorder = new MediaRecorder(stream);
            appState.audioChunks = [];
            
            const micSource = appState.audioCtx?.createMediaStreamSource(stream) || 
                             (new (window.AudioContext||window.webkitAudioContext)()).createMediaStreamSource(stream);
            setupVisualizer(micSource);

            appState.mediaRecorder.ondataavailable = e => appState.audioChunks.push(e.data);
            appState.mediaRecorder.onstop = processVoice;
            appState.mediaRecorder.start();
            
            appState.isRecording = true;
            micBtn.classList.add('active');
            transcriptBox.textContent = "📡 ESCUCHANDO FRECUENCIAS...";
        } catch (e) { alert("Acceso al micrófono denegado."); }
    } else {
        appState.mediaRecorder.stop();
        appState.isRecording = false;
        micBtn.classList.remove('active');
        transcriptBox.textContent = "⚙️ PROCESANDO EN NUBE...";
    }
}

async function processVoice() {
    const audioBlob = new Blob(appState.audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('context', JSON.stringify(appState.context));

    try {
        const res = await fetch(API_ENDPOINT, { method: 'POST', body: formData });
        const data = await res.json();

        if (data.type === 'success') {
            typeWriter(data.response);
            playAudio(data.audio);
        } else {
            transcriptBox.textContent = "❌ ERROR EN LA MATRIZ";
        }
    } catch (e) {
        transcriptBox.textContent = "❌ ERROR DE CONEXIÓN";
    }
}

function playAudio(base64) {
    const blob = b64toBlob(base64, 'audio/mp3');
    const url = URL.createObjectURL(blob);
    
    if (appState.audioElement) appState.audioElement.pause();
    
    appState.audioElement = new Audio(url);
    const audioSource = appState.audioCtx.createMediaElementSource(appState.audioElement);
    setupVisualizer(audioSource);
    appState.audioElement.play();
}

function typeWriter(text) {
    transcriptBox.innerHTML = '';
    let i = 0;
    const interval = setInterval(() => {
        if (i < text.length) {
            transcriptBox.innerHTML += text.charAt(i);
            i++;
        } else { clearInterval(interval); }
    }, 25);
}

// 4. SELFIE MODULE
function takeSelfie() {
    const flash = document.getElementById('camera-flash');
    const composer = document.getElementById('selfie-composer');
    const ctx = composer.getContext('2d');
    
    // UI Feedback
    gsap.to(flash, { opacity: 1, duration: 0.1, yoyo: true, repeat: 1 });
    document.body.classList.add('camera-active');
    
    setTimeout(() => {
        composer.width = 1080;
        composer.height = 1350; // Format IG

        // Merge user camera + hologram
        ctx.drawImage(userCamera, 0, 0, 1080, 1350);
        
        // Overlay Hologram (video current frame)
        ctx.globalAlpha = 0.8;
        ctx.drawImage(avatarVideo, 100, 200, 800, 1000);
        
        // Branding
        ctx.globalAlpha = 1;
        ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--primary');
        ctx.font = "bold 50px Orbitron";
        ctx.fillText("TRANSELO EVENTOS", 50, 1300);
        ctx.font = "30px Share Tech Mono";
        ctx.fillText("SELFIE HOLOGRÁFICA | " + appState.context.evento.toUpperCase(), 50, 1250);

        // Download
        const link = document.createElement('a');
        link.download = `Selfie_Transelo_${Date.now()}.png`;
        link.href = composer.toDataURL();
        link.click();
        
        document.body.classList.remove('camera-active');
    }, 500);
}

// Utils
function b64toBlob(b64Data, contentType) {
    const byteCharacters = atob(b64Data);
    const byteArrays = [];
    for (let offset = 0; offset < byteCharacters.length; offset += 512) {
        const slice = byteCharacters.slice(offset, offset + 512);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) { byteNumbers[i] = slice.charCodeAt(i); }
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }
    return new Blob(byteArrays, {type: contentType});
}

function initParticles(theme) {
    let color = "#00f2ff";
    if (theme === 'boda') color = "#ffd700";
    if (theme.includes('mundial')) color = "#39ff14";

    particlesJS("particles-js", {
        "particles": {
            "number": { "value": 80 },
            "color": { "value": color },
            "shape": { "type": "circle" },
            "opacity": { "value": 0.5 },
            "size": { "value": 3 },
            "line_linked": { "enable": true, "distance": 150, "color": color, "opacity": 0.4, "width": 1 }
        },
        "interactivity": { "events": { "onhover": { "enable": true, "mode": "repulse" } } }
    });
}

// LISTENERS
micBtn.addEventListener('mousedown', toggleMic);
micBtn.addEventListener('mouseup', toggleMic);
selfieBtn.addEventListener('click', takeSelfie);
window.addEventListener('load', init);
