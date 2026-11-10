import io
import os
import time
import sqlite3
import secrets
from functools import wraps
from datetime import timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file, session, redirect, url_for, flash, g
from google import genai
from google.genai import types
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid

# ---------------------------------
# Configuration
# ---------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GNANI_API_KEY = os.getenv("GNANI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
# Set GEMINI_BACKUP_MODEL in .env only after confirming that model is
# available to your Gemini API key. Leave it blank to use only the primary.
GEMINI_PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_BACKUP_MODEL = os.getenv("GEMINI_BACKUP_MODEL", "").strip()

# Timbre v2.5 voice IDs.
# These IDs are sent to Gnani; the UI labels are only descriptions.
VOICE_OPTIONS = {
    "Kaveri": {"label": "Woman · Kaveri", "gender": "female"},
    "Pranav": {"label": "Man · Pranav", "gender": "male"},
    "Nalini": {"label": "Woman · Nalini", "gender": "female"},
    "Deepak": {"label": "Man · Deepak", "gender": "male"},
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=timedelta(days=7))
# Local-only development secret. For deployment set FLASK_SECRET_KEY in .env.
secret_path = BASE_DIR / ".flask_secret"
if os.getenv("FLASK_SECRET_KEY"):
    app.secret_key = os.getenv("FLASK_SECRET_KEY")
else:
    if not secret_path.exists():
        secret_path.write_text(secrets.token_hex(32), encoding="utf-8")
    app.secret_key = secret_path.read_text(encoding="utf-8").strip()
DB_PATH = BASE_DIR / "bharat_voice.db"
PROFILE_DIR = BASE_DIR / "static" / "uploads" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()

def init_db():
    with app.app_context():
        db().executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            profile_picture TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        """)
        # Safe migration for existing SQLite databases created before profile support.
        columns = {row[1] for row in db().execute("PRAGMA table_info(users)").fetchall()}
        if "profile_picture" not in columns:
            db().execute("ALTER TABLE users ADD COLUMN profile_picture TEXT")
        db().commit()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify(success=False, error="Please log in first."), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]

@app.context_processor
def inject_auth():
    return {"csrf_token": csrf_token, "current_name": session.get("user_name", "")}

def valid_csrf():
    provided = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    return bool(provided) and secrets.compare_digest(provided, session.get("csrf_token", ""))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("home"))
    if request.method == "POST":
        if not valid_csrf():
            return "Invalid form token. Refresh and retry.", 400
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not 2 <= len(name) <= 80 or not 5 <= len(email) <= 254 or "@" not in email or not 8 <= len(password) <= 128:
            flash("Enter a valid name, email and password (minimum 8 characters).", "error")
        else:
            try:
                with db():
                    db().execute("INSERT INTO users (name,email,password_hash) VALUES (?,?,?)", (name,email,generate_password_hash(password)))
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email is already registered.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))
    if request.method == "POST":
        if not valid_csrf():
            return "Invalid form token. Refresh and retry.", 400
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))
        flash("Incorrect email or password.", "error")
    return render_template("auth.html", mode="login")

@app.post("/logout")
@login_required
def logout():
    if not valid_csrf():
        return "Invalid form token.", 400
    session.clear()
    return redirect(url_for("login"))

@app.get("/api/profile")
@login_required
def get_profile():
    user = db().execute("SELECT id,name,email,profile_picture,created_at FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        session.clear()
        return jsonify(success=False, error="Account not found. Please log in again."), 404
    result = dict(user)
    result["profile_picture_url"] = (url_for("static", filename="uploads/profiles/" + result["profile_picture"]) if result["profile_picture"] else None)
    return jsonify(success=True, profile=result)


@app.post("/api/profile")
@login_required
def update_profile():
    if not valid_csrf():
        return jsonify(success=False, error="Invalid form token. Refresh and retry."), 400
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    if not 2 <= len(name) <= 80:
        return jsonify(success=False, error="Name must be between 2 and 80 characters."), 400
    if not 5 <= len(email) <= 254 or "@" not in email or email.startswith("@") or email.endswith("@"):
        return jsonify(success=False, error="Enter a valid email address."), 400

    picture = request.files.get("profile_picture")
    saved_name = None
    if picture and picture.filename:
        raw = picture.stream.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            return jsonify(success=False, error="Profile photo must be 5 MB or smaller."), 413
        signatures = ((b"\xff\xd8\xff", ".jpg"), (b"\x89PNG\r\n\x1a\n", ".png"), (b"RIFF", ".webp"))
        ext = None
        for sig, candidate in signatures:
            if raw.startswith(sig) and (candidate != ".webp" or (len(raw) > 12 and raw[8:12] == b"WEBP")):
                ext = candidate
                break
        if not ext:
            return jsonify(success=False, error="Upload a valid JPG, PNG or WEBP image."), 400
        saved_name = uuid.uuid4().hex + ext
        (PROFILE_DIR / saved_name).write_bytes(raw)

    old = db().execute("SELECT profile_picture FROM users WHERE id=?", (session["user_id"],)).fetchone()
    try:
        with db():
            if saved_name:
                db().execute("UPDATE users SET name=?, email=?, profile_picture=? WHERE id=?", (name,email,saved_name,session["user_id"]))
            else:
                db().execute("UPDATE users SET name=?, email=? WHERE id=?", (name,email,session["user_id"]))
    except sqlite3.IntegrityError:
        if saved_name:
            (PROFILE_DIR / saved_name).unlink(missing_ok=True)
        return jsonify(success=False, error="This email is already used by another account."), 409

    session["user_name"] = name
    if saved_name and old and old["profile_picture"]:
        (PROFILE_DIR / old["profile_picture"]).unlink(missing_ok=True)
    user = db().execute("SELECT id,name,email,profile_picture,created_at FROM users WHERE id=?", (session["user_id"],)).fetchone()
    result = dict(user)
    result["profile_picture_url"] = url_for("static", filename="uploads/profiles/" + result["profile_picture"]) if result["profile_picture"] else None
    return jsonify(success=True, message="Profile updated successfully.", profile=result)


@app.get("/api/conversations")
@login_required
def get_conversations():
    rows = db().execute("SELECT id,title,created_at FROM conversations WHERE user_id=? ORDER BY id DESC LIMIT 100", (session["user_id"],)).fetchall()
    return jsonify(success=True, conversations=[dict(r) for r in rows])

@app.get("/api/conversations/<int:conversation_id>/messages")
@login_required
def get_messages(conversation_id):
    owner = db().execute("SELECT id FROM conversations WHERE id=? AND user_id=?", (conversation_id, session["user_id"])).fetchone()
    if not owner:
        return jsonify(success=False,error="Conversation not found."), 404
    rows = db().execute("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,)).fetchall()
    return jsonify(success=True,messages=[dict(r) for r in rows])

@app.delete("/api/conversations/<int:conversation_id>")
@login_required
def delete_conversation(conversation_id):
    if not valid_csrf():
        return jsonify(success=False,error="Invalid form token."), 400
    with db():
        result=db().execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id,session["user_id"]))
    return jsonify(success=bool(result.rowcount))


# Create one Gemini client only.
gemini_client = (
    genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=18000,
            retry_options=types.HttpRetryOptions(attempts=1)
        )
    )
    if GEMINI_API_KEY else None
)


# ---------------------------------
# Home Page
# ---------------------------------

@app.route("/")
@login_required
def home():
    return render_template("index.html")


# ---------------------------------
# API Key Check
# ---------------------------------

def check_gnani_api_key():
    if not GNANI_API_KEY:
        return jsonify({
            "success": False,
            "error": "Gnani API key not found. Check your .env file."
        }), 500
    return None


# ---------------------------------
# Speech to Text (STT)
# ---------------------------------

@app.route("/api/transcribe", methods=["POST"])
@login_required
def transcribe():
    key_error = check_gnani_api_key()
    if key_error:
        return key_error

    try:
        audio = request.files.get("audio")

        if not audio or not audio.filename:
            return jsonify({
                "success": False,
                "error": "Please upload an audio file."
            }), 400

        files = {
            "audio_file": (
                audio.filename,
                audio.stream,
                audio.mimetype or "audio/wav"
            )
        }

        form_data = {
            "language_code": "hi-IN",
            "format": "transcribe",
            "itn_native_numerals": "true"
        }

        response = requests.post(
            STT_URL,
            headers={"X-API-Key-ID": GNANI_API_KEY},
            files=files,
            data=form_data,
            timeout=90
        )

        try:
            result = response.json()
        except ValueError:
            return jsonify({
                "success": False,
                "error": "STT service returned an invalid response.",
                "details": response.text[:500]
            }), 502

        if not response.ok:
            return jsonify({
                "success": False,
                "error": result.get("message", "Speech recognition failed."),
                "details": result
            }), response.status_code

        return jsonify(result), 200

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "STT request timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException as exc:
        app.logger.exception("STT connection error")
        return jsonify({
            "success": False,
            "error": "Could not connect to Gnani STT service.",
            "details": str(exc)
        }), 502

    except Exception as exc:
        app.logger.exception("STT error")
        return jsonify({
            "success": False,
            "error": "An unexpected STT error occurred.",
            "details": str(exc)
        }), 500


# ---------------------------------
# Text to Speech (TTS)
# ---------------------------------

@app.route("/api/speak", methods=["POST"])
@login_required
def speak():
    key_error = check_gnani_api_key()
    if key_error:
        return key_error

    try:
        data = request.get_json(silent=True) or {}

        text_input = data.get("text", "")
        if not isinstance(text_input, str):
            return jsonify({
                "success": False,
                "error": "Text must be a string."
            }), 400

        text_input = text_input.strip()
        if not text_input:
            return jsonify({
                "success": False,
                "error": "Please enter some text."
            }), 400

        if len(text_input) > 5000:
            return jsonify({
                "success": False,
                "error": "Text is too long. Maximum 5000 characters."
            }), 400

        # Only allow voice IDs deliberately exposed by the frontend.
        selected_voice = data.get("voice", "Nalini")
        if selected_voice not in VOICE_OPTIONS:
            return jsonify({
                "success": False,
                "error": "Invalid voice selected.",
                "available_voices": list(VOICE_OPTIONS.keys())
            }), 400

        # Timbre v2.5 accepts speed from 0.85 to 1.15.
        try:
            speed = float(data.get("speed", 1.0))
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "Speaking speed must be a number."
            }), 400

        if not 0.85 <= speed <= 1.15:
            return jsonify({
                "success": False,
                "error": "Speaking speed must be between 0.85 and 1.15."
            }), 400

        payload = {
            "text": text_input,
            "voice": selected_voice,
            "model": "timbre-v2.5",
            "language": "hi-IN",
            "speed": speed,
            "audio_config": {
                "sample_rate": 48000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav"
            }
        }

        response = requests.post(
            TTS_URL,
            headers={
                "X-API-Key-ID": GNANI_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=90
        )

        if not response.ok:
            return jsonify({
                "success": False,
                "error": "TTS service failed.",
                "details": response.text[:1000]
            }), response.status_code

        if not response.content:
            return jsonify({
                "success": False,
                "error": "TTS service returned empty audio."
            }), 502

        return send_file(
            io.BytesIO(response.content),
            mimetype="audio/wav",
            as_attachment=False,
            download_name="bharat_voice.wav"
        )

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "TTS request timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException as exc:
        app.logger.exception("TTS connection error")
        return jsonify({
            "success": False,
            "error": "Could not connect to Gnani TTS service.",
            "details": str(exc)
        }), 502

    except Exception as exc:
        app.logger.exception("TTS error")
        return jsonify({
            "success": False,
            "error": "An unexpected TTS error occurred.",
            "details": str(exc)
        }), 500


# ---------------------------------
# AI Brain - Gemini Chat
# ---------------------------------

def is_retryable_gemini_error(exc):
    """Identify temporary Gemini overload, rate-limit and server errors."""
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = None

    message = str(exc).upper()
    return (
        status in (408, 429, 500, 502, 503, 504)
        or any(token in message for token in (
            "503 UNAVAILABLE", "502 BAD GATEWAY", "504 GATEWAY TIMEOUT",
            "429 RESOURCE_EXHAUSTED", "SERVICE UNAVAILABLE", "HIGH DEMAND",
            "TIMED OUT", "TIMEOUT"
        ))
    )


def gemini_error_message(exc):
    """Return an actionable, safe English explanation for a Gemini failure."""
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = None

    message = str(exc).upper()
    if status in (401, 403) or "API_KEY" in message or "API KEY" in message:
        return "Gemini authentication failed. Check that GEMINI_API_KEY is valid and has API access enabled."
    if status == 404 or "NOT_FOUND" in message or "MODEL NOT FOUND" in message:
        return "The configured Gemini model is not available to this API key. Check GEMINI_MODEL in .env."
    if status == 429 or "RESOURCE_EXHAUSTED" in message or "QUOTA" in message:
        return "Gemini quota or rate limit has been reached. Wait a moment, then check your API quota and billing settings."
    if is_retryable_gemini_error(exc):
        return "Gemini is temporarily unavailable. Please try again in a moment."
    return "Gemini could not generate a response. Check the server log for the provider error."


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    if not gemini_client:
        return jsonify(
            success=False,
            error="Gemini API key not found. Check your .env file."
        ), 500

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")

    if not isinstance(user_message, str):
        return jsonify(success=False, error="Message must be a string."), 400

    user_message = user_message.strip()
    if not user_message:
        return jsonify(success=False, error="Please enter your message."), 400
    if len(user_message) > 5000:
        return jsonify(success=False, error="Message is too long. Maximum 5000 characters."), 400

    conversation_id = data.get("conversation_id")
    if conversation_id is not None:
        if (
            not isinstance(conversation_id, int)
            or isinstance(conversation_id, bool)
            or not db().execute(
                "SELECT 1 FROM conversations WHERE id=? AND user_id=?",
                (conversation_id, session["user_id"])
            ).fetchone()
        ):
            return jsonify(success=False, error="Invalid conversation."), 404

    language = data.get("language", "auto")
    language_instruction = {
        "hi": "Reply in English.",
        "en": "Reply in English.",
    }.get(language, "Reply in English.")

    prompt = f"""You are Bharat Voice AI, a helpful AI assistant.

Instructions:
- {language_instruction}
- Reply only in clear English, even when the user writes in another language.
- Keep answers clear, friendly and useful.
- Do not claim to perform actions you cannot perform.

User message:
{user_message}
"""

    # Try the configured primary model once, then an optional verified backup.
    # The SDK timeout is 18 seconds and SDK retries are limited to one attempt.
    models_to_try = [GEMINI_PRIMARY_MODEL]
    if GEMINI_BACKUP_MODEL and GEMINI_BACKUP_MODEL != GEMINI_PRIMARY_MODEL:
        models_to_try.append(GEMINI_BACKUP_MODEL)

    answer = None
    successful_model = None
    last_error = None

    for model_name in models_to_try:
        try:
            app.logger.info("Requesting Gemini model: %s", model_name)
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            answer = getattr(response, "text", None)
            if answer and answer.strip():
                successful_model = model_name
                break
            last_error = RuntimeError(f"Model {model_name} returned an empty response")
        except Exception as exc:
            last_error = exc
            app.logger.warning("Gemini model %s failed: %s", model_name, exc)

    if not answer or not answer.strip():
        if last_error:
            app.logger.error("All configured Gemini models failed: %s", last_error)
        return jsonify(
            success=False,
            temporary=bool(last_error and is_retryable_gemini_error(last_error)),
            error=gemini_error_message(last_error) if last_error else "Gemini returned an empty response. Please try again."
        ), 503 if last_error and is_retryable_gemini_error(last_error) else 502

    # Save only successful exchanges, scoped to the authenticated user.
    try:
        with db():
            if conversation_id is None:
                cursor = db().execute(
                    "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                    (session["user_id"], user_message[:65])
                )
                conversation_id = cursor.lastrowid
            else:
                owned = db().execute(
                    "SELECT id FROM conversations WHERE id=? AND user_id=?",
                    (conversation_id, session["user_id"])
                ).fetchone()
                if not owned:
                    return jsonify(success=False, error="Conversation not found."), 404

            db().execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "user", user_message)
            )
            db().execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, "assistant", answer)
            )
    except sqlite3.Error:
        app.logger.exception("Failed to save chat")
        return jsonify(
            success=False,
            error="The AI responded, but the chat history could not be saved. Please try again."
        ), 500

    return jsonify(
        success=True,
        reply=answer,
        conversation_id=conversation_id,
        model=successful_model
    ), 200


# ---------------------------------
# Upload Size Error
# ---------------------------------

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "success": False,
        "error": "Audio file is too large. Maximum size is 15 MB."
    }), 413


# ---------------------------------
# Run Application
# ---------------------------------

init_db()

if __name__ == "__main__":
    if not GNANI_API_KEY:
        print("WARNING: GNANI_API_KEY not found in .env file.")
    else:
        print("Gnani API Key Loaded Successfully.")

    if gemini_client:
        print("Gemini API Connected Successfully!")
    else:
        print("WARNING: GEMINI_API_KEY not found in .env file.")

    print("Bharat Voice AI is starting...")
    app.run(host="127.0.0.1", port=5000, debug=True)

