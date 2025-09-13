#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Powered Local Governance Assistant - Final Backend (FIXED)
---------------------------------------------------------------------
- Serves a multi-page frontend with static assets (CSS, JS, images).
- Connects all backend API endpoints for chat, voice, OTP, and forms.
- Contains fixes for multilingual chat, STT, and improved AI prompting.
"""

import os
import uuid
import json
import sqlite3
import random
import base64
from datetime import datetime
from typing import Optional, Dict

from pydub import AudioSegment
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_from_directory, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv

# -------- AI & Service Imports --------
import google.generativeai as genai
from OpenRouterTranslate import OpenRouterTranslate
import whisper
from gtts import gTTS
from otp_handler import OTPHandler

# -------------------- Flask App Setup --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
TTS_DIR = os.path.join(BASE_DIR, "tts")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "a-very-secret-key-that-you-should-change")
app.config["JSON_AS_ASCII"] = False
CORS(app, resources={r"/api/*": {"origins": "*"}})

# -------------------- DB Setup --------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # This table is for the AI chat history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, user_message TEXT,
            bot_message TEXT, source_lang TEXT, target_lang TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    # This table is for the general application form
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, applicant_name TEXT,
            application_type TEXT, details TEXT, status TEXT DEFAULT 'submitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    # --- THIS IS THE NEW, CORRECT TABLE FOR YOUR GEOTAGGED COMPLAINTS ---
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
        )""")
    conn.commit()
    conn.close()

init_db()

# -------------------- AI Model Initialization --------------------
gemini_model = None
try:
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        print("[OK] Gemini initialized.")
    else:
        print("[WARN] GEMINI_API_KEY not found in .env file.")
except Exception as e:
    print(f"[ERROR] Gemini init failed: {e}")

translator = OpenRouterTranslate()
whisper_model = None
try:
    whisper_model = whisper.load_model("small")
    print("[OK] Whisper STT model loaded ('small').")
except Exception as e:
    print(f"[ERROR] Could not load Whisper model: {e}")

otp_service = OTPHandler()

# -------------------- Utilities --------------------
def ask_gemini(prompt: str) -> str:
    if not gemini_model: return "Gemini is not configured."
    try:
        resp = gemini_model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"Sorry, AI service error: {e}"

def translate_text(text: str, source: str, target: str) -> str:
    if not target or source.lower() == target.lower(): return text
    return translator.translate(text, source, target)

def detect_language(text: str) -> str:
    return translator.detect_language(text)

def generate_fake_bill(bill_type: str) -> Dict:
    user_details = {"name": "Ram Das", "phone": "+91 9876543210", "address": "Village Rampur, PIN: 261001"}
    is_paid = random.choice([True, False])
    bill_data = {
        "property_tax": {"title": "Property Tax Bill", "bill_id": f"PT-{random.randint(10000, 99999)}", "amount": f"₹ {random.randint(500, 2500)}", "due_date": "2025-08-30"},
        "water_bill": {"title": "Water Bill", "bill_id": f"WB-{random.randint(10000, 99999)}", "amount": f"₹ {random.randint(200, 800)}", "due_date": "2025-08-25"},
        "electricity_bill": {"title": "Electricity Bill", "bill_id": f"EB-{random.randint(10000, 99999)}", "amount": f"₹ {random.randint(300, 1500)}", "due_date": "2025-08-28"}
    }
    if bill_type in bill_data:
        bill = bill_data[bill_type]; bill.update(user_details)
        bill["status"] = "Paid" if is_paid else "Unpaid"
        if is_paid: bill["paid_on"] = "2025-08-05"
        return bill
    return {}
    
# -------------------- HTML Page Routes --------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/otp-login", methods=["GET"])
def otp_login_page():
    return render_template("otp_verification.html")

# --- ADD THIS NEW ROUTE ---
@app.route("/complaint", methods=["GET"])
def complaint_page():
    """Serves the new geotagged complaint form."""
    return render_template("complaint.html")

# -------------------- API Routes --------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    message = data.get("message", "").strip()
    if not message: return jsonify({"ok": False, "error": "message is required"}), 400
    
    source_language = detect_language(message)
    target_language = data.get("target_language", source_language)

    text_for_llm = translate_text(message, source_language, "en")

    bill_type = None
    if "property tax" in text_for_llm.lower(): bill_type = "property_tax"
    elif "water bill" in text_for_llm.lower(): bill_type = "water_bill"
    elif "electricity bill" in text_for_llm.lower(): bill_type = "electricity_bill"
    if bill_type: return jsonify({"ok": True, "response_type": "bill_details", "data": generate_fake_bill(bill_type)})

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
    
    final_reply = translate_text(bot_reply_en, "en", target_language)
    
    return jsonify({"ok": True, "response_type": "text", "bot_reply": final_reply})

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    mobile_number = data.get("mobile_number")
    if not mobile_number or not mobile_number.isdigit() or len(mobile_number) != 10:
        return jsonify({"ok": False, "error": "Invalid mobile number."}), 400
    otp_value = otp_service.generate_otp()
    session['otp'] = otp_value
    print(f"--- DEMO OTP for {mobile_number}: {otp_value} ---")
    success = otp_service.send_otp(mobile_number, otp_value)
    return jsonify({"ok": True, "message": "OTP processed."})

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    user_otp = data.get("otp")
    stored_otp = session.get('otp')
    if not stored_otp:
        return jsonify({"ok": False, "error": "OTP expired. Request a new one."}), 400
    if user_otp == stored_otp:
        session.pop('otp', None)
        return jsonify({"ok": True, "message": "Verification successful."})
    else:
        return jsonify({"ok": False, "error": "Invalid OTP."}), 400

@app.route("/api/apply", methods=["POST"])
def handle_application():
    try:
        details = {"email": request.form.get('email'), "phone": request.form.get('phone'), "purpose": request.form.get('purpose')}
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO applications (applicant_name, application_type, details) VALUES (?, ?, ?)",
            (request.form.get('name'), "Service Application", json.dumps(details))
        )
        app_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "ticket_number": f"APP-{app_id:06d}"})
    except Exception as e:
        return jsonify({"ok": False, "error": "Server error during application."}), 500
# --- ADD THIS ENTIRE NEW ENDPOINT HERE ---
# --- ADD THIS ENTIRE NEW ENDPOINT ---
# --- NEW, UPDATED get_applications FUNCTION ---
@app.route("/api/get-applications", methods=["GET"])
def get_applications():
    """Fetches both regular applications and geotagged complaints."""
    conn = get_db()
    cur = conn.cursor()

    all_tickets = []
    
    # Fetch standard applications from the 'applications' table
    apps_raw = cur.execute("SELECT id, applicant_name, application_type FROM applications ORDER BY created_at DESC").fetchall()
    app_statuses = ["In Review", "Payment Pending"]
    for app in apps_raw:
        all_tickets.append({
            "id": f"APP-{app['id']:06d}",
            "title": app['application_type'],
            "details": f"Applicant: {app['applicant_name']}",
            "status_text": random.choice(app_statuses),
            "type": "application"
        })

    # Fetch geotagged complaints from the 'complaints_geotagged' table
    complaints_raw = cur.execute("SELECT id, name, department, details FROM complaints_geotagged ORDER BY created_at DESC").fetchall()
    conn.close()

    for comp in complaints_raw:
        all_tickets.append({
            "id": f"COMP-{comp['id']:06d}",
            "title": f"Complaint: {comp['details']}",
            "details": f"Dept: {comp['department'].upper()}",
            "status_text": "In Review",
            "type": "complaint"
        })

    # --- THIS IS THE FIX ---
    # Manually add the tickets that were previously in the HTML
    # Now, they will be part of the dynamic list and filtered correctly.
    all_tickets.append({
        "id": "GOI-IC-2025-009012",
        "title": "Income Certificate Request",
        "details": "Dept: Revenue Department",
        "status_text": "Approved",
        "type": "certificate"
    })
    all_tickets.append({
        "id": "GOI-WC-2025-003456",
        "title": "Water Connection Application",
        "details": "Dept: Municipal Services",
        "status_text": "Rejected",
        "type": "application"
    })

    return jsonify({"ok": True, "applications": all_tickets})

@app.route("/api/submit-complaint", methods=["POST"])
def submit_complaint():
    """Receives complaint data with a base64 photo and geotag."""
    data = request.json
    if not all(k in data for k in ['name', 'phone', 'department', 'details', 'photo', 'latitude', 'longitude']):
        return jsonify({"ok": False, "error": "Missing required form data."}), 400

    try:
        # --- Handle the Base64 Image ---
        # 1. Split the header from the image data (e.g., "data:image/png;base64,")
        header, encoded = data['photo'].split(",", 1)
        
        # 2. Decode the base64 string into image data
        image_data = base64.b64decode(encoded)
        
        # 3. Create a unique filename to prevent overwrites
        image_filename = f"complaint_{uuid.uuid4().hex}.png"
        
        # 4. Define where to save the image (e.g., in a 'uploads/complaints' folder)
        complaints_dir = os.path.join(UPLOAD_DIR, 'complaints')
        os.makedirs(complaints_dir, exist_ok=True)
        image_path = os.path.join(complaints_dir, image_filename)
        
        # 5. Save the image file to your server
        with open(image_path, "wb") as f:
            f.write(image_data)
        
        # --- Save complaint details to the database ---
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO complaints_geotagged (name, phone, department, details, photo_filename, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (data['name'], data['phone'], data['department'], data['details'], image_filename, data['latitude'], data['longitude'])
        )
        ticket_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        # Return a success message with the new ticket ID
        return jsonify({"ok": True, "message": "Complaint submitted successfully.", "ticket_id": f"COMP-{ticket_id:06d}"})

    except Exception as e:
        print(f"[ERROR] Complaint submission failed: {e}")
        return jsonify({"ok": False, "error": "An internal server error occurred."}), 500
    
@app.route("/api/voice-to-text", methods=["POST"])
def voice_to_text():
    if not whisper_model: return jsonify({"ok": False, "error": "Whisper model not loaded"}), 500
    if "audio" not in request.files: return jsonify({"ok": False, "error": "No audio file uploaded"}), 400

    file = request.files["audio"]
    temp_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4().hex}.wav")
    file.save(temp_path)

    try:
        result = whisper_model.transcribe(temp_path, fp16=False)
        return jsonify({"ok": True, "text": result["text"], "language": result["language"]})
    except Exception as e:
        print(f"Whisper Error: {e}")
        return jsonify({"ok": False, "error": "Could not process audio."}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
        
@app.route("/api/text-to-speech", methods=["POST"])
def text_to_speech():
    data = request.json
    text = data.get("text", "").strip()
    lang = data.get("language", "en").lower()
    if not text: return jsonify({"ok": False, "error": "text is required"}), 400

    try:
        tts = gTTS(text=text, lang=lang)
        filename = f"tts_{uuid.uuid4().hex}.mp3"
        path = os.path.join(TTS_DIR, filename)
        tts.save(path)
        return jsonify({"ok": True, "audio_url": f"/tts/{filename}"})
    except Exception as e:
        print(f"gTTS Error: {e}")
        return jsonify({"ok": False, "error": f"Could not generate audio for lang '{lang}'"}), 500

@app.route("/tts/<path:filename>", methods=["GET"])
def serve_tts(filename):
    return send_from_directory(TTS_DIR, filename)

if __name__ == "__main__":
    print("=== FINAL Backend Starting (All Fixes Applied) ===")
    app.run(host="0.0.0.0", port=5000, debug=True)

