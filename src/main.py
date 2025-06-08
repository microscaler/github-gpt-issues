#!/usr/bin/env python3
"""
Script to parse a markdown file of Photon PaaS user stories, expand each story via OpenAI ChatCompletion,
and create GitHub milestones and issues accordingly.

Supports unit tests via --run-tests flag.

Dependencies:
  pip install PyGithub openai

Usage:
  export GITHUB_TOKEN="<your token>"
  export OPENAI_API_KEY="<your key>"
  python create_gh_issues.py --markdown user_stories.md --repo owner/repo
  python create_gh_issues.py --run-tests   # to run unit tests
"""
import os
import re
import sys
import argparse
import logging
import openai
from github import Github, GithubException
import unittest

# Configure basic logging
typical_format = '%(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=typical_format)


def parse_markdown(markdown_text):
    """
    Parse sections and stories from markdown.
    Returns list of dicts: { number, title, stories: [actor_line, ...] }
    """
    section_pattern = re.compile(r'^##\s+(\d+)\.\s+(.+)', re.MULTILINE)
    story_pattern = re.compile(r'^\s*\d+\.\d+\.\s*\*\*(.+?)\*\*', re.MULTILINE)
    sections = []
    current = None
    for line in markdown_text.splitlines():
        sec = section_pattern.match(line)
        if sec:
            current = {"number": sec.group(1), "title": sec.group(2).strip(), "stories": []}
            sections.append(current)
        elif current:
            st = story_pattern.match(line)
            if st:
                # st.group(1) is the actor line, e.g., "As a user, ..."
                current['stories'].append(st.group(1).strip())
    return sections


def expand_story(actor_line, model="gpt-4"):  # or gpt-3.5-turbo
    """
    Use OpenAI to expand a short actor_line into a full user story body.
    Returns the expanded story text or a fallback message on failure.
    The actor_line is preserved at the start of the body.
    """
    prompt = (
        f"Write a complete user story starting with the following actor line, including a brief description and acceptance criteria:\n\n{actor_line}"
    )
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert product manager writing clear user stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        body = resp.choices[0].message.content.strip()
        # Ensure original actor_line is first
        if not body.startswith(actor_line):
            body = f"{actor_line}\n\n{body}"
        return body
    except Exception as e:
        logging.error(f"OpenAI request failed for '{actor_line}': {e}")
        return f"{actor_line}\n\n**Failed to expand story**"


def create_milestone_and_issues(repo, section, model, existing_actor_lines):
    """
    Create a GitHub milestone for the section and issues for each new story.
    Skips stories whose actor_line already exists in the repo issues.
    """
    epic = section['title']
    try:
        milestone = repo.create_milestone(title=epic)
        logging.info(f"Created milestone: {epic}")
    except GithubException as e:
        logging.warning(f"Milestone '{epic}' exists or failed to create: {e}")
        milestone = next((m for m in repo.get_milestones() if m.title == epic), None)
        if not milestone:
            logging.error(f"Could not find or create milestone '{epic}', skipping section.")
            return

    for actor_line in section['stories']:
        if actor_line in existing_actor_lines:
            logging.info(f"Story with actor line '{actor_line}' already exists. Skipping duplicate.")
            continue
        logging.info(f"Expanding story: {actor_line}")
        full_body = expand_story(actor_line, model=model)
        # Use actor_line as issue title (first 50 chars)
        issue_title = actor_line if len(actor_line) <= 50 else actor_line[:47] + '...'
        logging.info(f"Creating issue for: {issue_title}")
        try:
            issue = repo.create_issue(
                title=issue_title,
                body=full_body,
                milestone=milestone
            )
            logging.info(f"Created issue #{issue.number} for '{actor_line}'")
            existing_actor_lines.add(actor_line)
        except GithubException as e:
            logging.error(f"Failed to create issue '{actor_line}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Create GitHub milestones & issues from user story markdown.")
    parser.add_argument("--markdown", help="Path to markdown file")
    parser.add_argument("--repo", help="GitHub repo in format owner/repo")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use for expansion")
    parser.add_argument("--run-tests", action="store_true", help="Run unit tests and exit")
    args = parser.parse_args()

    if args.run_tests:
        unittest.main(argv=[sys.argv[0]], exit=False)
        return

    if not args.markdown or not args.repo:
        parser.error("--markdown and --repo are required unless --run-tests is set.")

    gh_token = os.getenv("GITHUB_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not gh_token or not openai_key:
        logging.error("GITHUB_TOKEN and OPENAI_API_KEY must be set in environment.")
        sys.exit(1)
    openai.api_key = openai_key

    try:
        gh = Github(gh_token)
        repo = gh.get_repo(args.repo)
    except Exception as e:
        logging.error(f"Error accessing repo {args.repo}: {e}")
        sys.exit(1)

    # Build set of existing actor lines from issue bodies
    existing_actor_lines = set()
    actor_line_pattern = re.compile(r'^(As a .+)$', re.MULTILINE)
    try:
        for issue in repo.get_issues(state="all"):
            if issue.body:
                match = actor_line_pattern.search(issue.body)
                if match:
                    existing_actor_lines.add(match.group(1).strip())
        logging.info(f"Loaded {len(existing_actor_lines)} existing actor lines.")
    except Exception as e:
        logging.warning(f"Failed to fetch existing issues: {e}")

    try:
        with open(args.markdown, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        logging.error(f"Error reading markdown file '{args.markdown}': {e}")
        sys.exit(1)

    sections = parse_markdown(text)
    if not sections:
        logging.warning("No sections parsed from markdown. Exiting.")
        return

    for sec in sections:
        create_milestone_and_issues(repo, sec, args.model, existing_actor_lines)


# Unit Tests
class TestParser(unittest.TestCase):
    SAMPLE_MD = """
## 1. Section One
1.1. **As a user, want X**
1.2. **As an admin, want Y**
"""
    def test_parse_markdown(self):
        sections = parse_markdown(self.SAMPLE_MD)
        print(sections)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['stories'], ['As a user, want X', 'As an admin, want Y'])

class TestExpand(unittest.TestCase):
    def test_expand_story_output(self):
        result = expand_story('As a tester, want Z', model='gpt-3.5-turbo')
        print(result)
        self.assertTrue(result.startswith('As a tester,'))

if __name__ == '__main__':
    main()
