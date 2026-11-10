
# import os
# import io
# import requests
# from google import genai
# from google import genai

# from pathlib import Path
# from dotenv import load_dotenv
# from flask import (
#     Flask,
#     request,
#     jsonify,
#     render_template,
#     send_file
# )

# # ---------------------------------
# # Configuration
# # ---------------------------------

# BASE_DIR = Path(__file__).resolve().parent

# load_dotenv(BASE_DIR / ".env")

# API_KEY = os.getenv("GNANI_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# if GEMINI_API_KEY:
#     gemini_client = genai.Client(api_key=GEMINI_API_KEY)
# else:
#     gemini_client = None
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# gemini_client = None

# if GEMINI_API_KEY:
#     gemini_client = genai.Client(
#         api_key=GEMINI_API_KEY
#     )
#     print("Gemini API Connected Successfully!")
# else:
#     print("WARNING: Gemini API Key Not Found!")

# STT_URL = "https://api.vachana.ai/stt/v3"
# TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"

# app = Flask(__name__)

# # Maximum audio upload size: 15 MB
# app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024


# # ---------------------------------
# # Home Page
# # ---------------------------------

# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------------------------------
# # API Key Check
# # ---------------------------------

# def check_api_key():
#     if not API_KEY:
#         return jsonify({
#             "success": False,
#             "error": "Gnani API key not found. Check your .env file."
#         }), 500

#     return None


# # ---------------------------------
# # Speech to Text (STT)
# # ---------------------------------

# @app.route("/api/transcribe", methods=["POST"])
# def transcribe():

#     key_error = check_api_key()

#     if key_error:
#         return key_error

#     try:
#         audio = request.files.get("audio")

#         if not audio or not audio.filename:
#             return jsonify({
#                 "success": False,
#                 "error": "Please upload an audio file."
#             }), 400

#         files = {
#             "audio_file": (
#                 audio.filename,
#                 audio.stream,
#                 audio.mimetype or "audio/wav"
#             )
#         }

#         form_data = {
#             "language_code": "hi-IN",
#             "format": "transcribe",
#             "itn_native_numerals": "true"
#         }

#         response = requests.post(
#             STT_URL,
#             headers={
#                 "X-API-Key-ID": API_KEY
#             },
#             files=files,
#             data=form_data,
#             timeout=90
#         )

#         try:
#             result = response.json()
#         except ValueError:
#             return jsonify({
#                 "success": False,
#                 "error": "STT service returned an invalid response.",
#                 "details": response.text[:500]
#             }), 502

#         if not response.ok:
#             return jsonify({
#                 "success": False,
#                 "error": result.get("message", "Speech recognition failed."),
#                 "details": result
#             }), response.status_code

#         return jsonify(result), 200

#     except requests.exceptions.Timeout:
#         return jsonify({
#             "success": False,
#             "error": "STT request timed out. Please try again."
#         }), 504

#     except requests.exceptions.RequestException as e:
#         return jsonify({
#             "success": False,
#             "error": "Could not connect to Gnani STT service.",
#             "details": str(e)
#         }), 502

#     except Exception as e:
#         app.logger.exception("STT error")
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500


# # ---------------------------------
# # Text to Speech (TTS)
# # ---------------------------------

# @app.route("/api/speak", methods=["POST"])
# def speak():

#     key_error = check_api_key()

#     if key_error:
#         return key_error

#     try:
#         data = request.get_json(silent=True) or {}

#         text_input = data.get("text", "").strip()

#         if not text_input:
#             return jsonify({
#                 "success": False,
#                 "error": "Please enter some text."
#             }), 400

#         payload = {
#             "text": text_input,
#             "voice": "Nalini",
#             "model": "timbre-v2.5",
#             "language": "hi-IN",
#             "speed": 1.0,
#             "audio_config": {
#                 "sample_rate": 48000,
#                 "num_channels": 1,
#                 "sample_width": 2,
#                 "encoding": "linear_pcm",
#                 "container": "wav"
#             }
#         }

#         response = requests.post(
#             TTS_URL,
#             headers={
#                 "X-API-Key-ID": API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json=payload,
#             timeout=90
#         )

#         if not response.ok:
#             return jsonify({
#                 "success": False,
#                 "error": "TTS service failed.",
#                 "details": response.text[:1000]
#             }), response.status_code

#         if not response.content:
#             return jsonify({
#                 "success": False,
#                 "error": "TTS service returned empty audio."
#             }), 502

#         return send_file(
#             io.BytesIO(response.content),
#             mimetype="audio/wav",
#             as_attachment=False,
#             download_name="bharat_voice.wav"
#         )

#     except requests.exceptions.Timeout:
#         return jsonify({
#             "success": False,
#             "error": "TTS request timed out. Please try again."
#         }), 504

#     except requests.exceptions.RequestException as e:
#         return jsonify({
#             "success": False,
#             "error": "Could not connect to Gnani TTS service.",
#             "details": str(e)
#         }), 502

#     except Exception as e:
#         app.logger.exception("TTS error")
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500



# # ---------------------------------
# # AI Brain - Gemini Chat
# # ---------------------------------

# @app.route("/api/chat", methods=["POST"])
# def chat():

#     if not gemini_client:
#         return jsonify({
#             "success": False,
#             "error": "Gemini API key not found."
#         }), 500

#     try:
#         data = request.get_json(silent=True) or {}
#         user_message = data.get("message", "").strip()

#         if not user_message:
#             return jsonify({
#                 "success": False,
#                 "error": "Please enter your message."
#             }), 400

#         if len(user_message) > 5000:
#             return jsonify({
#                 "success": False,
#                 "error": "Message is too long. Maximum 5000 characters."
#             }), 400

#         prompt = f"""
#         You are Bharat Voice AI, a helpful AI assistant.

#         Instructions:
#         - Reply in the same language as the user.
#         - Prefer simple Hindi or Hinglish when appropriate.
#         - Keep answers clear, friendly and useful.
#         - Do not claim to perform actions you cannot perform.

#         User message:
#         {user_message}
#         """

#         response = gemini_client.models.generate_content(
#             model="gemini-3.8-flash",
#             contents=prompt
#         )

#         answer = response.text

#         if not answer:
#             return jsonify({
#                 "success": False,
#                 "error": "Gemini returned an empty response."
#             }), 502

#         return jsonify({
#             "success": True,
#             "reply": answer
#         })

#     except Exception as e:
#         app.logger.exception("Gemini chat error")

#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500


# # ---------------------------------
# # Upload Size Error
# # ---------------------------------

# @app.errorhandler(413)
# def file_too_large(error):
#     return jsonify({
#         "success": False,
#         "error": "Audio file is too large. Maximum size is 15 MB."
#     }), 413


# # ---------------------------------
# # Run Application
# # ---------------------------------

# if __name__ == "__main__":

#     if not API_KEY:
#         print("WARNING: GNANI_API_KEY not found in .env file.")
#     else:
#         print("Gnani API Key Loaded Successfully.")

#     print("Bharat Voice AI is starting...")

#     app.run(
#         host="127.0.0.1",
#         port=5000,
#         debug=True
#     )


'''
+---------------------+
|      new file       |
+---------------------+
'''

import io
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
from google import genai

# ---------------------------------
# Configuration
# ---------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GNANI_API_KEY = os.getenv("GNANI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
GEMINI_MODEL = "gemini-3.8-flash"

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

# Create one Gemini client only.
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ---------------------------------
# Home Page
# ---------------------------------

@app.route("/")
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

@app.route("/api/chat", methods=["POST"])
def chat():
    if not gemini_client:
        return jsonify({
            "success": False,
            "error": "Gemini API key not found. Check your .env file."
        }), 500

    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "")

        if not isinstance(user_message, str):
            return jsonify({
                "success": False,
                "error": "Message must be a string."
            }), 400

        user_message = user_message.strip()

        if not user_message:
            return jsonify({
                "success": False,
                "error": "Please enter your message."
            }), 400

        if len(user_message) > 5000:
            return jsonify({
                "success": False,
                "error": "Message is too long. Maximum 5000 characters."
            }), 400

        prompt = f"""
You are Bharat Voice AI, a helpful AI assistant.

Instructions:
- Reply in the same language as the user.
- Prefer simple Hindi or Hinglish when appropriate.
- Keep answers clear, friendly and useful.
- Do not claim to perform actions you cannot perform.

User message:
{user_message}
"""

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        answer = response.text
        if not answer:
            return jsonify({
                "success": False,
                "error": "Gemini returned an empty response."
            }), 502

        return jsonify({
            "success": True,
            "reply": answer
        }), 200

    except Exception as exc:
        app.logger.exception("Gemini chat error")
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


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



# new code

import io
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
from google import genai

# ---------------------------------
# Configuration
# ---------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GNANI_API_KEY = os.getenv("GNANI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
GEMINI_MODEL = "gemini-3.8-flash"

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

# Create one Gemini client only.
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ---------------------------------
# Home Page
# ---------------------------------

@app.route("/")
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

@app.route("/api/chat", methods=["POST"])
def chat():
    if not gemini_client:
        return jsonify({
            "success": False,
            "error": "Gemini API key not found. Check your .env file."
        }), 500

    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "")

        if not isinstance(user_message, str):
            return jsonify({
                "success": False,
                "error": "Message must be a string."
            }), 400

        user_message = user_message.strip()

        if not user_message:
            return jsonify({
                "success": False,
                "error": "Please enter your message."
            }), 400

        if len(user_message) > 5000:
            return jsonify({
                "success": False,
                "error": "Message is too long. Maximum 5000 characters."
            }), 400

        prompt = f"""
You are Bharat Voice AI, a helpful AI assistant.

Instructions:
- Reply in the same language as the user.
- Prefer simple Hindi or Hinglish when appropriate.
- Keep answers clear, friendly and useful.
- Do not claim to perform actions you cannot perform.

User message:
{user_message}
"""

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        answer = response.text
        if not answer:
            return jsonify({
                "success": False,
                "error": "Gemini returned an empty response."
            }), 502

        return jsonify({
            "success": True,
            "reply": answer
        }), 200

    except Exception as exc:
        app.logger.exception("Gemini chat error")
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


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
