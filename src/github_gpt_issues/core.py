#!/usr/bin/env python3
"""
Core functionality for github-gpt-issues:
- parse_markdown
- expand_story with optional Jinja2 prompt template
- create_milestone_and_issues
"""
import json
import re
import logging
import openai
from github import GithubException

logger = logging.getLogger(__name__)


def parse_markdown(markdown_text):
    """
    Parse sections and user-story actor lines from markdown text.

    Returns:
      List[Dict]: each dict has keys: 'number', 'title', 'stories' (list of actor_line strings)
    """
    section_pattern = re.compile(r'^##\s+(\d+)\.\s+(.+)$', re.MULTILINE)
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
                current['stories'].append(st.group(1).strip())
    return sections


def expand_story(actor_line, model="gpt-4", tone="neutral", detail_level="medium", prompt_template_path=None):
    """
    Expand an actor_line into a full user story using OpenAI function-calling.

    Supports optional prompt template via Jinja2, customizing tone and detail level.
    Returns a markdown body starting with the actor_line, a description, and acceptance criteria.
    """
    # Prepare the user prompt
    user_content = actor_line
    if prompt_template_path:
        try:
            from jinja2 import Template
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                tpl_content = f.read()
            tpl = Template(tpl_content)
            user_content = tpl.render(
                actor_line=actor_line,
                tone=tone,
                detail_level=detail_level
            )
        except ImportError:
            logger.warning("jinja2 not installed; falling back to actor_line only.")
        except Exception as e:
            logger.warning(f"Error with prompt template ({e}); falling back to actor_line only.")

    # Call the API
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert product manager writing clear user stories."},
                {"role": "user", "content": user_content}
            ],
            functions=[{
                "name": "create_user_story",
                "description": "Generate a structured user story output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "actor_line": {"type": "string"},
                        "description": {"type": "string"},
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["actor_line", "description", "acceptance_criteria"]
                }
            }],
            function_call="auto"
        )
        msg = response.choices[0].message
        # Structured path
        if msg.get("function_call"):
            payload = json.loads(msg.function_call.arguments)
            body = (
                f"{payload['actor_line']}\n\n"
                f"{payload['description']}\n\n**Acceptance Criteria:**\n"
            )
            for crit in payload['acceptance_criteria']:
                body += f"- {crit}\n"
            return body

        # Fallback to raw content
        text = msg.content.strip() if msg.content else ""
        if not text.startswith(actor_line):
            text = f"{actor_line}\n\n{text}"
        return text

    except Exception as e:
        logger.error(f"OpenAI request failed for '{actor_line}': {e}")
        return f"{actor_line}\n\n**Failed to expand story**"


def create_milestone_and_issues(repo, section, model, existing_actor_lines):
    """
    Create a milestone for the given section and issues for each new actor_line in that section.

    Skips actor_lines already in existing_actor_lines.
    """
    epic = section['title']
    try:
        milestone = repo.create_milestone(title=epic)
        logger.info(f"Created milestone: {epic}")
    except GithubException:
        # Try to fetch it if it already exists
        milestone = next((m for m in repo.get_milestones() if m.title == epic), None)
        if not milestone:
            logger.error(f"Could not create or find milestone '{epic}'. Skipping.")
            return

    for actor_line in section['stories']:
        if actor_line in existing_actor_lines:
            logger.info(f"Skipping duplicate actor_line: {actor_line}")
            continue
        logger.info(f"Expanding & creating issue for: {actor_line}")
        body = expand_story(actor_line, model=model)
        title = actor_line if len(actor_line) <= 50 else actor_line[:47] + "..."
        try:
            issue = repo.create_issue(title=title, body=body, milestone=milestone)
            existing_actor_lines.add(actor_line)
            logger.info(f"Created issue #{issue.number} for '{actor_line}'")
        except GithubException as e:
            logger.error(f"Failed to create issue for '{actor_line}': {e}")
