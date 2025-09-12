#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Powered Local Governance Assistant - Flask Backend (Hackathon Ready)
---------------------------------------------------------------------
- Serves as the backend API for your HTML/CSS frontend.
- Chatbot answers via Google Gemini, with intent detection for specific tasks.
- Multilingual translation via OpenRouter (Gemma-3).
- SQLite database for tickets, applications, and chat history.
- Voice: speech-to-text (SpeechRecognition) and text-to-speech (gTTS).
- Safe CORS enabled for easy local dev.
"""

import os
import uuid
import json
import traceback
import sqlite3
import random  # NEW: Import the random library
from datetime import datetime
from typing import Optional, Dict
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory, send_file, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# -------- Optional: Google Gemini (install google-generativeai) --------
GEMINI_AVAILABLE = True
try:
    import google.generativeai as genai
except Exception as e:
    GEMINI_AVAILABLE = False

# -------- Voice packages --------
try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None

# -------- Translation via OpenRouter (your provided class) --------
OpenRouterTranslate = None
try:
    from OpentRouterTanslate import OpenRouterTranslate as ORT
    OpenRouterTranslate = ORT
except Exception:
    try:
        from OpenRouterTranslate import OpenRouterTranslate as ORT
        OpenRouterTranslate = ORT
    except Exception:
        OpenRouterTranslate = None

# -------------------- Flask App Setup --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
TTS_DIR = os.path.join(BASE_DIR, "tts")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["JSON_AS_ASCII"] = False

CORS(app, resources={r"/api/*": {"origins": "*"}})

# -------------------- DB Helpers --------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Chat history
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            bot_message TEXT,
            source_lang TEXT,
            target_lang TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Complaints / tickets
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            issue TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Applications (birth, death, income, water bill, etc.)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT,
            application_type TEXT,
            details TEXT,
            status TEXT DEFAULT 'submitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# -------------------- Gemini Setup --------------------
gemini_model = None
def init_gemini():
    global gemini_model
    if not GEMINI_AVAILABLE:
        print("[WARN] google-generativeai not installed.")
        return
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] GEMINI_API_KEY not found in environment.")
        return
    try:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        print("[OK] Gemini initialized (gemini-1.5-flash).")
    except Exception as e:
        print(f"[ERROR] Gemini init failed: {e}")

init_gemini()

# -------------------- Translator Setup --------------------
translator = None
if OpenRouterTranslate is not None:
    try:
        translator = OpenRouterTranslate()
        print("[OK] OpenRouterTranslate initialized.")
    except Exception as e:
        print(f"[WARN] OpenRouterTranslate could not initialize: {e}")
else:
    print("[WARN] OpenRouterTranslate class not found.")

# -------------------- Utilities --------------------
LANG_CODE_VOICE_MAP: Dict[str, str] = {
    "en": "en-IN", "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN",
    "bn": "bn-IN", "mr": "mr-IN", "gu": "gu-IN", "ml": "ml-IN", "pa": "pa-IN",
}
GTTs_LANGUAGE_CODES = {
    "en": "en", "hi": "hi", "ta": "ta", "te": "te", "kn": "kn", "bn": "bn",
    "mr": "mr", "gu": "gu", "ml": "ml", "pa": "pa",
}

def generate_session_id() -> str:
    return uuid.uuid4().hex

def ask_gemini(prompt: str) -> str:
    if gemini_model is None:
        return "Gemini is not configured."
    try:
        resp = gemini_model.generate_content(prompt)
        if hasattr(resp, "text") and resp.text:
            return resp.text.strip()
        elif hasattr(resp, "candidates") and resp.candidates:
            parts = [getattr(part, "text", "") for part in resp.candidates[0].content.parts]
            return "\n".join([p for p in parts if p]).strip() or "[Empty response]"
        else:
            return "[No text returned by Gemini]"
    except Exception as e:
        return f"[Gemini error] {e}"

def translate_text(text: str, source_language: Optional[str], target_language: Optional[str]) -> str:
    if not target_language or (source_language and source_language.lower() == target_language.lower()):
        return text
    if translator:
        try:
            return translator.translate(text, source_language or "auto", target_language)
        except Exception as e:
            return f"[Translation error] {e}\n{text}"
    else:
        return f"[{target_language} translation unavailable] {text}"

def detect_language(text: str) -> str:
    if translator:
        try:
            return translator.detect_language(text)
        except Exception:
            return "en"
    return "en"

def save_chat(session_id: str, user_message: str, bot_message: str, source_lang: str, target_lang: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_history (session_id, user_message, bot_message, source_lang, target_lang) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_message, bot_message, source_lang, target_lang),
    )
    conn.commit()
    conn.close()

# --- NEW: FAKE BILL GENERATION LOGIC ---
def generate_fake_bill(bill_type: str) -> Dict:
    """Generates a fake bill with random details."""
    user_details = {
        "name": "Ram Das",
        "phone": "+91 9876543210",
        "address": "Village Rampur, District Sitapur, PIN: 261001"
    }
    is_paid = random.choice([True, False])
    bill_data = {
        "property_tax": {"title": "Property Tax Bill", "bill_id": f"PT-{random.randint(10000, 99999)}", "amount": f"₹ {random.randint(500, 2500)}", "due_date": "2025-08-30"},
        "water_bill": {"title": "Water Bill", "bill_id": f"WB-{random.randint(10000, 99999)}", "amount": f"₹ {random.randint(200, 800)}", "due_date": "2025-08-25"},
        "electricity_bill": {"title": "Electricity Bill", "bill_id": f"EB-{random.randint(10000, 99999)}", "amount": f"₹ {random.randint(300, 1500)}", "due_date": "2025-08-28"}
    }
    if bill_type == "electricity_bill": # Let's make one bill type always appear as paid for demo purposes
        is_paid = True
    if bill_type in bill_data:
        bill = bill_data[bill_type]
        bill.update(user_details)
        bill["status"] = "Paid" if is_paid else "Unpaid"
        if is_paid:
            bill["paid_on"] = "2025-08-05"
        return bill
    return {}

# -------------------- Routes --------------------

@app.route("/")
def home():
    try:
        return render_template("index1.html")
    except Exception:
        return "<h2>AI-Powered Local Governance Assistant (Backend Running)</h2>"

# ---- Chatbot endpoint ----
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "message is required"}), 400

    session_id = data.get("session_id") or generate_session_id()
    source_language = (data.get("source_language") or "").strip().lower() or detect_language(message)
    target_language = (data.get("target_language") or source_language or "en").strip().lower()

    text_for_llm = message.lower()
    if source_language != "en":
        text_for_llm = translate_text(message, source_language, "en").lower()

    # --- NEW: INTENT DETECTION FOR BILLS ---
    bill_type = None
    if "property tax" in text_for_llm:
        bill_type = "property_tax"
    elif "water bill" in text_for_llm or "water tax" in text_for_llm:
        bill_type = "water_bill"
    elif "electricity bill" in text_for_llm or "power bill" in text_for_llm:
        bill_type = "electricity_bill"
    
    if bill_type:
        fake_bill_data = generate_fake_bill(bill_type)
        return jsonify({"ok": True, "response_type": "bill_details", "data": fake_bill_data})

    # --- IF NOT A BILL QUERY, PROCEED WITH GEMINI ---
    system_prompt = f"""
    You are an AI assistant for a local village governance portal called "Sahayatha". Your primary role is to be helpful.

    **Rule 1: Complaint Resolution**
    If the user's query is a complaint about any of the issues listed below, you MUST respond in a helpful and specific format. First, acknowledge their problem, then provide the direct contact for the officer in charge. Finally, add the department's landline number as an alternative if the officer is unreachable.

Example Interaction:

User Query: "There are potholes on the main road."

Your ONLY Response: "For issues with road damage and potholes, the matter is overseen by Mr. Sanjay Singh (Road Inspector). Please contact him at +91 45678 90123. If the number is unreachable, you can contact the Public Works office at 040-23454444."

Contact Information:

Sanitation

Issues: water logging, garbage, drain

Primary Contact: Mr. Ramesh Kumar (Sanitation Supervisor) at +91 12345 67890.

Alternate: Sanitation Department Office at 040-23451111.

Electricity

Issues: power cut, street light

Primary Contact: Ms. Sunita Sharma (Junior Engineer) at +91 23456 78901.

Alternate: Electricity Board Office at 040-23452222.

Water Supply

Issues: no water, pipeline leakage

Primary Contact: Mr. Anil Verma (Pump Operator) at +91 34567 89012.

Alternate: Water Works Department at 040-23453333.

Public Works (Roads)

Issues: pothole, road damage

Primary Contact: Mr. Sanjay Singh (Road Inspector) at +91 45678 90123.

Alternate: Public Works Office at 040-23454444.

    **Rule 2: General Queries**
    If it's not a complaint, answer the query helpfully based on Indian local governance procedures.

    **Rule 3: Language**
    If the user's query is not in English it is in any other language, You have to reply back in the same language as the user's query.


    ---
    **User's Query:**
    {text_for_llm}
    """
    
    bot_reply_en = ask_gemini(system_prompt)
    final_reply = bot_reply_en
    if target_language and target_language != "en":
        final_reply = translate_text(bot_reply_en, "en", target_language)

    try:
        # For simplicity, we save the final translated reply.
        # A more complex app might save both original and translated versions.
        save_chat(session_id, message, final_reply, source_language, target_language)
    except Exception as e:
        print(f"[WARN] Failed to save chat history: {e}")

    return jsonify({"ok": True, "response_type": "text", "bot_reply": final_reply}), 200


# Route to display the application form page
@app.route("/apply", methods=["GET"])
def apply_page():
    return render_template("apply.html")

# Route to handle the form submission
@app.route("/api/apply", methods=["POST"])
def handle_application():
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        purpose = request.form.get('purpose')
        service_id = request.form.get('service_id', 'General Application')

        # Handle file upload
        uploaded_file = request.files.get('document')
        file_path = None
        if uploaded_file and uploaded_file.filename != '':
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(UPLOAD_DIR, filename)
            uploaded_file.save(file_path)

        # Store in database
        conn = get_db()
        cur = conn.cursor()
        details = {
            "email": email, "phone": phone, "purpose": purpose,
            "service_id": service_id, "file_path": file_path
        }
        cur.execute(
            "INSERT INTO applications (applicant_name, application_type, details) VALUES (?, ?, ?)",
            (name, "Service Application", json.dumps(details))
        )
        app_id = cur.lastrowid
        conn.commit()
        conn.close()

        return jsonify({"ok": True, "ticket_number": f"APP-{app_id:06d}"})

    except Exception as e:
        print(f"Application error: {e}")
        return jsonify({"ok": False, "error": "An error occurred on the server."}), 500


# ---- Translate endpoint ----
@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400
    source_language = (data.get("source_language") or "en").strip().lower()
    target_language = (data.get("target_language") or "en").strip().lower()
    translated = translate_text(text, source_language, target_language)
    return jsonify({"ok": True, "translated_text": translated, "source_language": source_language, "target_language": target_language})

# ---- Chat history ----
@app.route("/api/history", methods=["GET"])
def api_history():
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_history WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "session_id": session_id, "history": rows})

# ---- Complaints CRUD ----
@app.route("/api/complaints", methods=["POST"])
def create_complaint():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    contact = (data.get("contact") or "").strip()
    issue = (data.get("issue") or "").strip()
    if not issue:
        return jsonify({"ok": False, "error": "issue is required"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO complaints (name, contact, issue) VALUES (?, ?, ?)", (name, contact, issue))
    comp_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": comp_id, "status": "open"})

@app.route("/api/complaints", methods=["GET"])
def list_complaints():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"ok": True, "complaints": rows})

@app.route("/api/complaints/<int:comp_id>", methods=["GET"])
def get_complaint(comp_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints WHERE id = ?", (comp_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "complaint": dict(row)})

@app.route("/api/complaints/<int:comp_id>", methods=["PATCH"])
def update_complaint(comp_id):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if not status:
        return jsonify({"ok": False, "error": "status is required"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status = ? WHERE id = ?", (status, comp_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": comp_id, "status": status})

# ---- Applications CRUD (generic) ----
@app.route("/api/applications", methods=["POST"])
def create_application():
    data = request.get_json(silent=True) or {}
    applicant_name = (data.get("applicant_name") or "").strip()
    application_type = (data.get("application_type") or "").strip().lower()
    details = data.get("details") or {}
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO applications (applicant_name, application_type, details) VALUES (?, ?, ?)",
        (applicant_name, application_type, json.dumps(details, ensure_ascii=False)),
    )
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": app_id, "status": "submitted"})

@app.route("/api/applications", methods=["GET"])
def list_applications():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        try:
            r["details"] = json.loads(r.get("details") or "{}")
        except Exception:
            pass
    conn.close()
    return jsonify({"ok": True, "applications": rows})

@app.route("/api/applications/<int:app_id>", methods=["GET"])
def get_application(app_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "not found"}), 404
    row = dict(row)
    try:
        row["details"] = json.loads(row.get("details") or "{}")
    except Exception:
        pass
    return jsonify({"ok": True, "application": row})

@app.route("/api/applications/<int:app_id>", methods=["PATCH"])
def update_application(app_id):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if not status:
        return jsonify({"ok": False, "error": "status is required"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": app_id, "status": status})

# ---- Voice: Speech-to-Text ----
@app.route("/api/voice-to-text", methods=["POST"])
def voice_to_text():
    """
    Upload an audio file with form-data key 'audio'.
    This function now converts the audio to the correct WAV format before processing.
    """
    if sr is None:
        return jsonify({"ok": False, "error": "SpeechRecognition not installed"}), 500

    if "audio" not in request.files:
        return jsonify({"ok": False, "error": "No audio file uploaded with key 'audio'"}), 400

    file = request.files["audio"]
    filename = f"audio_{uuid.uuid4().hex}.wav"
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    # --- NEW: CONVERT AUDIO TO PCM WAV ---
    try:
        sound = AudioSegment.from_file(save_path)
        wav_path = os.path.join(UPLOAD_DIR, f"converted_{filename}")
        sound.export(wav_path, format="wav")
    except Exception as e:
        return jsonify({"ok": False, "error": f"Audio conversion error: {e}"}), 500
    # --- END OF CONVERSION ---

    # Language handling
    lang = (request.form.get("language") or "en").lower()
    sr_lang_code = LANG_CODE_VOICE_MAP.get(lang, "en-IN")

    # Recognize speech
    recog = sr.Recognizer()
    try:
        # IMPORTANT: Use the newly converted file (wav_path)
        with sr.AudioFile(wav_path) as source:
            audio = recog.record(source)
        text = recog.recognize_google(audio, language=sr_lang_code)
        return jsonify({"ok": True, "text": text, "language": lang})
    except sr.UnknownValueError:
        return jsonify({"ok": False, "error": "Could not understand audio"}), 400
    except sr.RequestError as e:
        return jsonify({"ok": False, "error": f"Speech recognition API error: {e}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": f"Processing error: {e}"}), 500
        
# ---- Voice: Text-to-Speech ----
@app.route("/api/text-to-speech", methods=["POST"])
def text_to_speech():
    if gTTS is None:
        return jsonify({"ok": False, "error": "gTTS not installed"}), 500
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400
    lang = (data.get("language") or "en").lower()
    gtts_lang = GTTs_LANGUAGE_CODES.get(lang, "en")
    try:
        tts = gTTS(text=text, lang=gtts_lang)
        filename = f"tts_{uuid.uuid4().hex}.mp3"
        path = os.path.join(TTS_DIR, filename)
        tts.save(path)
        return jsonify({"ok": True, "audio_url": f"/tts/{filename}", "filename": filename})
    except Exception as e:
        return jsonify({"ok": False, "error": f"TTS error: {e}"}), 500

@app.route("/tts/<path:filename>", methods=["GET"])
def serve_tts(filename):
    return send_from_directory(TTS_DIR, filename, as_attachment=False)

# -------------------- Error Handler --------------------
@app.errorhandler(500)
def server_error(e):
    return jsonify({"ok": False, "error": "Internal server error", "detail": str(e)}), 500

# -------------------- Main --------------------
if __name__ == "__main__":
    print("=== Backend starting ===")
    print(f"DB Path: {DB_PATH}")
    print(f"Uploads: {UPLOAD_DIR}")
    print(f"TTS Dir: {TTS_DIR}")
    print(f"GEMINI available: {GEMINI_AVAILABLE}")
    print(f"Translator available: {translator is not None}")
    app.run(host="0.0.0.0", port=5000, debug=True)