Bharat Voice AI - Local run

1. Install dependencies with: pip install -r requirements.txt
2. Keep GNANI_API_KEY and GEMINI_API_KEY in C:\app\.env.
3. Start the server with: python app.py
4. Open http://127.0.0.1:5000/signup and create an account.

Gemini chat uses GEMINI_MODEL (default: gemini-3.8-flash) and falls back to
GEMINI_BACKUP_MODEL (default: gemini-3.6-flash). Set GEMINI_BACKUP_MODEL= in
.env to disable fallback. A working API key and available provider quota are
still required.

Run offline chat checks with: python -m unittest test_chat
These tests mock Gemini and do not call external APIs.


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