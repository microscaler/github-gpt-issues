# justfile for Python project

run-main:
    python src/github_gpt_issues/main.py --run-tests

install:
    pip install -r requirements.txt

test:
    pytest

lint:
    flake8 src/

format:
    black src/