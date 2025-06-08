import pytest
import json
from types import SimpleNamespace
import openai
from github_gpt_issues.core import expand_stories_batch, _retry, expand_story

# Dummy function to simulate API errors and successes
def flaky_func_factory(failures, exception_type):
    state = {'calls': 0}
    def func(*args, **kwargs):
        state['calls'] += 1
        if state['calls'] <= failures:
            raise exception_type("Rate limit hit")
        return "success"
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
def patch_openai(monkeypatch):
    """Patch openai.ChatCompletion.create for batch tests"""
    import github_gpt_issues.core as core_module

    def fake_batch_create(*args, **kwargs):
        # Simulate structured batch function_call
        payload = {'stories': [
            {'actor_line': 'A1', 'description': 'Desc1', 'acceptance_criteria': ['C1']},
            {'actor_line': 'A2', 'description': 'Desc2', 'acceptance_criteria': ['C2']},
        ]}
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    monkeypatch.setattr(core_module.openai.ChatCompletion, 'create', fake_batch_create)


def test_expand_stories_batch_success():
    actor_lines = ['A1', 'A2']
    result = expand_stories_batch(actor_lines, model='gpt-test')
    assert isinstance(result, dict)
    assert result['A1'].startswith('A1')
    assert 'Desc1' in result['A1']
    assert result['A2'].startswith('A2')
    assert 'Desc2' in result['A2']


def test_expand_stories_batch_fallback(monkeypatch):
    # Simulate batch API raising, fallback to expand_story
    import github_gpt_issues.core as core_module
    # Force batch call to raise
    monkeypatch.setattr(
        core_module.openai.ChatCompletion,
        'create',
        lambda *a, **k: (_ for _ in ()).throw(openai.error.RateLimitError())
    )
    # Patch expand_story to return a predictable mapping for any args
    monkeypatch.setattr(core_module, 'expand_story', lambda *args, **kwargs: f"story_{args[0]}")

    actor_lines = ['X1', 'X2']
    result = expand_stories_batch(actor_lines, model='gpt-test')
    assert result == {'X1': 'story_X1', 'X2': 'story_X2'}


def test_retry_succeeds_after_retries():
    # Simulate two failures then success
    func = flaky_func_factory(failures=2, exception_type=openai.error.RateLimitError)
    res = _retry(func, max_retries=3, initial_delay=0, backoff=1)
    assert res == 'success'


def test_retry_raises_after_max():
    # Simulate always failing
    func = flaky_func_factory(failures=5, exception_type=openai.error.APIError)
    with pytest.raises(openai.error.APIError):
        _retry(func, max_retries=3, initial_delay=0, backoff=1)
