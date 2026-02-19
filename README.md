# Local Governance Assistant (LGA)
## AI-Powered Voice-First Telugu Government Services Portal

[
[
[

**Voice-enabled, offline-capable portal** for rural Telugu citizens to access government services using **Whisper STT → Ollama LLM + RAG → MMS-TTS** pipeline.

***

## 🎯 **What It Does**

Citizens can:
- **Voice queries** in Telugu: "నా ఇంట్లో తాగునీరు లేదు" → Gets MWSSB helpline 1800-425-7425
- **File complaints** (water, electricity, roads) with photo + geolocation
- **Track applications** (ration card, certificates, schemes)
- **Get scheme info** (Rythubandhu ₹5,000/acre, Kalyana Lakshmi ₹1L)
- **Audio responses** in natural Telugu speech




***

## 🏗️ **Tech Stack**

```
┌─────────────────┐    ┌──────────────┐    ┌──────────────┐
│   Whisper STT   │───▶│ Chroma RAG   │───▶│ Ollama LLM   │
│  (base model)   │    │(governance_  │    │llama3.2:3b   │
└─────────────────┘    │ brochure.pdf) │    │Godavari opt. │
                       └──────┬───────┘    └──────┬───────┘
                              │                  │
                       ┌──────┴───────┐    ┌──────┴───────┐
                       │   MMS-TTS    │    │   Flask API  │
                       │(facebook/    │◀──▶│/api/chat     │
                       │ mms-tts-tel) │    │/voice-to-text│
                       └──────────────┘    └──────────────┘
```

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | HTML/CSS/JS + Mobile-first | Voice chat UI, hamburger nav |
| **Backend** | Flask + SQLite | `/api/chat`, `/api/voice-to-text` |
| **STT** | OpenAI Whisper (`base`) | Telugu speech → text |
| **LLM** | Ollama (`llama3.2:3b`) | RAG-grounded responses |
| **RAG** | Chroma + MiniLM-L6-v2 | `governance_brochure.pdf` retrieval |
| **TTS** | MMS-TTS (`facebook/mms-tts-tel`) | Telugu text → speech (.wav) |



***

## 🚀 **Quick Start (5 minutes)**

### Prerequisites
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg python3-venv git

# NVIDIA GPU drivers + CUDA (optional, speeds up 3x)
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit
```

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/lga.git
cd lga
python3 -m venv virenv
source virenv/bin/activate  # Linux/Mac
# virenv\Scripts\activate  # Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Download Models
```bash
# Ollama LLM (3GB, downloads automatically first run)
ollama pull llama3.2:3b

# Or Telugu-specialized (optional):
# ollama pull godavari:latest
```

### 4. Add Knowledge Base
```bash
# Download sample governance brochure (or use your own PDF)
wget https://example.com/governance_brochure.pdf
# Edit app.py: KBPATH = "governance_brochure.pdf"
```

### 5. Run Backend
```bash
python app.py
```
```
[BOOT] ✓ Ollama connected! Model: llama3.2:3b
[BOOT] ✓ TTS loaded
[RAG] Ready. KB loaded: governance_brochure.pdf
[BOOT] Whisper loaded.
=== BACKEND STARTED ===
 * Running on http://127.0.0.1:5000
```

### 6. Open Frontend
```
http://localhost:5000
```



<img width="1919" height="870" alt="Screenshot 2026-02-19 201711" src="https://github.com/user-attachments/assets/36460cb2-6217-4c0d-ac28-00b3f62fa8ef" />

<img width="1919" height="874" alt="Screenshot 2026-02-19 201805" src="https://github.com/user-attachments/assets/0445a724-f821-416e-a9b2-cd7c73a76892" />


<img width="1917" height="751" alt="Screenshot 2026-02-19 201735" src="https://github.com/user-attachments/assets/d3f703eb-a3f0-4aa6-8599-65772b0b8d19" />

***

## 🗣️ **Voice Demo**

1. **Click mic button** → Speak: *"నా ఇంట్లో తాగునీరు లేదు"*
2. **STT** → "నా ఇంట్లో తాగునీరు లేదు"
3. **RAG** → Retrieves MWSSB section from PDF
4. **LLM** → "తాగునీరు సమస్యలకు MWSSB helpline: 1800-425-7425"
5. **TTS** → Plays Telugu audio response

***

## 📁 **Project Structure**

```
lga/
├── app.py                 # Flask backend (STT + chat API)
├── ai_engine_ollama.py    # RAG + Ollama + MMS-TTS
├── static/
│   ├── style.css         # Mobile-first responsive UI
│   ├── script.js         # Chat + hamburger + voice
│   ├── tts/              # Generated audio (gitignore)
│   └── images/           # UI assets
├── templates/            # (optional Flask templates)
├── governance_brochure.pdf # RAG knowledge base
├── requirements.txt
├── .gitignore
└── README.md
```

***

## 🔧 **Backend Endpoints**

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/chat` | POST | Text → AI response + audio | `{bot_reply, audio_url}` |
| `/api/voice-to-text` | POST | Audio → transcribed text | `{text, ok}` |
| `/api/apply` | POST | Submit application form | `{ticketId: "APP-000123"}` |
| `/` | GET | Home page | `index.html` |

***

## ⚙️ **Customization**

### Telugu LLMs (swap in `ai_engine_ollama.py`)
```python
# Edit MODEL_NAME
self.model_name = "llama3.2:3b"      # Fast, general
# self.model_name = "godavari:latest"  # Telugu-specialized
# self.model_name = "navarasa:2b"      # Indic multilingual
```

### RAG Knowledge Base
```bash
# Replace PDF with your local schemes/helplines
cp your_schemes.pdf governance_brochure.pdf
python app.py  # Auto-ingests on startup
```

***

## 📊 **Performance** (RTX 3050, i5, 16GB)

| Query Type | LLM Time | TTS Time | Total |
|------------|----------|----------|-------|
| Water complaint | 1.9s | 0.9s | **2.8s** |
| Ration card | 8.1s | 3.9s | **12.0s** |
| Certificates | 11.1s | 0.6s | **11.7s** |



<img width="1380" height="241" alt="Screenshot 2026-02-19 201912" src="https://github.com/user-attachments/assets/917f15a3-7e0b-456f-84c6-c95a49021ae9" />

***

## 🛠️ **Hardware Requirements**

| Usage | CPU | RAM | GPU | Storage |
|-------|-----|-----|-----|---------|
| **Development** | i5 | 8GB | Optional | 10GB |
| **Production** | i7 | 16GB | RTX 3050+ | 20GB |

***
***

## 🤝 **Hackathon Evolution**

| Version | Date | Features |
|---------|------|----------|
| **v1.0** | 2024 | Text-only chat |
| **v2.0** | 2026 | **STT + RAG + TTS** |

***

## 📄 **License**
MIT License - Free for academic/commercial use.

## 🙏 **Acknowledgements**
- **Ollama** - Local LLM inference
- **OpenAI Whisper** - Multilingual STT
- **Meta MMS-TTS** - Telugu speech synthesis
- **Chroma + LangChain** - RAG pipeline

***


**⭐ Star this repo if it helped!** 🚀
