import pytest
import json
import openai
from github_gpt_issues.core import (
    _retry,
    RateLimitError,
    APIError,
    expand_stories_batch,
)


# Dummy function to simulate API errors and successes
def flaky_func_factory(failures, exception_type):
    state = {"calls": 0}

    def func():  # <- fix: remove *args
        state["calls"] += 1
        if state["calls"] <= failures:
            raise exception_type("Rate limit hit")
        return "success"

    func.state = state
    return func


class DummyFunctionCall:
    def __init__(self, arguments):
        self.arguments = arguments


class DummyChoice:
    def __init__(self, message):
        self.message = message


class DummyMessage:
    def __init__(self, function_call=None, content=None):
        self.function_call = function_call
        self.content = content

    def get(self, key, default=None):
        return getattr(self, key, default)


class DummyResponse:
    def __init__(self, choice):
        self.choices = [choice]


@pytest.fixture(autouse=True)
def patch_openai_batch(monkeypatch):
    """Patch openai.ChatCompletion.create for batch tests"""
    import github_gpt_issues.core as core_module

    def fake_batch_create(*args, **kwargs):
        # Validate batch prompt
        messages = kwargs.get("messages", [])
        user_msg = next((m for m in messages if m["role"] == "user"), {})
        assert "- A1\n- A2" in user_msg.get("content", "")

        # Simulate structured batch function_call
        payload = {
            "stories": [
                {
                    "actor_line": "A1",
                    "description": "Desc1",
                    "acceptance_criteria": ["C1"],
                },
                {
                    "actor_line": "A2",
                    "description": "Desc2",
                    "acceptance_criteria": ["C2"],
                },
            ]
        }
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_batch_create)


def test_expand_stories_batch_success():
    actor_lines = ["A1", "A2"]
    result = expand_stories_batch(actor_lines, model="gpt-test")
    assert isinstance(result, dict)
    assert result["A1"].startswith("A1")
    assert "Desc1" in result["A1"]
    assert result["A2"].startswith("A2")
    assert "Desc2" in result["A2"]


def test_expand_stories_batch_empty(monkeypatch):
    """Empty input returns empty dict without API call"""
    calls = {"batch": 0}

    def fake_create(*args, **kwargs):
        calls["batch"] += 1

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_create)
    result = expand_stories_batch([], model="gpt-test")
    assert result == {}
    assert calls["batch"] == 0


def test_expand_stories_batch_fallback(monkeypatch):
    """Fallback to expand_story for single or batch failures"""
    import github_gpt_issues.core as core_module

    # Force batch call to raise
    monkeypatch.setattr(
        openai.ChatCompletion,
        "create",
        lambda *a, **k: (_ for _ in ()).throw(openai.error.RateLimitError()),
    )
    # Patch expand_story to return predictable mapping
    monkeypatch.setattr(
        core_module, "expand_story", lambda *args, **kwargs: f"story_{args[0]}"
    )
    # Single-item fallback
    single = expand_stories_batch(["X1"], model="gpt-test")
    assert single == {"X1": "story_X1"}
    # Multi-item fallback
    multi = expand_stories_batch(["X1", "X2"], model="gpt-test")
    assert multi == {"X1": "story_X1", "X2": "story_X2"}


def test_retry_succeeds_after_retries(monkeypatch):
    """_retry should retry on RateLimitError with no delay"""

    func = flaky_func_factory(failures=2, exception_type=RateLimitError)
    monkeypatch.setattr("time.sleep", lambda s: None)

    # ✅ Just pass the callable, don't pre-invoke it
    res = _retry(func, max_retries=3, initial_delay=2, backoff_multiplier=3)

    assert res == "success"
    assert func.state["calls"] == 3


def test_retry_raises_after_max(monkeypatch):

    func = flaky_func_factory(failures=5, exception_type=APIError)
    monkeypatch.setattr("time.sleep", lambda s: None)

    with pytest.raises(APIError):
        _retry(lambda: func(), max_retries=3, initial_delay=1, backoff_multiplier=2)

    assert func.state["calls"] == 4  # 1 initial + 3 retries


def test_expand_stories_batch_malformed_json(monkeypatch, caplog):
    """
    If the batch function_call.arguments is invalid JSON,
    expand_stories_batch should catch it, warn, and fall back
    to individual expand_story calls.
    """
    import github_gpt_issues.core as core_module
    from types import SimpleNamespace

    # 1) Fake a ChatCompletion response with a bad JSON payload
    class BadMsg:
        def __init__(self):
            self.function_call = SimpleNamespace(
                name="create_user_stories_batch",
                arguments='{"stories": [INVALID JSON]}',
            )
            self.content = None

    class BadChoice:
        def __init__(self):
            self.message = BadMsg()

    class BadResp:
        def __init__(self):
            self.choices = [BadChoice()]

    # 2) Patch openai to return that response
    monkeypatch.setattr(openai.ChatCompletion, "create", lambda *a, **k: BadResp())

    # 3) Patch expand_story so we can detect fallback calls
    monkeypatch.setattr(
        core_module,
        "expand_story",
        lambda actor_line, **kwargs: f"story_for_{actor_line}",
    )

    caplog.set_level("WARNING")
    result = core_module.expand_stories_batch(["X1", "X2"], model="gpt-test")

    # We should have fallen back to expand_story for each actor_line
    assert result == {
        "X1": "story_for_X1",
        "X2": "story_for_X2",
    }

    # And a warning was logged about the batch failure
    assert any("Batch expand failed" in rec.message for rec in caplog.records)


def test_expand_stories_batch_raw_content_fallback(monkeypatch):
    """When batch API returns raw content without function_call, delegate to expand_story."""
    import github_gpt_issues.core as core_module
    from types import SimpleNamespace

    # 1) Fake ChatCompletion.create to return a message with content but no function_call
    raw_content = "Some random text that doesn't match function_call"

    def fake_create(*args, **kwargs):
        class Msg:
            content = raw_content

            def get(self, key, default=None):
                return False

        class Choice:
            message = Msg()

        return SimpleNamespace(choices=[Choice()])

    monkeypatch.setattr(openai.ChatCompletion, "create", fake_create)

    # 2) Stub out expand_story to verify it's used
    monkeypatch.setattr(core_module, "expand_story", lambda a, **k: f"story_{a}")

    # 3) Run batch on two actor lines
    result = core_module.expand_stories_batch(["X1", "X2"], model="gpt-test")

    # 4) Since raw_content doesn’t split into per-story blocks, we should see fall-back
    assert result == {"X1": "story_X1", "X2": "story_X2"}
