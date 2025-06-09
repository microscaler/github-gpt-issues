# tests/test_core_extended.py

import pytest
import json
from types import SimpleNamespace
from github_gpt_issues.core import expand_story, create_milestone_and_issues

# The patch_openai fixture is provided in conftest.py


def test_expand_story_with_template(tmp_path):
    # Create a simple prompt template
    tpl = tmp_path / "prompt.md"
    tpl.write_text(
        "Generate a story for {{ actor_line }} with tone={{ tone }} and detail={{ detail_level }}"
    )
    body = expand_story(
        actor_line="As a tester, want T",
        model="gpt-test",
        tone="friendly",
        detail_level="detailed",
        prompt_template_path=str(tpl),
    )
    assert "As a tester, want T" in body
    assert "This is a description." in body


# Dummy classes for milestone and issue creation
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
        issue = DummyIssue(
            number=len(self.issues) + 1, title=title, body=body, milestone=milestone
        )
        self.issues.append(issue)
        return issue


@pytest.fixture
def dummy_repo():
    return DummyRepo()


def test_create_milestone_and_issues(dummy_repo):
    section = {"title": "Epic A", "stories": ["As a dev, want A"]}
    existing = set()

    create_milestone_and_issues(
        dummy_repo, section, model="gpt-test", existing_actor_lines=existing
    )

    # Milestone created
    assert len(dummy_repo.milestones) == 1
    assert dummy_repo.milestones[0].title == "Epic A"
    # Issue created
    assert len(dummy_repo.issues) == 1
    issue = dummy_repo.issues[0]
    assert issue.title == "As a dev, want A"
    assert "As a dev, want A" in issue.body
    assert issue.milestone.title == "Epic A"
    # existing_actor_lines updated
    assert "As a dev, want A" in existing


def test_skip_duplicate(dummy_repo):
    section = {"title": "Epic B", "stories": ["As a user, want B"]}
    existing = {"As a user, want B"}

    create_milestone_and_issues(
        dummy_repo, section, model="gpt-test", existing_actor_lines=existing
    )

    # Milestone created but no issues
    assert len(dummy_repo.milestones) == 1
    assert len(dummy_repo.issues) == 0
