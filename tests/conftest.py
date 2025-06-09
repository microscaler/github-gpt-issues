# tests/conftest.py

import sys
import os
import openai
import types

# ──────────────────────────────────────────────────────────────────────────────
# Polyfill openai.error for compatibility with core.py’s retry wrapper
# ──────────────────────────────────────────────────────────────────────────────
openai.error = types.ModuleType("openai.error")
openai.error.RateLimitError = Exception
openai.error.APIError = Exception

# ──────────────────────────────────────────────────────────────────────────────
# Ensure src/ is on the PYTHONPATH so github_gpt_issues can be imported
# ──────────────────────────────────────────────────────────────────────────────
SRC_PATH = os.path.abspath(os.path.join(os.getcwd(), "src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import pytest  # noqa: E402
import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────────
# Dummy classes to simulate OpenAI function responses
# ──────────────────────────────────────────────────────────────────────────────


class DummyFunctionCall:
    def __init__(self, arguments):
        self.arguments = arguments


class DummyChoice:
    def __init__(self, message):
        self.message = message


class DummyMessage:
    def __init__(self, content=None, function_call=None):
        self.content = content
        self.function_call = function_call

    def get(self, key, default=None):
        return getattr(self, key, default)


class DummyResponse:
    def __init__(self, choice):
        self.choices = [choice]


# ──────────────────────────────────────────────────────────────────────────────
# Global fixture to patch openai.ChatCompletion.create
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    """
    Automatically patch openai.ChatCompletion.create for all tests.
    Returns a structured payload by default.
    """
    import github_gpt_issues.core as core_module

    def fake_create(*args, **kwargs):
        # Grab the last user message as actor_line
        messages = kwargs.get("messages", [])
        actor_line = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                actor_line = msg.get("content", "")
                break

        payload = {
            "actor_line": actor_line,
            "description": "This is a description.",
            "acceptance_criteria": ["First criterion", "Second criterion"],
        }
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    monkeypatch.setattr(core_module.openai.ChatCompletion, "create", fake_create)
