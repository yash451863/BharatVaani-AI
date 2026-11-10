import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import app as app_module


class ProviderError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class FakeModels:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def generate_content(self, *, model, contents):
        self.calls.append((model, contents))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)


class FakeGemini:
    def __init__(self, results):
        self.models = FakeModels(results)


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = app_module.DB_PATH
        self.original_gemini_client = app_module.gemini_client
        app_module.DB_PATH = Path(self.temp_dir.name) / "test.db"
        app_module.init_db()

        with app_module.app.app_context():
            with app_module.db() as connection:
                cursor = connection.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    ("Test User", "test@example.com", "not-used"),
                )
                self.user_id = cursor.lastrowid

        self.client = app_module.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id

    def tearDown(self):
        app_module.DB_PATH = self.original_db_path
        app_module.gemini_client = self.original_gemini_client
        self.temp_dir.cleanup()

    def test_chat_uses_backup_model_after_primary_failure(self):
        fake = FakeGemini([
            ProviderError(404, "model not found"),
            "Namaste! Main aapki madad kar sakta hoon.",
        ])
        app_module.gemini_client = fake

        response = self.client.post("/api/chat", json={"message": "Namaste"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertEqual(response.json["reply"], "Namaste! Main aapki madad kar sakta hoon.")
        self.assertEqual(
            [call[0] for call in fake.models.calls],
            [app_module.GEMINI_PRIMARY_MODEL, app_module.GEMINI_BACKUP_MODEL],
        )
        conversations = self.client.get("/api/conversations").json["conversations"]
        self.assertEqual(len(conversations), 1)
        messages = self.client.get(
            f"/api/conversations/{response.json['conversation_id']}/messages"
        ).json["messages"]
        self.assertEqual([message["role"] for message in messages], ["user", "assistant"])

    def test_chat_reports_quota_errors_without_saving_failed_message(self):
        app_module.gemini_client = FakeGemini([
            ProviderError(429, "RESOURCE_EXHAUSTED"),
            ProviderError(429, "RESOURCE_EXHAUSTED"),
        ])

        response = self.client.post("/api/chat", json={"message": "Hello"})

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json["temporary"])
        self.assertIn("quota", response.json["error"].lower())
        history = self.client.get("/api/conversations")
        self.assertEqual(history.json["conversations"], [])

    def test_chat_rejects_non_object_json(self):
        app_module.gemini_client = FakeGemini(["This should not be used"])

        response = self.client.post("/api/chat", json=["not", "an", "object"])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(app_module.gemini_client.models.calls), 0)


if __name__ == "__main__":
    unittest.main()
