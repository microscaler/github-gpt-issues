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


def test_expand_story_raw_fallback(monkeypatch):
    import github_gpt_issues.core as core
    from tests.conftest import DummyResponse, DummyChoice, DummyMessage
    # Simulate raw content response without function_call
    def fake_raw(*args, **kwargs):
        return DummyResponse(DummyChoice(DummyMessage(content="Extra details here")))
    monkeypatch.setattr(core.openai.ChatCompletion, 'create', fake_raw)

    actor = "As a user, want raw"
    result = core.expand_story(actor)
    assert actor in result
    assert "Extra details here" in result


def test_expand_story_prefixed(monkeypatch):
    import github_gpt_issues.core as core
    from tests.conftest import DummyResponse, DummyChoice, DummyMessage
    # Simulate response starting with actor_line
    actor = "As a user, already"
    def fake_prefixed(*args, **kwargs):
        # Properly escape newline in content string
        return DummyResponse(DummyChoice(DummyMessage(content=actor + "More info")))
    monkeypatch.setattr(core.openai.ChatCompletion, 'create', fake_prefixed)

    result = core.expand_story(actor)
    # Actor line appears only once and body includes extra text
    assert result.count(actor) == 1
    assert "More info" in result
