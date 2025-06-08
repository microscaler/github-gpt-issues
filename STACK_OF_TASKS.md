# Stack of Refinement Tasks for GitHub Story Creator

## 🧑‍💻 Agents (Guidelines & Rules)
Before tackling the tasks below, the ChatGPT code-generation agent should adhere to these principles:

- **Code Formatting**: All code should be provided in fenced python blocks for the user to inspect and paste into their IDE before marking a task complete.
- **Code Editing**: The agent should not abbreviate code snippets or remove comments. The user should be able to see the full context of changes made.
- **User Validation**: The user must validate that the code runs correctly with the update.
- **Dependency Management**: `requirements.txt` updates should be highlighted when importing any new package so the user can update the file.
- **Test Coverage**: Ensure the script is covered by unit tests at ≥80%. Use `pytest` and `pytest-cov`, integrate coverage checks in CI.
- **Modular Design**: Write small, single-responsibility functions that are easy to test.
- **Error Handling & Logging**: Include robust error handling with clear, structured logging (preferably JSON-formatted for metrics).
- **Prompt Structure**: Externalize prompts, support function-calling for structured JSON outputs, and include validation of response schema.
- **Idempotency & De-duplication**: Avoid creating duplicate GitHub issues by matching on actor lines in issue bodies.
- **Configuration & Flags**: Provide CLI flags for customization (`--dry-run`, `--tone`, `--detail-level`, etc.) and external configuration files.
- **Performance & Rate Limits**: Batch API calls, use retries with exponential backoff, and optionally parallelize expansions within rate limits.
- **Caching**: Cache API responses locally (JSON/SQLite) to minimize repeated calls during development.

---

## 1. Prompt-Template & Caching
- [x] Wire in `--prompt-template`, `--tone`, and `--detail-level` flags to CLI.
- [x] Add Jinja2-based prompt rendering in `expand_story`.
- [x] Implement JSON‐file caching of `actor_line` → story body.
- [x] Write tests for cache hits and writes.

## 2. CI & Test Coverage
- [x] Configure `pytest.ini` with `testpaths` and `python_paths`.
- [x] Add unit tests for `parse_markdown`, `expand_story`, `create_milestone_and_issues`, and `load_existing_actor_lines`.
- [x] Achieve ≥80% coverage on `core.py`.

## 3. Batch API Calls & Rate-Limit Handling
- [x] Group multiple `actor_line`s into a single ChatCompletion batch request.
- [ ] Split the combined response back into individual story bodies.
- [ ] Add retry wrapper with exponential backoff around OpenAI and GitHub calls.

### 3.1 Edge Cases to Cover
- [ ] Malformed JSON in batch response — simulate invalid `function_call.arguments` and fallback gracefully.
- [ ] Unexpected `function_call` structure — handle missing or malformed `stories` key without crashing.
- [ ] Batch raw-content fallback — simulate responses using `msg.content` and ensure delegation to `expand_story`.
- [ ] Non-retryable errors in `_retry` (e.g., generic `ValueError`) should not be retried.
- [ ] Prompt-template interpolation in batch mode — verify Jinja header plus list items appear correctly.
- [ ] Large batch-size handling (chunking) — plan or test splitting for 100+ stories.
- [ ] Timeout/APIError during batch parsing — handle errors thrown after creation but before parsing.
- [ ] Duplicate `actor_line`s in batch input — ensure unique output keys.

## 4. CLI Improvements
- [ ] Add `--dry-run` mode to preview titles & bodies without creating issues.
- [ ] Support `--cache-file` flag in CLI to enable/disable caching.

## 5. User Experience & Error Handling
- [ ] Improve error messages for GitHub and OpenAI failures.
- [ ] Show progress/status logs for long-running operations.

## 6. Documentation & Examples
- [ ] Update `README.md` with batching and retry sections.
- [ ] Add sample prompt-template in `docs/`.
- [ ] Provide example markdown and CLI command in `docs/`.

---

_Last updated: 2025-06-09_
