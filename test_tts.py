
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        print("API Key missing!")
        return

    url = "https://api.vachana.ai/api/v1/tts/inference"
    headers = {
        "X-API-Key-ID": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": "नमस्ते! आपका स्वागत है भारत वॉइस एआई में। मैं आपकी कैसे मदद कर सकती हूँ?",
        "voice": "Nalini",
        "model": "timbre-v2.5",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=90
        )

        print("Status:", response.status_code)

        if response.status_code == 200:
            with open("output.wav", "wb") as file:
                file.write(response.content)

            print("Voice generated successfully!")
            print("Saved as output.wav")

        else:
            print("Error:", response.text)

    except requests.RequestException as error:
        print("Connection Error:", error)


if __name__ == "__main__":
    main()
