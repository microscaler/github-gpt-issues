[![PyPI](https://img.shields.io/pypi/v/github-gpt-issues.svg)](https://pypi.org/project/github-gpt-issues/)
[![Build Status](https://img.shields.io/github/actions/workflow/status/microscaler/github-gpt-issues/ci.yml?branch=main)](https://github.com/microscaler/github-gpt-issues/actions)
[![Coverage Status](https://img.shields.io/codecov/c/github/microscaler/github-gpt-issues/main.svg)](https://codecov.io/gh/microscaler/github-gpt-issues)
[![License](https://img.shields.io/github/license/microscaler/github-gpt-issues.svg)](./LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/github-gpt-issues.svg)](https://pypi.org/project/github-gpt-issues/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/github-gpt-issues.svg)](https://pypi.org/project/github-gpt-issues/)
[![Code Style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: flake8](https://img.shields.io/badge/lint-flake8-blueviolet.svg)](https://flake8.pycqa.org/)
[![Docs](https://img.shields.io/readthedocs/github-gpt-issues.svg)](https://readthedocs.org/projects/github-gpt-issues/)
[![Contributors](https://img.shields.io/github/contributors/microscaler/github-gpt-issues.svg)](https://github.com/microscaler/github-gpt-issues/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/microscaler/github-gpt-issues.svg)](https://github.com/microscaler/github-gpt-issues/commits/main)
[![Open Issues](https://img.shields.io/github/issues/microscaler/github-gpt-issues.svg)](https://github.com/microscaler/github-gpt-issues/issues)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/microscaler)](https://github.com/sponsors/microscaler)


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

## Coverage report:
| Name                            |    Stmts |     Miss |   Cover |
|-------------------------------- | -------: | -------: | ------: |
| src/github\_gpt\_issues/core.py |      129 |       24 |     81% |
| src/github\_gpt\_issues/main.py |       56 |       30 |     46% |
| tests/test\_cache.py            |       35 |        1 |     97% |
| tests/test\_core\_extended.py   |       47 |        1 |     98% |
| tests/test\_github.py           |       51 |        1 |     98% |
|                       **TOTAL** |  **540** |   **57** | **89%** |


---

## Contributing

1. Pick an open task from [STACK_OF_TASKS.md](./STACK_OF_TASKS.md)
2. Branch, implement, add tests
3. Submit a PR

---

## License

Apache-2.0 © microscaler
