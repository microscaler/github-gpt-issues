#!/usr/bin/env python3
"""
Core functionality for github-gpt-issues:
- parse_markdown
- expand_story (single) with caching and retry
- expand_stories_batch (batch)
- create_milestone_and_issues
"""
import functools
import os
import json
import re
import openai
import time
import random
import logging


# Gracefully handle missing openai.error for tests
# fmt: off
try:
    from openai.error import RateLimitError, APIError
except ImportError:
    # openai.error not available: define dummy exception classes so only these are retryable
    class RateLimitError(Exception):
        """Dummy RateLimitError for retry logic"""
        pass

    class APIError(Exception):
        """Dummy APIError for retry logic"""
        pass
# fmt: on

from github import GithubException

logger = logging.getLogger(__name__)


def parse_markdown(markdown_text):
    """
    Parse sections and user-story actor lines from markdown text.

    Returns:
      List[Dict]: each dict has keys: 'number', 'title', 'stories'
    """
    section_pattern = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)
    story_pattern = re.compile(r"^\s*\d+\.\d+\.\s*\*\*(.+?)\*\*", re.MULTILINE)
    sections = []
    current = None
    for line in markdown_text.splitlines():
        sec = section_pattern.match(line)
        if sec:
            current = {
                "number": sec.group(1),
                "title": sec.group(2).strip(),
                "stories": [],
            }
            sections.append(current)
        elif current:
            st = story_pattern.match(line)
            if st:
                current["stories"].append(st.group(1).strip())

    return sections


def _retry(
    func,
    *args,
    max_retries=3,
    initial_delay=1.0,
    backoff_multiplier=2.0,
    jitter=False,
    **kwargs,
):
    delay = initial_delay
    retryable_exceptions = (RateLimitError, APIError, GithubException)
    callable_func = (
        func if not args and not kwargs else functools.partial(func, *args, **kwargs)
    )

    for attempt in range(max_retries + 1):
        try:
            return callable_func()
        except retryable_exceptions as e:
            if attempt == max_retries:
                logger.error(f"Retry failed after {max_retries} attempts: {e}")
                raise
            wait = delay * (1 + random.random()) if jitter else delay
            logger.warning(
                f"{type(e).__name__} on attempt {attempt + 1}/{max_retries}: {e}. Retrying in {wait:.2f}s..."
            )
            time.sleep(wait)
            delay *= backoff_multiplier
            continue
        except Exception as e:
            logger.error(f"Non-retryable exception: {e}")
            raise
    return None


def expand_story(
    actor_line,
    model="gpt-4",
    tone="neutral",
    detail_level="medium",
    prompt_template_path=None,
    cache_file=None,
):
    cache = {}
    if cache_file and os.path.exists(cache_file):
        try:
            cache = json.loads(open(cache_file, "r", encoding="utf-8").read())
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
        else:
            if actor_line in cache:
                return cache[actor_line]

    user_content = actor_line
    if prompt_template_path:
        try:
            from jinja2 import Template

            tpl = Template(open(prompt_template_path, encoding="utf-8").read())
            user_content = tpl.render(
                actor_line=actor_line, tone=tone, detail_level=detail_level
            )
        except ImportError:
            logger.warning("jinja2 missing; using actor_line only")
        except Exception as e:
            logger.warning(f"Template error: {e}; using actor_line only")

    try:
        resp = _retry(
            lambda: openai.ChatCompletion.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert product manager writing user stories.",
                    },
                    {"role": "user", "content": user_content},
                ],
                functions=[
                    {
                        "name": "create_user_story",
                        "description": "Generate structured user story",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "actor_line": {"type": "string"},
                                "description": {"type": "string"},
                                "acceptance_criteria": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [
                                "actor_line",
                                "description",
                                "acceptance_criteria",
                            ],
                        },
                    }
                ],
                function_call="auto",
            )
        )
        msg = resp.choices[0].message
        if msg.get("function_call"):
            data = json.loads(msg.function_call.arguments)
            body = f"{data['actor_line']}\n\n{data['description']}\n\n**Acceptance Criteria:**\n"
            for crit in data["acceptance_criteria"]:
                body += f"- {crit}\n"
        else:
            text = (msg.content or "").strip()
            body = text if text.startswith(actor_line) else f"{actor_line}\n\n{text}"
    except Exception as e:
        logger.error(f"expand_story API failed: {e}")
        body = f"{actor_line}\n\n**Failed to expand story**"

    if cache_file:
        try:
            cache[actor_line] = body
            open(cache_file, "w", encoding="utf-8").write(json.dumps(cache, indent=2))
        except Exception as e:
            logger.warning(f"Could not write cache: {e}")
    return body


def expand_stories_batch(
    actor_lines,
    model="gpt-4",
    tone="neutral",
    detail_level="medium",
    prompt_template_path=None,
):
    if not actor_lines:
        return {}

    batch_text = "Generate complete user stories for:\n" + "\n".join(
        f"- {a}" for a in actor_lines
    )
    user_content = batch_text
    if prompt_template_path:
        try:
            from jinja2 import Template

            tpl = Template(open(prompt_template_path, encoding="utf-8").read())
            header = tpl.render(actor_line="", tone=tone, detail_level=detail_level)
            user_content = header + "\n\n" + batch_text
        except Exception as e:
            logger.warning(f"Batch template error ({e}); continuing without template")

    try:
        resp = _retry(
            lambda: openai.ChatCompletion.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert product manager writing user stories.",
                    },
                    {"role": "user", "content": user_content},
                ],
                functions=[
                    {
                        "name": "create_user_stories_batch",
                        "description": "Generate structured user stories in batch",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "stories": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "actor_line": {"type": "string"},
                                            "description": {"type": "string"},
                                            "acceptance_criteria": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                        "required": [
                                            "actor_line",
                                            "description",
                                            "acceptance_criteria",
                                        ],
                                    },
                                }
                            },
                            "required": ["stories"],
                        },
                    }
                ],
                function_call="auto",
            )
        )
        msg = resp.choices[0].message
        if msg.get("function_call"):
            try:
                payload = json.loads(msg.function_call.arguments)
                stories = payload.get("stories")
                if not isinstance(stories, list):
                    raise ValueError("Missing or invalid 'stories' key")
                out = {}
                for entry in stories:
                    al = entry["actor_line"]
                    body = (
                        f"{al}\n\n{entry['description']}\n\n**Acceptance Criteria:**\n"
                    )
                    for crit in entry["acceptance_criteria"]:
                        body += f"- {crit}\n"
                    out[al] = body
                return out
            except Exception as e:
                logger.warning(
                    f"Batch expand got unexpected payload: {e}; falling back to individual calls"
                )
    except Exception as e:
        logger.warning(f"Batch expand failed ({e}); falling back to individual calls")

    # fallback to individual expansion
    return {
        a: expand_story(
            a,
            model=model,
            tone=tone,
            detail_level=detail_level,
            prompt_template_path=prompt_template_path,
        )
        for a in actor_lines
    }


def create_milestone_and_issues(
    repo,
    section,
    model,
    existing_actor_lines,
    tone="neutral",
    detail_level="medium",
    prompt_template_path=None,
    cache_file=None,
):
    epic = section["title"]
    try:
        milestone = _retry(lambda: repo.create_milestone(title=epic))
    except GithubException:
        try:
            all_ms = _retry(lambda: repo.get_milestones())
        except Exception as ge:
            logger.error(f"Failed to fetch milestones: {ge}")
            return
        milestone = next((m for m in all_ms if m.title == epic), None)
        if not milestone:
            logger.error(f"Can't find or create milestone '{epic}'")
            return

    new_lines = [a for a in section["stories"] if a not in existing_actor_lines]
    if not new_lines:
        return

    bodies = expand_stories_batch(
        new_lines,
        model=model,
        tone=tone,
        detail_level=detail_level,
        prompt_template_path=prompt_template_path,
    )

    for al in new_lines:
        body = bodies.get(al, f"{al}\n\n**Failed to expand story**")
        title = al if len(al) <= 50 else al[:47] + "..."
        try:
            issue = _retry(
                lambda: repo.create_issue(title=title, body=body, milestone=milestone)
            )
            existing_actor_lines.add(al)
            logger.info(f"Created issue #{issue.number} for '{al}'")
        except GithubException as e:
            logger.error(f"Issue creation failed for '{al}': {e}")
