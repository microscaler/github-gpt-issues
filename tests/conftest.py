# tests/conftest.py
import sys
import os

# Ensure src directory is on sys.path for imports in tests
SRC_PATH = os.path.abspath(os.path.join(os.getcwd(), 'src'))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import pytest
import json
from types import SimpleNamespace

# Dummy classes for OpenAI function-calling simulation
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

@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    """Automatically patch openai.ChatCompletion.create for all tests"""
    import github_gpt_issues.core as core_module

    def fake_create(*args, **kwargs):
        # Build payload using the last user message
        messages = kwargs.get('messages') or []
        actor_line = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                actor_line = msg.get('content')
                break
        payload = {
            'actor_line': actor_line or '',
            'description': 'This is a description.',
            'acceptance_criteria': ['First criterion', 'Second criterion']
        }
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    # Patch the ChatCompletion.create method
    monkeypatch.setattr(core_module.openai.ChatCompletion, 'create', fake_create)
