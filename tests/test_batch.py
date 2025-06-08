import pytest
import json
import openai
from github_gpt_issues.core import expand_stories_batch, _retry

# Dummy function to simulate API errors and successes
def flaky_func_factory(failures, exception_type):
    state = {'calls': 0}
    def func(*args, **kwargs):
        state['calls'] += 1
        if state['calls'] <= failures:
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
        messages = kwargs.get('messages', [])
        user_msg = next((m for m in messages if m['role']=='user'), {})
        assert '- A1\n- A2' in user_msg.get('content','')

        # Simulate structured batch function_call
        payload = {'stories': [
            {'actor_line': 'A1', 'description': 'Desc1', 'acceptance_criteria': ['C1']},
            {'actor_line': 'A2', 'description': 'Desc2', 'acceptance_criteria': ['C2']},
        ]}
        func_call = DummyFunctionCall(arguments=json.dumps(payload))
        message = DummyMessage(function_call=func_call)
        return DummyResponse(DummyChoice(message))

    monkeypatch.setattr(openai.ChatCompletion, 'create', fake_batch_create)


def test_expand_stories_batch_success():
    actor_lines = ['A1', 'A2']
    result = expand_stories_batch(actor_lines, model='gpt-test')
    assert isinstance(result, dict)
    assert result['A1'].startswith('A1')
    assert 'Desc1' in result['A1']
    assert result['A2'].startswith('A2')
    assert 'Desc2' in result['A2']


def test_expand_stories_batch_empty(monkeypatch):
    """Empty input returns empty dict without API call"""
    calls = {'batch':0}
    def fake_create(*args, **kwargs): calls['batch']+=1
    monkeypatch.setattr(openai.ChatCompletion, 'create', fake_create)
    result = expand_stories_batch([], model='gpt-test')
    assert result == {}
    assert calls['batch'] == 0


def test_expand_stories_batch_fallback(monkeypatch):
    """Fallback to expand_story for single or batch failures"""
    import github_gpt_issues.core as core_module
    # Force batch call to raise
    monkeypatch.setattr(openai.ChatCompletion, 'create', lambda *a, **k: (_ for _ in ()).throw(openai.error.RateLimitError()))
    # Patch expand_story to return predictable mapping
    monkeypatch.setattr(core_module, 'expand_story', lambda *args, **kwargs: f"story_{args[0]}")

    # Single-item fallback
    single = expand_stories_batch(['X1'], model='gpt-test')
    assert single == {'X1':'story_X1'}
    # Multi-item fallback
    multi = expand_stories_batch(['X1','X2'], model='gpt-test')
    assert multi == {'X1':'story_X1','X2':'story_X2'}


def test_retry_succeeds_after_retries(monkeypatch):
    """_retry should retry on RateLimitError with no delay"""
    func = flaky_func_factory(failures=2, exception_type=openai.error.RateLimitError)
    # Speed up sleep
    monkeypatch.setattr('time.sleep', lambda s: None)
    res = _retry(func, max_retries=3, initial_delay=0, backoff=1)
    assert res == 'success'
    # Ensure retries occurred
    assert func.state['calls'] == 3


def test_retry_raises_after_max(monkeypatch):
    """_retry should raise after exceeding max_retries"""
    func = flaky_func_factory(failures=5, exception_type=openai.error.APIError)
    monkeypatch.setattr('time.sleep', lambda s: None)
    with pytest.raises(openai.error.APIError):
        _retry(func, max_retries=3, initial_delay=0, backoff=1)
    assert func.state['calls'] == 3
