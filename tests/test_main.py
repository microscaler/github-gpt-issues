import json
import tempfile
from pathlib import Path
import pytest
from github_gpt_issues.main import load_existing_actor_lines

class DummyIssue:
    def __init__(self, body):
        self.body = body

class DummyRepo:
    def __init__(self, issues):
        self._issues = issues
    def get_issues(self, state):
        return self._issues


def test_load_existing_actor_lines_basic(caplog):
    issues = [
        DummyIssue("As a user, want X Details here."),
        DummyIssue("Random body without actor line."),
        DummyIssue(None),  # no body
        DummyIssue("As an admin, perform Y More text."),
    ]
    repo = DummyRepo(issues)
    caplog.set_level("INFO")

    existing = load_existing_actor_lines(repo)

    # Should extract the full matched lines
    assert existing == {
        "As a user, want X Details here.",
        "As an admin, perform Y More text."
    }

def test_load_existing_actor_lines_handles_exception(caplog):
    class BadRepo:
        def get_issues(self, state):
            raise ValueError("GitHub down")
    bad_repo = BadRepo()

    caplog.set_level("WARNING")
    existing = load_existing_actor_lines(bad_repo)

    assert existing == set()
    assert any("Failed to load existing issues" in rec.message for rec in caplog.records)

