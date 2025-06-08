# github-gpt-issues

A CLI tool that turns a simple markdown file of user-story lines into fully-formed GitHub issues, powered by the OpenAI API.

---

## What

`github-gpt-issues` reads a markdown file containing user-story actor lines (e.g. `1.1. **As a user, I want X**`), sends each actor line to ChatGPT to generate a complete story (description + acceptance criteria), and then creates:

* A GitHub **milestone** per markdown section
* A GitHub **issue** per user story, with the generated body

It uses PyGithub to talk to GitHub and the OpenAI Python SDK to call ChatGPT.

---

## Why

* **Speed up backlog creation**: Draft hundreds of issues from a simple list in minutes
* **Consistency & structure**: Each story follows the same template (actor → description → acceptance criteria)
* **Reduce manual work**: Let AI fill in the details, you focus on planning and prioritisation

---

## How

### Prerequisites

* **Python 3.8+**
* **GitHub personal access token** with `repo` scopes
* **OpenAI API key**

### Install

```bash
git clone https://github.com/microscaler/github-gpt-issues.git
cd github-gpt-issues
pip install -r requirements/requirements.txt
```

### Configure

```bash
export GITHUB_TOKEN="ghp_..."
export OPENAI_API_KEY="sk-..."
```

### Usage

```bash
# Generate issues from a markdown file into a GitHub repo
python src/main.py \
  --markdown path/to/user_stories.md \
  --repo your-org/your-repo

# Run the built-in unit tests
python src/main.py --run-tests
```

#### Common Flags

* `--model` – Which OpenAI model to use (default `gpt-4`)
* `--dry-run` – Preview titles + bodies without creating issues
* `--tone`, `--detail-level` – Customize prompt (coming soon)

---

## Project Structure

```
├── LICENSE
├── README.md
├── STACK_OF_TASKS.md           # Roadmap of future enhancements
├── docs/
├── requirements/
│   └── requirements.txt        # Python dependencies
├── src/
│   ├── __init__.py
│   └── main.py                 # Main script
└── tests/                      # Unit tests (pytest + pytest-cov)
    ├── test_parser.py
    ├── test_expand.py
    └── fixtures/
        └── prompt_input.md
```

---

## Testing & Coverage

We use `pytest` + `pytest-cov` to ensure >80% coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

---

## Contributing

1. Pick an open task from [STACK_OF_TASKS.md](./STACK_OF_TASKS.md)
2. Branch, implement, add tests
3. Submit a PR

---

## License

Apache-2.0 © microscaler
