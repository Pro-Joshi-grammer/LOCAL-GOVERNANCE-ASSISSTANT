// ============================================
// HAMBURGER + SIDEBAR + PAGE NAVIGATION (MISSING)
// ============================================
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('active');
  document.getElementById('overlay').classList.toggle('active');
  document.querySelector('.hamburger').classList.toggle('active');
}

function navigateToPage(pageId) {
  // Update active nav link
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelector(`[data-page="${pageId}"]`).classList.add('active');
  
  // Switch page content
  document.querySelectorAll('.page-content').forEach(page => page.classList.remove('active'));
  document.getElementById(pageId).classList.add('active');
  
  // Update breadcrumb
  const pageNames = {
    'home': 'Home Dashboard',
    'services': 'All Services',
    'tickets': 'My Applications',
    'certificates': 'Certificates',
    'payments': 'Payments',
    'profile': 'My Profile'
  };
  document.getElementById('current-page').textContent = pageNames[pageId];
  
  // Close sidebar on desktop too (optional)
  if (window.innerWidth <= 768) toggleSidebar();
}



document.addEventListener("DOMContentLoaded", () => {
  const chatHistory = document.getElementById("chat-history");
  const input = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const micBtn = document.getElementById("mic-btn");

  if (!chatHistory || !input || !sendBtn || !micBtn) {
    console.error("Missing chat elements", { chatHistory, input, sendBtn, micBtn });
    return;
  }

  function addMsg(who, text) {
    const div = document.createElement("div");
    div.className = (who === "user") ? "chat-message user-message" : "chat-message bot-message";
    div.textContent = text;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }

  async function sendText(message) {
    const msg = (message || "").trim();
    if (!msg) return;

    addMsg("user", msg);

    let res, data;
    try {
      res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
      });
      data = await res.json();
    } catch (e) {
      console.error(e);
      addMsg("bot", "Server error (chat).");
      return;
    }

    if (!data || !data.ok) {
      addMsg("bot", "Server error: " + ((data && data.error) ? data.error : "unknown"));
      return;
    }

    addMsg("bot", data.bot_reply || "(no reply)");

    if (data.audio_url) {
      const audio = new Audio(data.audio_url + "?t=" + Date.now());
      audio.play().catch(console.error);
    }
  }

  sendBtn.addEventListener("click", () => {
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    sendText(msg);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // -------- Voice (toggle start/stop) --------
  let recorder = null;
  let chunks = [];
  let streamRef = null;

  async function startRecording() {
    streamRef = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(streamRef);
    chunks = [];

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = async () => {
      try {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, "voice.webm");

        input.value = "Processing voice...";

        const r = await fetch("/api/voice-to-text", { method: "POST", body: form });
        const j = await r.json();

        input.value = "";

       if (j && j.ok && j.text) {
  // Put recognized text into the input, but DON'T auto-send
  input.value = j.text.trim();
}
 
else {
          addMsg("bot", "STT failed: " + ((j && j.error) ? j.error : "unknown"));
        }
      } catch (e) {
        console.error(e);
        input.value = "";
        addMsg("bot", "Server error (voice).");
      } finally {
        if (streamRef) streamRef.getTracks().forEach(t => t.stop());
        streamRef = null;
        recorder = null;
        chunks = [];
        micBtn.classList.remove("is-recording");
        micBtn.textContent = "🎤";
      }
    };

    recorder.start();
    micBtn.classList.add("is-recording");
    micBtn.textContent = "⏹";
  }

  micBtn.addEventListener("click", async () => {
    try {
      if (recorder && recorder.state === "recording") {
        recorder.stop();
        return;
      }
      await startRecording();
    } catch (e) {
      console.error(e);
      addMsg("bot", "Mic permission denied / unsupported.");
    }
  });
});
