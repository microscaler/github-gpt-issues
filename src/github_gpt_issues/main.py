#!/usr/bin/env python3
"""
CLI entrypoint for github-gpt-issues.
Handles argument parsing, environment setup, and orchestration.
"""
import os
import sys

# Ensure the src directory is on PYTHONPATH for package imports

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))


import sys
import argparse
import logging
import re
from github import Github
from github import GithubException
from github_gpt_issues.core import parse_markdown, expand_story, create_milestone_and_issues

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_existing_actor_lines(repo):
    """Fetch existing 'As a ...' lines from all issue bodies."""
    pattern = re.compile(r'^(As an? .+)$', re.MULTILINE)
    existing = set()
    try:
        for issue in repo.get_issues(state="all"):
            body = getattr(issue, "body", None)
            if body:
                match = pattern.search(body)
                if match:
                    existing.add(match.group(1).strip())
        logger.info(f"Loaded {len(existing)} existing actor lines.")
    except Exception as e:
        logger.warning(f"Failed to fetch existing issues: {e}")
        return set()
    return existing



def main():
    parser = argparse.ArgumentParser(
        description="Create GitHub milestones & issues from user story markdown."
    )
    parser.add_argument("--markdown", help="Path to markdown file")
    parser.add_argument("--repo", help="GitHub repo (owner/repo)")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use for expansion")
    parser.add_argument("--run-tests", action="store_true", help="Run unit tests and exit")
    args = parser.parse_args()

    if args.run_tests:
        # Delegate to pytest
        import pytest
        sys.exit(pytest.main(["--maxfail=1", "--disable-warnings", "--cov=src"]))

    if not args.markdown or not args.repo:
        parser.error("--markdown and --repo are required unless --run-tests is set.")

    # Load environment variables
    gh_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not gh_token or not openai_key:
        logger.error("GITHUB_TOKEN and OPENAI_API_KEY must be set in environment.")
        sys.exit(1)
    import openai
    openai.api_key = openai_key

    # Init GitHub client
    try:
        gh = Github(gh_token)
        repo = gh.get_repo(args.repo)
    except Exception as e:
        logger.error(f"Error accessing repo {args.repo}: {e}")
        sys.exit(1)

    existing_actor_lines = load_existing_actor_lines(repo)

    # Read markdown
    try:
        with open(args.markdown, encoding='utf-8') as f:
            md = f.read()
    except Exception as e:
        logger.error(f"Failed to read markdown file: {e}")
        sys.exit(1)

    sections = parse_markdown(md)
    if not sections:
        logger.warning("No sections found in markdown. Exiting.")
        return

    # Create milestones & issues
    for sec in sections:
        create_milestone_and_issues(repo, sec, args.model, existing_actor_lines)


if __name__ == '__main__':
    main()
