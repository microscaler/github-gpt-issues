import json
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


def test_load_existing_actor_lines_empty(caplog):
    """When get_issues returns no issues, should return empty set with no warnings"""
    class EmptyRepo:
        def get_issues(self, state):
            return []
    repo = EmptyRepo()

    caplog.set_level("INFO")
    existing = load_existing_actor_lines(repo)

    assert existing == set()
    # No warnings logged
    assert not caplog.records


def test_multiple_actor_lines_only_first(caplog):
    """If an issue body contains multiple actor lines, only the first is captured"""
    multiline_body = (
        "As a user, want A\n"
        "As an admin, perform B\n"
        "Details..."
    )
    issues = [DummyIssue(multiline_body)]
    repo = DummyRepo(issues)
    caplog.set_level("INFO")

    existing = load_existing_actor_lines(repo)

    assert existing == {"As a user, want A"}


def test_whitespace_trim(caplog):
    """Extra whitespace around actor line should be trimmed"""
    issues = [
        DummyIssue("  As a tester, want X   ")
    ]
    repo = DummyRepo(issues)
    caplog.set_level("INFO")

    existing = load_existing_actor_lines(repo)

    assert existing == {"As a tester, want X"}
