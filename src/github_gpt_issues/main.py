# src/github_gpt_issues/main.py
#!/usr/bin/env python3
"""
CLI entrypoint for github-gpt-issues.
Parses args, sets up clients, and orchestrates core functions.
"""
import os
import sys
import argparse
import logging
import re
import openai
from github import Github, GithubException
from github_gpt_issues.core import (
    parse_markdown,
    create_milestone_and_issues
)

# Ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_existing_actor_lines(repo):
    pattern = re.compile(r'^(As an? .+)$', re.MULTILINE)
    existing = set()
    try:
        for issue in repo.get_issues(state="all"):
            body = getattr(issue, "body", "") or ""
            m = pattern.search(body)
            if m:
                existing.add(m.group(1).strip())
        logger.info(f"Loaded {len(existing)} existing actor lines.")
    except Exception as e:
        logger.warning(f"Failed to fetch existing issues: {e}")
        return set()
    return existing


def main():
    parser = argparse.ArgumentParser(description="Create GitHub issues from markdown stories")
    parser.add_argument("--markdown", required=True, help="Path to user-stories markdown")
    parser.add_argument("--repo", required=True, help="GitHub repo (owner/repo)")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use")
    parser.add_argument("--prompt-template", help="Path to Jinja2 prompt template")
    parser.add_argument("--tone", default="neutral", help="Tone for generated stories")
    parser.add_argument("--detail-level", default="medium", help="Detail level for generated stories")
    parser.add_argument("--cache-file", help="Path to JSON cache file for story expansions")
    parser.add_argument("--run-tests", action="store_true", help="Run pytest and exit")
    args = parser.parse_args()

    if args.run_tests:
        import pytest
        sys.exit(pytest.main(["--maxfail=1", "--disable-warnings", "--cov=src"]))

    gh_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not gh_token or not openai_key:
        logger.error("GITHUB_TOKEN and OPENAI_API_KEY must be set")
        sys.exit(1)
    openai.api_key = openai_key

    try:
        gh = Github(gh_token)
        repo = gh.get_repo(args.repo)
    except Exception as e:
        logger.error(f"Error accessing repo {args.repo}: {e}")
        sys.exit(1)

    existing = load_existing_actor_lines(repo)

    try:
        md = open(args.markdown, encoding="utf-8").read()
    except Exception as e:
        logger.error(f"Failed to read markdown file: {e}")
        sys.exit(1)

    sections = parse_markdown(md)
    if not sections:
        logger.warning("No sections found. Exiting.")
        sys.exit(0)

    for sec in sections:
        create_milestone_and_issues(
            repo,
            sec,
            args.model,
            existing,
            tone=args.tone,
            detail_level=args.detail_level,
            prompt_template_path=args.prompt_template,
            cache_file=args.cache_file
        )


if __name__ == "__main__":
    main()
