# Stack of Refinement Tasks for GitHub Story Creator

## 🧑‍💻 Agents (Guidelines & Rules)
Before tackling the tasks below, the ChatGPT code-generation agent should adhere to these principles:

- **Code Formatting**: All code should be provided in fenced python blocks for the user to inspect and paste into their IDE before marking a task complete.
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

Below is the prioritized stack of tasks, **ordered by recommended implementation sequence** (highest priority first). We can check off each item as it’s completed.

1. [ ] **Implement Function-Calling for Structured Output**
   - [ ] Define a JSON schema for the user story (`actor_line`, `description`, `acceptance_criteria`)
   - [ ] Use OpenAI function-calling to get structured responses
   - [ ] Parse and format the JSON into the issue body template

2. [ ] **Introduce Prompt Template Customization**
   - [ ] Extract the system/user prompt into an external file or CLI flag
   - [ ] Support multiple prompt templates (e.g. BDD style, performance-focused)
   - [ ] Load and interpolate variables (tone, length) into the prompt

3. [ ] **Add Response Caching**
   - [ ] Create a local cache (JSON or SQLite) mapping `actor_line` → GPT response
   - [ ] On script startup, load cache; before any API call, check cache first
   - [ ] After a successful expansion, write back to cache

4. [ ] **Batch API Calls & Rate-Limit Handling**
   - [ ] Group N `actor_line`s into a single ChatCompletion request
   - [ ] Split the multi-response into individual story bodies
   - [ ] Implement exponential backoff and retry logic on rate limits

5. [ ] **Model Fallback & Quality Checks**
   - [ ] Validate GPT response includes `actor_line` and an `Acceptance Criteria` section
   - [ ] If validation fails, retry on same or fallback model (e.g. `gpt-3.5-turbo`)
   - [ ] Log low-confidence cases for manual review

6. [ ] **Interactive Preview Mode**
   - [ ] Add a `--dry-run` flag that prints `title` + `body` for each issue
   - [ ] Prompt `Create this issue? [Y/n]` before calling GitHub
   - [ ] Summarize skipped duplicates at end

7. [ ] **Template Snippets & Automated Labeling**
   - [ ] Define a Jinja or markdown template for issue bodies, including front-matter metadata
   - [ ] Apply default labels (e.g. `user-story`, `epic-<section>`)
   - [ ] Inject these snippets via the prompt or post-process

8. [ ] **Enhanced Logging & Metrics**
   - [ ] Wrap ChatCompletion calls with timing and token-usage logging
   - [ ] Output structured logs (JSON) for later analysis
   - [ ] Track total token counts and API latencies

9. [ ] **Parallel Execution**
   - [ ] Use `concurrent.futures` to expand multiple stories concurrently
   - [ ] Respect OpenAI concurrency limits
   - [ ] Collect and aggregate results/errors

10. [ ] **User-Driven Tone & Length Flags**
    - [ ] Add CLI flags `--tone` and `--detail-level`
    - [ ] Interpolate these values into the prompt (e.g. “Write in a {tone} tone, with {detail_level} detail.”)

---

**Next Steps:** Let me know which task you’d like to tackle first, or if you’d like to reorder/prioritize!
