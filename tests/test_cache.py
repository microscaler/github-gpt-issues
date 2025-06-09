import json
import tempfile
from pathlib import Path
import pytest
from github_gpt_issues.core import expand_story

# import Dummy classes and patch fixture
from tests.conftest import DummyResponse, DummyChoice, DummyMessage, DummyFunctionCall
import github_gpt_issues.core as core_module


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    """Patch OpenAI create, by default returning a structured payload for testing write-to-cache."""

    def fake_create(*args, **kwargs):
        payload = {
            "actor_line": kwargs.get("messages")[-1]["content"],
            "description": "Cached description",
            "acceptance_criteria": ["Crit1", "Crit2"],
        }
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    monkeypatch.setattr(core_module.openai.ChatCompletion, "create", fake_create)


def test_expand_story_cache_hit(tmp_path):
    # Prepopulate cache file
    cache_file = tmp_path / "story_cache.json"
    existing = {"As a user, want A": "Pre-cached body"}
    cache_file.write_text(json.dumps(existing))

    # Monkeypatch OpenAI to error if called
    import github_gpt_issues.core as core

    def error_call(*args, **kwargs):
        raise RuntimeError("OpenAI should not be called when cache hits")

    pytest.MonkeyPatch().setattr(core.openai.ChatCompletion, "create", error_call)

    result = expand_story("As a user, want A", cache_file=str(cache_file))
    assert result == "Pre-cached body"


def test_expand_story_cache_write(tmp_path):
    # Fresh cache file
    cache_file = tmp_path / "story_cache2.json"
    cache_file.unlink(missing_ok=True)

    # Expand a new story; write to cache
    actor = "As a user, want B"
    result = expand_story(actor, cache_file=str(cache_file))
    # Check returned body from fake_create
    assert "Cached description" in result

    # Verify cache file created and contains the new entry
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert actor in data
    assert data[actor] == result
