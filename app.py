#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
import json
import sqlite3
import base64
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import time
import whisper

from ai_engine_ollama import LocalGovernanceAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TTS_DIR = os.path.join(STATIC_DIR, "tts")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT,
            application_type TEXT,
            details TEXT,
            status TEXT DEFAULT 'submitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS complaints_geotagged (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            department TEXT NOT NULL,
            details TEXT,
            photo_filename TEXT,
            latitude REAL,
            longitude REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- AI ----------------
print("="*50)
print("[BOOT] Loading Ollama + MMS (offline heavy)...")
ai_bot = LocalGovernanceAI()

# Optional: keep a small TXT as KB; you can change later
KB_PATH = "governancebrochuer.txt"
if os.path.exists(KB_PATH):
    ai_bot.setup_rag(KB_PATH)
    print(f"[BOOT] KB loaded: {KB_PATH}")
else:
    print("[WARN] No KB file found; bot will answer generally without RAG.")
print("="*50)

# ---------------- Whisper (STT) ----------------
print("[BOOT] Loading Whisper STT model...")
# Use base for faster; change to "small" if needed
whisper_model = whisper.load_model("base")
print("[BOOT] Whisper loaded.")

# ---------------- Pages ----------------
@app.route("/")
def home():
    # Use whichever UI you are using in templates
    return render_template("index.html")

@app.route("/apply")
def apply_page():
    return render_template("apply.html")

@app.route("/complaint")
def complaint_page():
    return render_template("complaint.html")


# ---------------- API: Chat ----------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json(force=True)
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"ok": False, "error": "Empty message"}), 400

        print(f"[USER MESSAGE] {message}")

        # --- LLM timing ---
        t_llm_start = time.perf_counter()
        bot_reply = ai_bot.ask(message)
        t_llm_end = time.perf_counter()
        llm_time = t_llm_end - t_llm_start
        print(f"[TIMING] LLM time: {llm_time:.3f}s")

        # --- TTS timing ---
        audio_filename = f"response_{uuid.uuid4().hex[:8]}.wav"
        audio_path = os.path.join(TTS_DIR, audio_filename)

        t_tts_start = time.perf_counter()
        ai_bot.speak(bot_reply, output_path=audio_path)
        t_tts_end = time.perf_counter()
        tts_time = t_tts_end - t_tts_start
        print(f"[TIMING] TTS time: {tts_time:.3f}s")

        total_time = llm_time + tts_time
        print(f"[TIMING] Total (LLM+TTS): {total_time:.3f}s")

        return jsonify({
            "ok": True,
            "bot_reply": bot_reply,
            "audio_url": f"/static/tts/{audio_filename}",
            "timing": {
                "llm_time": llm_time,
                "tts_time": tts_time,
                "total_time": total_time
            }
        })

    except Exception as e:
        print(f"[ERROR] /api/chat failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
# ---------------- API: Voice to Text ----------------
@app.route("/api/voice-to-text", methods=["POST"])
def voice_to_text():
    if "audio" not in request.files:
        return jsonify({"ok": False, "error": "No audio uploaded"}), 400

    file = request.files["audio"]
    ext = os.path.splitext(file.filename)[1] or ".webm"
    temp_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4().hex}{ext}")
    file.save(temp_path)

    try:
        print("[STT] Processing audio...")

        t_stt_start = time.perf_counter()
        result = whisper_model.transcribe(
            temp_path,
            language="te",
            task="transcribe",
            fp16=False,
            initial_prompt="తెలుగు"
        )
        t_stt_end = time.perf_counter()
        stt_time = t_stt_end - t_stt_start
        print(f"[TIMING] STT time: {stt_time:.3f}s")

        text = (result.get("text") or "").strip()
        print(f"[STT RESULT] {text}")

        return jsonify({"ok": True, "text": text, "stt_time": stt_time})

    except Exception as e:
        print(f"[STT ERROR] {e}")
        return jsonify({"ok": False, "error": "STT failed"}), 500

    finally:
        try:
            os.remove(temp_path)
        except:
            pass

# ---------------- API: Apply (simple form) ----------------
@app.route("/api/apply", methods=["POST"])
def submit_application():
    try:
        # Accept both JSON and form-data
        if request.is_json:
            data = request.get_json()
            name = data.get("name")
            phone = data.get("phone")
            email = data.get("email")
            purpose = data.get("purpose")
        else:
            name = request.form.get("name")
            phone = request.form.get("phone")
            email = request.form.get("email")
            purpose = request.form.get("purpose")

        details = json.dumps({"phone": phone, "email": email, "purpose": purpose})

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO applications (applicant_name, application_type, details) VALUES (?, ?, ?)",
            (name, "Service Application", details)
        )
        app_id = cur.lastrowid
        conn.commit()
        conn.close()

        return jsonify({"ok": True, "ticket_id": f"APP-{app_id:06d}"})

    except Exception as e:
        print(f"[ERROR] /api/apply failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("=== BACKEND STARTED ===")
    # IMPORTANT: debug=False so it doesn't restart twice and reload models
    app.run(host="0.0.0.0", port=5000, debug=False)
