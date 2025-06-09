import pytest
import json

from github_gpt_issues.core import parse_markdown, expand_story


# Dummy classes to simulate OpenAI response
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
    """Automatically patch openai.ChatCompletion.create for expand_story"""
    import github_gpt_issues.core as core_module

    def fake_create(model, messages, functions, function_call):
        # Simulate a valid function_call response
        payload = {
            "actor_line": messages[-1]["content"].splitlines()[0],
            "description": "This is a description.",
            "acceptance_criteria": ["First criterion", "Second criterion"],
        }
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    monkeypatch.setattr(core_module.openai.ChatCompletion, "create", fake_create)


def test_parse_markdown_basic():
    md = """
## 1. Section One
1.1. **As a user, want X**
1.2. **As an admin, want Y**

## 2. Section Two
2.1. **As a tester, want Z**
"""
    sections = parse_markdown(md)
    assert len(sections) == 2
    sec1 = sections[0]
    assert sec1["number"] == "1"
    assert sec1["title"] == "Section One"
    assert sec1["stories"] == ["As a user, want X", "As an admin, want Y"]
    sec2 = sections[1]
    assert sec2["number"] == "2"
    assert sec2["title"] == "Section Two"
    assert sec2["stories"] == ["As a tester, want Z"]


def test_expand_story_structured():
    actor = "As a user, want X"
    body = expand_story(actor, model="gpt-test")
    assert actor in body
    assert "This is a description." in body
    assert "**Acceptance Criteria:**" in body
    assert "- First criterion" in body
    assert "- Second criterion" in body


def test_expand_story_fallback(monkeypatch):
    import github_gpt_issues.core as core_module

    def raise_error(*args, **kwargs):
        raise ValueError("API down")

    monkeypatch.setattr(core_module.openai.ChatCompletion, "create", raise_error)
    actor = "As a user, want Y"
    body = expand_story(actor, model="gpt-test")
    assert actor in body
    assert "Failed to expand story" in body


def test_retry_non_retryable_error():
    """ValueError should not be retried by _retry"""
    from github_gpt_issues.core import _retry

    calls = {"count": 0}

    def bad():
        calls["count"] += 1
        raise ValueError("fatal error")

    import pytest

    with pytest.raises(ValueError):
        _retry(bad)
    assert calls["count"] == 1
