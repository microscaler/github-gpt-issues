import pytest
from github_gpt_issues.main import load_existing_actor_lines

class DummyIssue:
    def __init__(self, body):
        self.body = body

class DummyRepo:
    def __init__(self, issues):
        self._issues = issues
    def get_issues(self, state):
        # ignoring state, return simulated issues
        return self._issues


def test_load_existing_actor_lines_basic(monkeypatch, caplog):
    # Prepare dummy issues: some with actor lines, some without
    issues = [
        DummyIssue("As a user, want X\nDetails here."),
        DummyIssue("Random body without actor line."),
        DummyIssue(None),  # issue with no body
        DummyIssue("As an admin, perform Y\nMore text."),
    ]
    repo = DummyRepo(issues)

    caplog.set_level("INFO")
    existing = load_existing_actor_lines(repo)

    # Should extract only two actor lines
    assert "As a user, want X" in existing
    assert "As an admin, perform Y" in existing
    assert len(existing) == 2
    # Should log loaded count
    assert any("Loaded 2 existing actor lines." in rec.message for rec in caplog.records)


def test_load_existing_actor_lines_handles_exception(monkeypatch, caplog):
    # Simulate repo.get_issues raising
    class BadRepo:
        def get_issues(self, state):
            raise ValueError("GitHub down")
    bad_repo = BadRepo()

    caplog.set_level("WARNING")
    existing = load_existing_actor_lines(bad_repo)
    # Should return empty set on exception
    assert existing == set()
    # Should log a warning
    assert any("Failed to fetch existing issues" in rec.message for rec in caplog.records)
