# src/github_gpt_issues/main.py
#!/usr/bin/env python3
"""
CLI for github-gpt-issues, now supporting batching and rate-limit retry.
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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_existing_actor_lines(repo):
    pattern = re.compile(r'^(As an? .+)$', re.MULTILINE)
    existing = set()
    try:
        for issue in repo.get_issues(state="all"):
            body = issue.body or ""
            m = pattern.search(body)
            if m:
                existing.add(m.group(1))
    except Exception as e:
        logger.warning(f"Failed to load existing issues: {e}")
    return existing


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--markdown", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--model", default="gpt-4")
    p.add_argument("--prompt-template")
    p.add_argument("--tone", default="neutral")
    p.add_argument("--detail-level", default="medium")
    p.add_argument("--cache-file")
    p.add_argument("--run-tests", action="store_true")
    args = p.parse_args()

    if args.run_tests:
        import pytest; sys.exit(pytest.main(["--maxfail=1", "--disable-warnings", "--cov=src"]))

    gh_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not (gh_token and openai_key):
        logger.error("Set GITHUB_TOKEN & OPENAI_API_KEY"); sys.exit(1)
    openai.api_key = openai_key

    try:
        repo = Github(gh_token).get_repo(args.repo)
    except Exception as e:
        logger.error(f"GitHub access error: {e}"); sys.exit(1)

    existing = load_existing_actor_lines(repo)
    md = open(args.markdown, encoding="utf-8").read()
    sections = parse_markdown(md)
    for sec in sections:
        create_milestone_and_issues(
            repo, sec, args.model, existing,
            tone=args.tone,
            detail_level=args.detail_level,
            prompt_template_path=args.prompt_template,
            cache_file=args.cache_file
        )


if __name__ == "__main__":
    main()
