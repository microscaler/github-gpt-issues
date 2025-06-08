import pytest
import json
import tempfile
from types import SimpleNamespace
from github_gpt_issues.core import expand_story, create_milestone_and_issues

# Test template rendering and structured output

def test_expand_story_with_template(tmp_path):
    # Create a simple Jinja prompt template file
    tpl = tmp_path / "prompt.md"
    tpl.write_text(
        "Generate a story for {{ actor_line }} with tone={{ tone }} and detail={{ detail_level }}"
    )
    # Call expand_story with the template
    body = expand_story(
        actor_line="As a tester, want T",
        model="gpt-test",
        tone="friendly",
        detail_level="detailed",
        prompt_template_path=str(tpl)
    )
    assert "As a tester, want T" in body
    assert "This is a description." in body

# Dummy classes for milestone and issue creation
class DummyMilestone(SimpleNamespace): pass
class DummyIssue(SimpleNamespace): pass

class DummyRepo:
    def __init__(self):
        self.milestones = []
        self.issues = []
    def create_milestone(self, title):
        m = DummyMilestone(title=title)
        self.milestones.append(m)
        return m
    def get_milestones(self):
        return self.milestones
    def create_issue(self, title, body, milestone):
        issue = DummyIssue(number=len(self.issues)+1, title=title, body=body, milestone=milestone)
        self.issues.append(issue)
        return issue

@pytest.fixture
def dummy_repo():
    return DummyRepo()

# Test milestone and issue creation logic

def test_create_milestone_and_issues(dummy_repo, caplog):
    section = {'title': 'Epic A', 'stories': ['As a dev, want A']}
    existing = set()
    caplog.set_level("INFO")

    create_milestone_and_issues(dummy_repo, section, model="gpt-test", existing_actor_lines=existing)

    # Milestone created
    assert len(dummy_repo.milestones) == 1
    assert dummy_repo.milestones[0].title == 'Epic A'
    # Issue created
    assert len(dummy_repo.issues) == 1
    issue = dummy_repo.issues[0]
    assert issue.title == 'As a dev, want A'
    assert 'As a dev, want A' in issue.body
    assert issue.milestone.title == 'Epic A'
    # existing_actor_lines updated
    assert 'As a dev, want A' in existing
    assert any("Created issue #" in rec.message for rec in caplog.records)

# Test skipping duplicates

def test_skip_duplicate(dummy_repo, caplog):
    section = {'title': 'Epic B', 'stories': ['As a user, want B']}
    existing = {'As a user, want B'}
    caplog.set_level("INFO")

    create_milestone_and_issues(dummy_repo, section, model="gpt-test", existing_actor_lines=existing)

    # Milestone created but no issues
    assert len(dummy_repo.milestones) == 1
    assert len(dummy_repo.issues) == 0
    assert any("Skipping duplicate actor_line" in rec.message for rec in caplog.records)

# Test fallback raw content path

def test_expand_story_raw_fallback(monkeypatch):
    import github_gpt_issues.core as core
    from tests.conftest import DummyResponse, DummyChoice, DummyMessage
    # Simulate raw content response
    def fake_raw(*args, **kwargs):
        return DummyResponse(DummyChoice(DummyMessage(content="Extra details here")))
    monkeypatch.setattr(core.openai.ChatCompletion, 'create', fake_raw)

    actor = "As a user, want raw"
    result = core.expand_story(actor)
    assert actor in result
    assert "Extra details here" in result

# Test avoiding double prefix

def test_expand_story_prefixed(monkeypatch):
    import github_gpt_issues.core as core
    from tests.conftest import DummyResponse, DummyChoice, DummyMessage
    actor = "As a user, already"
    def fake_prefixed(*args, **kwargs):
        return DummyResponse(DummyChoice(DummyMessage(content=actor + "\nMore info")))
    monkeypatch.setattr(core.openai.ChatCompletion, 'create', fake_prefixed)

    result = core.expand_story(actor)
    assert result.count(actor) == 1
    assert "More info" in result
