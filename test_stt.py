import os
import requests
from dotenv import load_dotenv
load_dotenv()
def main():
    api_key = os.getenv("GNANI_API_KEY")
    url = "https://api.vachana.ai/stt/v3"
    audio_path = "sample.wav"
    if not api_key:
        print("API Key missing!")
    elif not os.path.exists(audio_path):
        print("sample.wav file not found!")
    else:
        headers = {"X-API-Key-ID": api_key}

        with open(audio_path, "rb") as audio:
            files = {
                "audio_file": ("sample.wav", audio, "audio/wav")
            }

            data = {
                "language_code": "hi-IN",
                "preferred_language": "hi-IN",
                "format": "transcribe",
                "itn_native_numerals": "true"
            }

            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=90
            )
        print("Status:", response.status_code)
        print("Response:", response.text)


if __name__ == "__main__":
    main()
