import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")

if __name__ == "__main__":
    if not API_KEY:
        print("ERROR: Gemini API key not found in .env")
        raise SystemExit(1)

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=API_KEY)
    print("Bharat Voice AI - Gemini Test")
    print("--------------------------------")

    try:
        response = client.models.generate_content(
            model=model,
            contents="Namaste! Apna introduction Hindi mein do. Tum Bharat Voice AI ke AI assistant ho."
        )

        print("\nGemini Response:")
        print(response.text)

    except Exception as e:
        print("\nGemini API Error:")
        print(str(e))

    finally:
        client.close()