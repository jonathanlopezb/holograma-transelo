// 🌌 TRANSELO ENGINE 2.0 - ARCHITECTURE REAL & AI PERSONALIZATION
const API_BASE = '/api';
const micBtn = document.getElementById('mic-btn');
const selfieBtn = document.getElementById('selfie-btn');
const transcriptBox = document.getElementById('transcript-box');
const vCanvas = document.getElementById('visualizer-canvas');
const vCtx = vCanvas.getContext('2d');
const avatarVideo = document.getElementById('avatar-video');
const userCamera = document.getElementById('user-camera');

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

// 1. INITIALIZATION & AVATAR SYNC
async function init() {
    // SYNC AVATAR: ¿Quién es la cumpleañera de hoy?
    try {
        const resAvatar = await fetch(`${API_BASE}/event/current-avatar`);
        const avatarData = await resAvatar.json();
        
        if (avatarData.video_url.endsWith('.jpg')) {
            // Si es imagen, la mostramos estática o con un filtro glitch
            avatarVideo.poster = avatarData.video_url;
            avatarVideo.src = "";
        } else {
            avatarVideo.src = avatarData.video_url;
        }
        
    } catch (e) {
        console.error("No se pudo cargar el avatar IA:", e);
    }

    // Reveal UI
    gsap.to(".guest-card", { opacity: 1, x: 0, duration: 1, delay: 0.5 });
    gsap.to(".transcript-container", { opacity: 1, y: 0, duration: 1, delay: 0.8 });
    
    // Camera & Scanner
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
    document.body.className = `theme-${appState.context.evento}`;
    if (window.particlesJS) initParticles(appState.context.evento);
}

// 2. ESCÁNER QR CON VALIDACIÓN REAL
function startQRScanner() {
    if (appState.isScannerActive) return;
    const script = document.createElement('script');
    script.src = "https://unpkg.com/html5-qrcode";
    script.onload = () => {
        const html5QrCode = new Html5Qrcode("app-viewport");
        const config = { fps: 20, qrbox: { width: 300, height: 300 } };
        html5QrCode.start({ facingMode: "user" }, config, async (qrId) => {
            if (!appState.isWelcomeTriggered && qrId.length < 15) { 
                appState.isWelcomeTriggered = true;
                await validateAndWelcome(qrId);
            }
        });
        appState.isScannerActive = true;
    };
    document.head.appendChild(script);
}

async function validateAndWelcome(qrId) {
    try {
        transcriptBox.textContent = `📡 IDENTIFICANDO INVITADO...`;
        const resGuest = await fetch(`${API_BASE}/guest/${qrId}`);
        if (!resGuest.ok) throw new Error();
        const guest = await resGuest.json();
        
        appState.context = { nombre: guest.name, mesa: guest.table, evento: guest.event_type, host_name: guest.event_host };
        updateUI();

        // TRIGGER AI
        const formData = new FormData();
        const prompt = `Soy yo, ${appState.context.host_name}. ¡Bienvenido ${appState.context.name}! Qué alegría verte aquí. Tu mesa es la ${appState.context.table}.`;
        formData.append('text_trigger', prompt);
        formData.append('context', JSON.stringify(appState.context));

        const resChat = await fetch(`${API_BASE}/chat`, { method: 'POST', body: formData });
        const chat = await resChat.json();
        if (chat.type === 'success') {
            typeWriter(chat.response);
            playAudio(chat.audio);
            setTimeout(() => { appState.isWelcomeTriggered = false; }, 15000);
        }
    } catch(e) { 
        transcriptBox.textContent = "❌ ERROR: ACCESO DENEGADO";
        setTimeout(() => { appState.isWelcomeTriggered = false; }, 4000);
    }
}

// 3. AUDIO ENGINE
async function toggleMic() {
    if (!appState.isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            appState.mediaRecorder = new MediaRecorder(stream);
            appState.audioChunks = [];
            if(!appState.audioCtx) appState.audioCtx = new (window.AudioContext||window.webkitAudioContext)();
            const source = appState.audioCtx.createMediaStreamSource(stream);
            setupVisualizer(source);
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
        const res = await fetch(`${API_BASE}/chat`, { method: 'POST', body: formData });
        const data = await res.json();
        if (data.type === 'success') { typeWriter(data.response); playAudio(data.audio); }
    } catch (e) { transcriptBox.textContent = "❌ ERROR"; }
}

function setupVisualizer(sourceNode) {
    if (!appState.analyser) { appState.analyser = appState.audioCtx.createAnalyser(); appState.analyser.fftSize = 64; }
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
        ctx.fillText("TRANSELO | " + (appState.context.host_name || "MIS 15 AÑOS"), 50, 1300);
        const link = document.createElement('a');
        link.download = `Selfie_Hologram.png`;
        link.href = composer.toDataURL();
        link.click();
        document.body.classList.remove('camera-active');
    }, 500);
}

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
    if (t === 'quince') color = "#ff00ff";
    if (t === 'boda') color = "#ffd700";
    particlesJS("particles-js", {
        "particles": { "number": { "value": 100 }, "color": { "value": color }, "line_linked": { "enable": true, "color": color } }
    });
}

micBtn.addEventListener('mousedown', toggleMic);
micBtn.addEventListener('mouseup', toggleMic);
selfieBtn.addEventListener('click', takeSelfie);
window.addEventListener('load', init);
