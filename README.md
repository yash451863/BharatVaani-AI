# Bharat Voice AI · SQLite Accounts Edition

Flask AI voice assistant with Gnani STT/TTS, Gemini chat, animated frontend, SQLite user accounts and per-user chat history.

## Install
1. Back up your current `C:\app` folder.
2. Extract this archive into `C:\app` (overwrite `app.py`, `templates/`, `static/`; keep your `.env`).
3. In PowerShell: `cd C:\app`, `.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt`, `python app.py`.
4. Open `http://127.0.0.1:5000/signup` and create an account.
5. Sign in, send chat messages, create a new chat, open/delete old chats.

## Notes
- `.env` must include `GNANI_API_KEY` and `GEMINI_API_KEY`. Do not upload `.env` or `.flask_secret`.
- `bharat_voice.db` is created automatically in project folder. Do not commit it.
- Passwords are stored as hashes, not plaintext. Users see only their own chats.
- Chat messages are stored only when Gemini returns a successful response.
- Chat uses `GEMINI_MODEL` (default: `gemini-3.8-flash`) and falls back to `GEMINI_BACKUP_MODEL` (default: `gemini-3.6-flash`). Set `GEMINI_BACKUP_MODEL=` in `.env` to disable fallback.
- Chat errors distinguish API-key access, model availability, quota limits and temporary provider outages. A valid API key and available quota are still required.
- Voice recordings are sent to the Gnani API but are not saved to SQLite.
- This is a local demo implementation, **not** production-ready authentication or payment infrastructure. Before public deployment add HTTPS, request throttling, security monitoring, backups, and hardened configuration.
- Existing browser-local chat history is **not** imported into SQLite.
- Premium pricing is only a visual preview, not active subscriptions.

## Run the offline chat tests
Run `python -m unittest test_chat` from `C:\app`. These tests use a temporary SQLite database and mocked Gemini responses; they do not call paid external APIs.


# Bharat Voice AI

An AI-powered Hindi voice assistant.

## Technology Stack
- Python
- Flask
- SQLite
- Gemini API
- Gnani Prisma STT
- Gnani Timbre TTS
- HTML, CSS, JavaScript

## Features
- User Signup and Login
- User Profile Management
- Profile Picture Upload
- AI Chat Assistant
- Hindi Speech-to-Text
- Text-to-Speech
- Conversation History

## Run Locally
1. Install requirements
2. Configure API keys in .env
3. Run python app.py
4. Open http://127.0.0.1:5000


🚀 Introducing Bharat Voice AI, my AI-powered voice assistant built using Gnani AI technologies.

The goal of this project is to make AI more accessible through Hindi and voice-based interaction.

Key Features:

- AI-powered conversations
- Hindi Speech-to-Text using Gnani Prisma
- Text-to-Speech using Gnani Timbre
- User accounts and profile management
- Conversation history

Technology Stack: Python, Flask, SQLite, HTML, CSS, JavaScript and Gemini API.

This project helped me explore AI integration, speech technologies and full-stack development.

Built as part of the Great Indian AI Internship Challenge.

#GnaniAI #GreatIndianAIInternshipChallenge #ArtificialIntelligence #VoiceAI #Python #BuildInPublic