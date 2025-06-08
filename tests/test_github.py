import json
import tempfile
import os
from types import SimpleNamespace
import pytest
from github_gpt_issues.core import expand_story, create_milestone_and_issues

# The patch_openai fixture in conftest will automatically patch ChatCompletion.create

def test_expand_story_with_template(tmp_path):
    # Create a simple prompt template
    tpl = tmp_path / "prompt.md"
    tpl.write_text(
        "Generate a story for {{ actor_line }} with tone={{ tone }} and detail={{ detail_level }}"
    )
    # Call expand_story with template
    result = expand_story(
        "As a tester, want T",
        model="gpt-test",
        tone="friendly",
        detail_level="detailed",
        prompt_template_path=str(tpl)
    )
    # Since openai is patched, result should include actor_line and simulated description
    assert "As a tester, want T" in result
    assert "This is a description." in result

class DummyMilestone(SimpleNamespace):
    pass

class DummyIssue(SimpleNamespace):
    pass

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
        issue = DummyIssue(number=len(self.issues) + 1, title=title, body=body, milestone=milestone)
        self.issues.append(issue)
        return issue

@pytest.fixture
def dummy_repo():
    return DummyRepo()


def test_create_milestone_and_issues(dummy_repo, caplog):
    section = { 'title': 'Epic A', 'stories': ['As a dev, want A'] }
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
    # Logging occurred
    assert any("Created issue #" in record.message for record in caplog.records)


def test_skip_duplicate(dummy_repo, caplog):
    section = { 'title': 'Epic B', 'stories': ['As a user, want B'] }
    existing = {'As a user, want B'}
    caplog.set_level("INFO")

    create_milestone_and_issues(dummy_repo, section, model="gpt-test", existing_actor_lines=existing)

    # Should create milestone but skip issue
    assert len(dummy_repo.milestones) == 1
    assert len(dummy_repo.issues) == 0
    # Log skip
    assert any("Skipping duplicate actor_line" in record.message for record in caplog.records)
