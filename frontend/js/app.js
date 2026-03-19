// 🌌 TRANSELO EVENTOS ENGINE 2.0 - CORE & SCANNER
// Libraries: GSAP, Canvas API, Web Media API, Html5Qrcode

const API_ENDPOINT = '/api/chat'; 
const micBtn = document.getElementById('mic-btn');
const selfieBtn = document.getElementById('selfie-btn');
const transcriptBox = document.getElementById('transcript-box');
const vCanvas = document.getElementById('visualizer-canvas');
const vCtx = vCanvas.getContext('2d');
const avatarVideo = document.getElementById('avatar-video');
const userCamera = document.getElementById('user-camera');

// State
let appState = {
    isRecording: false,
    audioCtx: null,
    analyser: null,
    dataArray: null,
    context: {},
    mediaRecorder: null,
    audioChunks: [],
    audioElement: null,
    isScannerActive: false,
    isWelcomeTriggered: false
};

// 1. INITIALIZATION
function init() {
    const params = new URLSearchParams(window.location.search);
    appState.context = {
        nombre: params.get('nombre') || 'Invitado Especial',
        mesa: params.get('mesa') || 'N/A',
        evento: params.get('evento') || 'default'
    };

    updateUI();
    
    // Reveal UI
    gsap.to(".guest-card", { opacity: 1, x: 0, duration: 1, delay: 0.5 });
    gsap.to(".transcript-container", { opacity: 1, y: 0, duration: 1, delay: 0.8 });
    
    if (window.particlesJS) initParticles(appState.context.evento);

    // Startup Webcam & Scanner
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => { 
            userCamera.srcObject = stream;
            startQRScanner();
        })
        .catch(e => console.error("Camera access denied:", e));
}

function updateUI() {
    document.getElementById('guest-name').textContent = appState.context.nombre.toUpperCase();
    document.getElementById('guest-table').textContent = appState.context.mesa;
    document.getElementById('event-type').textContent = appState.context.evento.toUpperCase();
    document.getElementById('session-id').textContent = Math.random().toString(36).substr(2, 6).toUpperCase();
    document.body.className = `theme-${appState.context.evento}`;
}

// 2. AUTOMATIC QR SCANNER (EYE OF THE TOTEM)
function startQRScanner() {
    if (appState.isScannerActive) return;
    
    // Load script dynamically for performance
    const script = document.createElement('script');
    script.src = "https://unpkg.com/html5-qrcode";
    script.onload = () => {
        const html5QrCode = new Html5Qrcode("app-viewport"); // Scanner over the main viewport
        const config = { fps: 15, qrbox: { width: 300, height: 300 } };
        
        html5QrCode.start({ facingMode: "user" }, config, (decoded) => {
            if (!appState.isWelcomeTriggered && decoded.includes("evento=")) {
                appState.isWelcomeTriggered = true;
                handleQRWelcome(decoded);
            }
        });
        appState.isScannerActive = true;
    };
    document.head.appendChild(script);
}

async function handleQRWelcome(url) {
    const params = new URL(url).searchParams;
    appState.context = {
        nombre: params.get('nombre'),
        mesa: params.get('mesa'),
        evento: params.get('evento')
    };
    
    updateUI(); // Immediate change to specific theme
    
    // Special trigger: "Introduce yourself to the guest"
    const formData = new FormData();
    const prompt = `¡Bienvenido ${appState.context.nombre}! Qué alegría que estés en mis 15. Tu mesa es la ${appState.context.mesa}. Pasa y diviértete.`;
    
    formData.append('text_trigger', prompt);
    formData.append('context', JSON.stringify(appState.context));

    try {
        transcriptBox.textContent = `📡 ESCANEANDO IDENTIDAD... BIENVENIDO ${appState.context.nombre.toUpperCase()}`;
        const res = await fetch(API_ENDPOINT, { method: 'POST', body: formData });
        const data = await res.json();
        
        if (data.type === 'success') {
            typeWriter(data.response);
            playAudio(data.audio);
            // Reset for next guest in 15 seconds
            setTimeout(() => { appState.isWelcomeTriggered = false; }, 15000);
        }
    } catch(e) { console.error("Welcome trigger failed:", e); }
}

// 3. VOICE ENGINE
async function toggleMic() {
    if (!appState.isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            appState.mediaRecorder = new MediaRecorder(stream);
            appState.audioChunks = [];
            
            if(!appState.audioCtx) {
                appState.audioCtx = new (window.AudioContext||window.webkitAudioContext)();
            }
            const micSource = appState.audioCtx.createMediaStreamSource(stream);
            setupVisualizer(micSource);

            appState.mediaRecorder.ondataavailable = e => appState.audioChunks.push(e.data);
            appState.mediaRecorder.onstop = processVoice;
            appState.mediaRecorder.start();
            
            appState.isRecording = true;
            micBtn.classList.add('active');
            transcriptBox.textContent = "📡 ESCUCHANDO...";
        } catch (e) { alert("Mic required"); }
    } else {
        appState.mediaRecorder.stop();
        appState.isRecording = false;
        micBtn.classList.remove('active');
        transcriptBox.textContent = "⚙️ PENSANDO...";
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
        }
    } catch (e) { transcriptBox.textContent = "❌ ERROR"; }
}

// Audio visualizer and setup same as before but integrated
function setupVisualizer(sourceNode) {
    if (!appState.analyser) {
        appState.analyser = appState.audioCtx.createAnalyser();
        appState.analyser.fftSize = 64;
    }
    sourceNode.connect(appState.analyser);
    if (!(sourceNode instanceof MediaStreamAudioSourceNode)) appState.analyser.connect(appState.audioCtx.destination);
    renderVisualizer();
}

function renderVisualizer() {
    if (!appState.analyser) return;
    requestAnimationFrame(renderVisualizer);
    appState.dataArray = new Uint8Array(appState.analyser.frequencyBinCount);
    appState.analyser.getByteFrequencyData(appState.dataArray);
    
    vCtx.clearRect(0, 0, vCanvas.width, vCanvas.height);
    const barWidth = (vCanvas.width / appState.dataArray.length) * 2;
    let x = 0;
    for (let i = 0; i < appState.dataArray.length; i++) {
        const barHeight = (appState.dataArray[i] / 255) * vCanvas.height;
        vCtx.fillStyle = getComputedStyle(document.body).getPropertyValue('--primary');
        vCtx.fillRect(x, vCanvas.height - barHeight, barWidth - 1, barHeight);
        x += barWidth;
    }
}

function playAudio(base64) {
    const blob = b64toBlob(base64, 'audio/mp3');
    const url = URL.createObjectURL(blob);
    if (appState.audioElement) appState.audioElement.pause();
    appState.audioElement = new Audio(url);
    if (!appState.audioCtx) appState.audioCtx = new (window.AudioContext||window.webkitAudioContext)();
    const source = appState.audioCtx.createMediaElementSource(appState.audioElement);
    setupVisualizer(source);
    appState.audioElement.play();
}

function typeWriter(text) {
    transcriptBox.innerHTML = '';
    let i = 0;
    const interval = setInterval(() => {
        if (i < text.length) { transcriptBox.innerHTML += text.charAt(i); i++; }
        else { clearInterval(interval); }
    }, 25);
}

// 4. SELFIE
function takeSelfie() {
    const flash = document.getElementById('camera-flash');
    const composer = document.getElementById('selfie-composer');
    const ctx = composer.getContext('2d');
    gsap.to(flash, { opacity: 1, duration: 0.1, yoyo: true, repeat: 1 });
    document.body.classList.add('camera-active');
    
    setTimeout(() => {
        composer.width = 1080; composer.height = 1350;
        ctx.drawImage(userCamera, 0, 0, 1080, 1350);
        ctx.globalAlpha = 0.8;
        ctx.drawImage(avatarVideo, 100, 200, 800, 1000);
        ctx.globalAlpha = 1;
        ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--primary');
        ctx.font = "bold 50px Orbitron";
        ctx.fillText("TRANSELO | MIS 15 AÑOS", 50, 1300);
        const link = document.createElement('a');
        link.download = `HologramSelfie.png`;
        link.href = composer.toDataURL();
        link.click();
        document.body.classList.remove('camera-active');
    }, 500);
}

// Utils
function b64toBlob(b, c) {
    const s = atob(b); const arrays = [];
    for (let o = 0; o < s.length; o += 512) {
        const sc = s.slice(o, o + 512);
        const n = new Array(sc.length);
        for (let i = 0; i < sc.length; i++) n[i] = sc.charCodeAt(i);
        arrays.push(new Uint8Array(n));
    }
    return new Blob(arrays, {type: c});
}

function initParticles(t) {
    let color = "#00f2ff";
    if (t === 'quince') color = "#ff00ff"; // Rosa/Purpurina para quinces
    if (t === 'boda') color = "#ffd700";
    particlesJS("particles-js", {
        "particles": { "number": { "value": 100 }, "color": { "value": color }, "line_linked": { "enable": true, "color": color } }
    });
}

micBtn.addEventListener('mousedown', toggleMic);
micBtn.addEventListener('mouseup', toggleMic);
selfieBtn.addEventListener('click', takeSelfie);
window.addEventListener('load', init);
